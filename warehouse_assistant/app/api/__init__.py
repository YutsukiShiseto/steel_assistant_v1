"""
API包初始化模块。
用于注册和管理所有API路由。
"""
from fastapi import APIRouter
from warehouse_assistant.app.api.routes.trace import router as trace_router

# 创建主路由器
router = APIRouter()

# 注册子路由器
router.include_router(trace_router)

# 可以在这里注册更多的路由器，例如：
# router.include_router(ask_router)
