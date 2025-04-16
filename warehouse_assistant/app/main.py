"""
FastAPI应用主模块。
定义和配置FastAPI应用实例。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from warehouse_assistant.app.core.config import settings # 导入配置，确保日志已初始化
# 导入轮询监听器替代Change Stream
from warehouse_assistant.app.services.background.polling_listener import (
    start_polling_task,
    stop_polling_task
)
# 导入数据库服务用于应用关闭时清理连接（如果需要）
from warehouse_assistant.app.services.database.mongo_service import get_db_service
from warehouse_assistant.app.api import router as api_router
from warehouse_assistant.app.services.ai.knowledge_base import get_knowledge_service # <--- 确保这行导入存在
# 导入后台任务管理器
from warehouse_assistant.app.services.background.task_manager import task_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI application startup...")
    # 启动数据库服务（单例模式下会自动初始化）
    get_db_service()
    # 启动知识库服务（单例模式下会自动初始化）
    from warehouse_assistant.app.services.ai.knowledge_base import get_knowledge_service
    get_knowledge_service()
    # 启动轮询任务替代Change Stream
    await start_polling_task()
    # 启动所有后台任务
    await task_manager.start_all_tasks()
    yield
    # Clean up on shutdown
    logger.info("FastAPI application shutdown...")
    # 停止轮询任务
    await stop_polling_task()
    # 关闭数据库连接（如果使用单例）
    db_service = get_db_service()
    db_service.close()
    # 停止所有后台任务
    await task_manager.stop_all_tasks()
    logger.info("Shutdown tasks complete.")

# 创建 FastAPI app instance with lifespan manager
app = FastAPI(
    title="智能仓储助手",
    description="提供智能问答和物料追溯功能的API服务",
    version="0.1.1", # 版本号可以更新
    lifespan=lifespan
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router)

# --- 根路由 ---
@app.get("/")
async def root():
    db_service = get_db_service()
    db_status = "Connected" if not db_service.use_local_file and db_service.client else "Local File Mode or Connection Failed"
    kb_service = get_knowledge_service()
    kb_status = "Loaded" if kb_service.vectorstore else "Not Loaded"

    return {
        "name": "智能仓储助手API",
        "version": app.version,
        "status": "运行中",
        "database_status": db_status,
        "knowledge_base_status": kb_status
    }

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    logger.info("应用启动中...")
    # 启动所有后台任务
    await task_manager.start_all_tasks()
    logger.info("应用启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的操作"""
    logger.info("应用关闭中...")
    # 停止所有后台任务
    await task_manager.stop_all_tasks()
    logger.info("应用关闭完成")
