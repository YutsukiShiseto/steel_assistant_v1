import requests
import json
import os
from fastapi import FastAPI, HTTPException, Request #导入FastAPI相关组件
from fastapi.responses import StreamingResponse #导入用于流式响应的类
from pydantic import BaseModel #导入pydantic用于定义请求体模型
from dotenv import load_dotenv
import asyncio #导入asyncio用于异步操作

# 加载环境变量
load_dotenv("warehouse_assistant/.env")

# pydantic 模型
class AskRequest(BaseModel):
    """
    定义前端发送给过来的请求体结构
    """
    query: str
    user_id: str #让前端传递user_id
    conversation_id: str | None = None #conversation_id 可以是字符串或者是None，默认是None

# FastAPI应用实例
app = FastAPI(title = "Dify 终端聊天助手")



# --- 全局变量（用于存储对话状态，注意：这种方式在多用户时有问题，后面会提）---
# 更好的方式是前端每次请求都带上 conversation_id
# conversation_store = {} # 暂时不用全局变量，让前端管理
 
 # Dify API 调用函数（FastAPI）
async def call_dify_api(user_query: str, user_id: str, conversation_id: str | None):
    """
    异步函数，调用Dify API 并处理流式响应
    这个函数将作为一个生成器（generator）来产生数据块
    """
    headers = {
        "Authorization": f"Bearer {os.getenv('DIFY_API_KEY')}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": {"query": user_query},
        "query": user_query,
        "user": user_id,
        "response_mode": "streaming",

        #只有当 conversation_id 有值时才包含他
        **({"conversation_id": conversation_id} if conversation_id else {})
    }

    try:
        #使用 aiohttp 或 httpx 进行异步请求，这里为了简单先用requests + run_in_executor
        #注意：requests 是同步库，在异步环境中使用它会阻塞事件循环
        #更优的方式是使用异步 HTTP 客户端如httpx 或 aiohttp
        #这里用一种 FastAPI 推荐的异步代码中运行同步代码的方式
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, #使用默认的线程池执行器
            lambda: requests.post(
                os.getenv("DIFY_API_URL"),
                headers=headers,
                json=payload,
                stream=True
            )
        )
        response.raise_for_status() #检查 HTTP 错误状态

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    try:
                        data_str = decoded_line[len("data:"):].strip()
                        if data_str:
                            # 直接将原始的data：开头的行 yield 出去
                            #或者解析后只 yield 需要的部分
                            #yield f"{decoded_line}\n" #方式一，直接转发原始 SSE 行

                            #方式二 解析后之转发 message 的 answer
                            data = json.loads(data_str)
                            # (调试) print(f"数据块: {data}")
                            event = data.get("event")
                            #print(f"数据块: {data}")

                            if event == "message":
                                message_text = data.get("answer", "")
                                 # 如果 answer 为 None 或不存在，则给一个空字符串，避免错误
                                 #将数据块（可能是JSON 字符串，或者只是文本）发送给前端
                                 #为了兼容 SSE，通常包装成 "data:...\n\n" 格式
                                yield f"data: {json.dumps({'message_text': message_text})}\n\n"
                            
                            elif event == "message_end":
                                # 更新全局的 conversation_id 以便下次循环使用
                                # 可以发送一个特殊事件告诉前端结束，并带上conversation_id
                                new_conversation_id = data.get("conversation_id")
                                yield f"data: {json.dumps({'event': 'end', 'conversation_id': new_conversation_id})}\n\n"
                                break # 当前轮次结束

                            elif event == "error":
                                # 发送错误信息给前端
                                yield f"data: {json.dumps({'event': 'error', 'code': data.get('code'), 'message': data.get('message')})}\n\n"
                                break

                    except json.JSONDecodeError:
                        # 在流中间打印错误，但不一定终止，继续尝试接收下一行
                        yield f"data: {json.dumps({'event': 'error', 'message': f'JSON decode error for line: {data_str}'})}\n\n"
                    except Exception as chunk_error:
                        yield f"data: {json.dumps({'event': 'error', 'message': f'Error processing chunk: {chunk_error}'})}\n\n"
        #确保最后发送一个结束信号（如果 message_end 没有发送）
        # yield f"data: {json.dumps({'event': 'final_end'})}\n\n"#备用结束信号                    

        

    except requests.exceptions.RequestException as e:
        # 将请求错误信息也通过 SSE 发送给前端
        yield f"data: {json.dumps({'event': 'error', 'message': f'Dify API request failed: {e}'})}\n\n"
        #或者直接抛出 HTTPException，让FastAPI返回 500 错误
    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': f'Unknown server error: {e}'})}\n\n"
        #raise HTTPException(status_code=500, detail=f"Unknown server error: {e}")
                        
# API 路由（Endpoint）
@app.post("/api/dify/ask") #定义一个POST请求的端点
async def handle_dify_ask(request_data: AskRequest):
    """
    接受前端问题，调用 Dify API, 并将流式响应返回给前端
    """

    #从请求体中获取数据
    user_query = request_data.query
    user_id = request_data.user_id
    conversation_id = request_data.conversation_id

    #返回一个 StreamingResponse，内容由 call_dify_api 生成器提供
    #media_type="text/event-stream" 是 SSE 的标准类型
    return StreamingResponse(
        call_dify_api(user_query, user_id, conversation_id),
        media_type="text/event-stream",
    )

# 添加 CORS 中间件，允许前端访问

from fastapi.middleware.cors import CORSMiddleware

# --- 假设前端的 IP 是 172.20.17.141，端口是 3000 (请替换为实际端口) ---
frontend_origin = "http://192.168.87.96:5173" 

# --- 假设你自己本地测试时，前端也可能运行在 3000 端口 ---
local_frontend_origin_localhost = "http://localhost:3000" 
local_frontend_origin_ip = "http://127.0.0.1:3000" 
# --- 如果你自己测试的前端端口不同，请修改这里的 3000 ---

origins = [
    frontend_origin,                 # 允许你前端同学的实际访问源
    local_frontend_origin_localhost, # 允许你自己或其他人在本地用 localhost 访问前端时发起的请求
    local_frontend_origin_ip,
    "http://localhost:5174",         # 你之前添加的
    "https://2c13-120-234-171-125.ngrok-free.app", # <--- 添加你的 ngrok URL
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # 使用上面定义的列表
    allow_credentials=True,         # 通常设为 True
    allow_methods=["*"],            # 允许所有 HTTP 方法
    allow_headers=["*"],            # 允许所有请求头
)

# 根路径， 用于测试服务是否启动成功
@app.get("/")
async def read_root():
    return {"message": "Dify API 代理服务已启动"}
