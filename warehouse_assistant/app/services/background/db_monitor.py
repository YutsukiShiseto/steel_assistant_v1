"""
数据库监听器模块 - 监听MongoDB中的新数据并触发风险评估
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from bson import ObjectId
from warehouse_assistant.app.core.config import settings
from warehouse_assistant.app.services.ai.crews.risk_crew import run_risk_assessment_for_event
from warehouse_assistant.app.services.background.event_tracker import get_event_tracker

logger = logging.getLogger(__name__)

class DatabaseMonitor:
    """MongoDB数据库监听器，用于监听新的追溯事件并触发风险评估"""
    
    def __init__(self):
        """初始化数据库监听器"""
        self.client = MongoClient(settings.MONGODB_CONNECTION_STRING)
        self.db = self.client[settings.MONGODB_DB_NAME]
        self.events_collection = self.db["trace_events"]
        self.last_check_time = datetime.utcnow()
        self.running = False
        self.check_interval = 30  # 每30秒检查一次新数据
        
    async def start_monitoring(self):
        """开始监听数据库变化"""
        logger.info("开始监听数据库变化...")
        self.running = True
        
        while self.running:
            try:
                # 查找自上次检查以来的新事件
                new_events = await self._get_new_events()
                
                if new_events:
                    logger.info(f"发现 {len(new_events)} 个新事件，开始处理...")
                    await self._process_new_events(new_events)
                
                # 更新最后检查时间
                self.last_check_time = datetime.utcnow()
                
                # 等待下一次检查
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"监听数据库时发生错误: {e}", exc_info=True)
                # 出错后等待一段时间再继续
                await asyncio.sleep(60)
    
    def stop_monitoring(self):
        """停止监听数据库变化"""
        logger.info("停止监听数据库变化")
        self.running = False
    
    async def _get_new_events(self) -> List[Dict[str, Any]]:
        """获取自上次检查以来的新事件"""
        try:
            # 查找创建时间晚于上次检查时间且没有风险评估的事件
            # 修改查询条件，使用timestamp字段而不是created_at
            query = {
                "timestamp": {"$gt": self.last_check_time},
                "$or": [
                    {"risk_assessment": {"$exists": False}},
                    {"risk_assessment": None}
                ]
            }
            
            # 将查询操作包装在异步函数中执行
            new_events = await asyncio.to_thread(
                lambda: list(self.events_collection.find(query))
            )
            
            return new_events
        except Exception as e:
            logger.error(f"获取新事件时出错: {e}", exc_info=True)
            return []
    
    async def _process_new_events(self, events: List[Dict[str, Any]]):
        """处理新事件，触发风险评估"""
        event_tracker = get_event_tracker()
        
        for event in events:
            try:
                # 确保event有_id字段
                if "_id" not in event:
                    logger.warning(f"事件缺少_id字段，跳过: {event}")
                    continue
                
                event_id = str(event["_id"])
                
                # 检查事件是否已在处理中或已处理过
                if event_tracker.is_processing(event_id) or event_tracker.has_processed(event_id):
                    logger.info(f"[数据库监听器] 事件 {event_id} 已在处理中或已处理过，跳过")
                    continue
                    
                # 标记事件为处理中
                if not event_tracker.mark_as_processing(event_id):
                    logger.warning(f"[数据库监听器] 无法标记事件 {event_id} 为处理中状态，跳过")
                    continue
                    
                logger.info(f"[数据库监听器] 为事件 {event_id} 触发风险评估...")
                
                try:
                    # 先检查事件是否仍然存在
                    event_check = self.events_collection.find_one({"_id": ObjectId(event_id)})
                    if not event_check:
                        logger.warning(f"事件 {event_id} 不再存在，跳过风险评估")
                        event_tracker.mark_as_processed(event_id, False)
                        continue
                    
                    # 直接调用风险评估函数
                    result = run_risk_assessment_for_event(event_id)
                    logger.info(f"事件 {event_id} 的风险评估完成: {result}")
                    
                    # 标记事件为已处理
                    success = result.get('status') == 'success'
                    event_tracker.mark_as_processed(event_id, success)
                    
                except Exception as e:
                    logger.error(f"运行风险评估时出错: {e}", exc_info=True)
                    event_tracker.mark_as_processed(event_id, False)
            except Exception as e:
                logger.error(f"处理事件时出错: {e}", exc_info=True)

# 创建单例实例
db_monitor = DatabaseMonitor() 