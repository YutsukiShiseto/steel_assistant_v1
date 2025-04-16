# warehouse_assistant/scripts/test_deepseek.py (推荐重命名)

import os
import sys
from pathlib import Path
import logging
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
# 导入配置设置，即使不用所有值，也方便维护
from warehouse_assistant.app.core.config import settings

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- DeepSeek 官方 API 配置 ---
# 优先从环境变量获取，提供一个明确的占位符
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY_PLACEHOLDER")
# 使用带提供商前缀的模型名称
DEEPSEEK_MODEL_WITH_PROVIDER = "deepseek/deepseek-chat" # 或者 "deepseek/deepseek-coder"

def test_crewai_deepseek_connection():
    """测试CrewAI与DeepSeek官方模型的连接"""
    logger.info("开始测试CrewAI与 DeepSeek 官方模型的连接...")
    try:
        # --- 检查 DeepSeek API Key ---
        if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY_PLACEHOLDER":
            logger.error("❌ DeepSeek API Key 未配置。请设置 DEEPSEEK_API_KEY 环境变量。")
            return False # 直接返回失败

        logger.info(f"使用 DeepSeek 模型 (带提供商前缀): {DEEPSEEK_MODEL_WITH_PROVIDER}")

        # --- 1. 直接调用测试 (使用 LiteLLM) ---
        logger.info("测试直接使用 LiteLLM 调用 DeepSeek API...")
        import litellm
        try:
            # 确保环境变量 DEEPSEEK_API_KEY 对 LiteLLM 可见
            # (注意: litellm 可能查找 DEEPSEEK_API_KEY 而不是 OPENAI_API_KEY)
            os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY

            response = litellm.completion(
                model=DEEPSEEK_MODEL_WITH_PROVIDER,
                messages=[
                    {"role": "system", "content": "你是人工智能助手"},
                    {"role": "user", "content": "请用一句话介绍你自己，并说明你是 DeepSeek 模型。"},
                ],
                # stream=False # 确保获取完整响应
            )
            direct_response = response.choices[0].message.content
            logger.info(f"直接调用 LiteLLM->DeepSeek 结果: {direct_response}")
            if "DeepSeek" not in direct_response:
                 logger.warning("直接调用测试：响应中未包含 'DeepSeek' 关键词。")
        except Exception as direct_err:
             logger.error(f"直接调用 LiteLLM->DeepSeek API 失败: {direct_err}", exc_info=True)
             logger.error("请检查 DEEPSEEK_API_KEY 是否有效以及网络连接。")
             return False # 直接调用失败则后续测试无意义


        # --- 2. 配置 CrewAI 使用的 LLM 实例 ---
        logger.info("配置 CrewAI 使用的 LLM 实例 (指向 DeepSeek)...")
        try:
            # 创建 ChatOpenAI 实例，明确传入模型名称和 API Key
            crew_llm = ChatOpenAI(
                model=DEEPSEEK_MODEL_WITH_PROVIDER,
                api_key=DEEPSEEK_API_KEY,
                # temperature=0.7 # 可根据需要调整
                # base_url="https://api.deepseek.com/v1" # 通常不需要，除非默认URL有问题
            )
            logger.info("CrewAI LLM 实例配置完成。")
        except Exception as llm_init_err:
            logger.error(f"创建 ChatOpenAI 实例失败: {llm_init_err}", exc_info=True)
            return False


        # --- 3. 创建 CrewAI Agent ---
        logger.info("创建测试 Agent...")
        try:
            test_agent = Agent(
                role="测试代理",
                goal="测试与 DeepSeek 模型的连接并按要求响应", # 目标更具体
                backstory="你是一个简单的测试代理，接收任务并使用配置好的 DeepSeek 模型生成回答。",
                verbose=True,
                allow_delegation=False, # 测试代理通常不需要委托
                llm=crew_llm # 传入配置好的 LLM 实例
            )
            logger.info("测试 Agent 创建成功。")
        except Exception as agent_init_err:
             logger.error(f"创建 Agent 实例失败: {agent_init_err}", exc_info=True)
             # 检查 crewai 版本和依赖是否兼容
             return False


        # --- 4. 创建 CrewAI Task ---
        logger.info("创建测试 Task...")
        try:
            test_task = Task(
                description="请回答以下问题：'你是什么模型？你能做什么？' 你的回答必须明确包含 'DeepSeek' 这个词。",
                expected_output="一段包含 'DeepSeek' 词语的自然语言回答。",
                agent=test_agent
                # human_input=False # 任务不需要人工输入
            )
            logger.info("测试 Task 创建成功。")
        except Exception as task_init_err:
            logger.error(f"创建 Task 实例失败: {task_init_err}", exc_info=True)
            return False


        # --- 5. 创建并执行 Crew ---
        logger.info("创建并执行 Crew...")
        try:
            crew = Crew(
                agents=[test_agent],
                tasks=[test_task],
                process=Process.sequential,
                verbose=True # <--- 修改这里！将 2 改为 True
            )
            logger.info("Crew 创建成功，开始执行 kickoff()...")
            result = crew.kickoff()
            logger.info("CrewAI 任务执行完成。")

        except Exception as crew_run_err:
            logger.error(f"执行 Crew kickoff() 时发生错误: {crew_run_err}", exc_info=True)
            return False


        # --- 6. 分析结果 ---
        logger.info("分析 Crew 执行结果...")
        logger.info("-" * 50)
        # 打印原始 result 对象的类型和内容，有助于调试
        logger.info(f"原始 Result 类型: {type(result)}")
        logger.info(f"原始 Result 内容: {result}")
        logger.info("-" * 50)

        # --- 尝试从 CrewOutput 对象提取最终答案 ---
        final_answer = None
        if hasattr(result, 'raw'): # 常见属性：原始输出
            final_answer = result.raw
            logger.info("从 result.raw 提取最终答案。")
        elif hasattr(result, 'result'): # 另一种常见属性
             final_answer = result.result
             logger.info("从 result.result 提取最终答案。")
        elif hasattr(result, 'final_answer'): # 还有可能是这个
             final_answer = result.final_answer
             logger.info("从 result.final_answer 提取最终答案。")
        elif isinstance(result, str): # 兼容旧版本或简单任务的直接字符串输出
             final_answer = result
             logger.info("结果直接是字符串。")
        else:
             # 如果以上都不是，打印对象的属性看看
             try:
                 logger.warning(f"无法直接提取最终答案，尝试打印 result 属性: {dir(result)}")
             except:
                  pass # 避免打印属性时出错

        # --- 基于提取出的 final_answer 进行判断 ---
        if final_answer and isinstance(final_answer, str) and "DeepSeek" in final_answer:
            logger.info("✅ 测试成功：CrewAI 成功调用 DeepSeek 模型并获得包含关键词的响应！")
            logger.info(f"提取到的最终答案:\n{final_answer}")
            return True
        elif final_answer and isinstance(final_answer, str):
            logger.warning("⚠️ 测试结果不确定：模型返回了结果，但未包含预期的 'DeepSeek' 关键词。请检查模型响应和任务描述。")
            logger.info(f"提取到的最终答案:\n{final_answer}")
            return False
        else:
             logger.error(f"❌ 测试失败：无法从 Crew 执行结果中提取有效的字符串答案。原始 Result 类型: {type(result)}")
             return False

    # --- 捕获函数级别的总异常 ---
    except ValueError as ve: # 捕获配置错误
         logger.error(f"❌ 测试前置条件失败: {ve}")
         return False
    except Exception as e:
        logger.error(f"❌ 测试过程中发生未捕获的异常：{e}", exc_info=True)
        return False

if __name__ == "__main__":
    # 确保设置了 sys.path (如果需要从 scripts 目录运行)
    # script_dir = Path(__file__).parent
    # project_root = script_dir.parent.parent
    # sys.path.insert(0, str(project_root))

    success = test_crewai_deepseek_connection()
    if success:
        print("\n测试通过！")
        # sys.exit(0) # 可选：成功时退出码为 0
    else:
        print("\n测试失败。请检查日志获取详细信息。")
        # sys.exit(1) # 可选：失败时退出码为 1