"""
后台任务管理器 - 管理所有后台运行的任务
"""
import asyncio
import logging
from typing import Dict, Any, List, Callable, Coroutine
from warehouse_assistant.app.services.background.db_monitor import db_monitor

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """管理应用程序的后台任务"""
    
    def __init__(self):
        """初始化任务管理器"""
        self.tasks: Dict[str, asyncio.Task] = {}
        
    async def start_all_tasks(self):
        """启动所有后台任务"""
        logger.info("启动所有后台任务...")
        
        # 启动数据库监听器
        await self.start_task("db_monitor", db_monitor.start_monitoring)
        
        logger.info("所有后台任务已启动")
    
    async def start_task(self, task_name: str, task_func: Callable[[], Coroutine]):
        """启动单个后台任务"""
        if task_name in self.tasks and not self.tasks[task_name].done():
            logger.warning(f"任务 {task_name} 已经在运行中")
            return
        
        logger.info(f"启动任务: {task_name}")
        self.tasks[task_name] = asyncio.create_task(task_func())
    
    async def stop_all_tasks(self):
        """停止所有后台任务"""
        logger.info("停止所有后台任务...")
        
        # 停止数据库监听器
        db_monitor.stop_monitoring()
        
        # 取消所有任务
        for task_name, task in self.tasks.items():
            if not task.done():
                logger.info(f"取消任务: {task_name}")
                task.cancel()
        
        # 等待所有任务完成
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        self.tasks.clear()
        logger.info("所有后台任务已停止")

# 创建单例实例
task_manager = BackgroundTaskManager() 