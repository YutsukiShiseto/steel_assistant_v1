"""
事件处理状态跟踪模块
用于跟踪事件处理状态，避免重复处理
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
import threading

logger = logging.getLogger(__name__)

class EventTracker:
    """事件处理状态跟踪器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EventTracker, cls).__new__(cls)
                    cls._instance._init_tracker()
        return cls._instance
    
    def _init_tracker(self):
        """初始化跟踪器"""
        self._lock = threading.RLock()  # 使用可重入锁保护状态访问
        self.processing_events = set()  # 正在处理的事件ID集合
        self.processed_events = {}  # 已处理事件的字典 {event_id: timestamp}
        self.max_history = 1000  # 最大历史记录数
        self.retention_period = timedelta(hours=24)  # 保留处理记录的时间
    
    def is_processing(self, event_id: str) -> bool:
        """检查事件是否正在处理中"""
        with self._lock:
            return event_id in self.processing_events
    
    def has_processed(self, event_id: str) -> bool:
        """检查事件是否已处理过"""
        with self._lock:
            return event_id in self.processed_events
    
    def mark_as_processing(self, event_id: str) -> bool:
        """标记事件为处理中状态"""
        with self._lock:
            if self.is_processing(event_id) or self.has_processed(event_id):
                logger.warning(f"事件 {event_id} 已在处理中或已处理过，跳过")
                return False
            
            self.processing_events.add(event_id)
            logger.info(f"事件 {event_id} 已标记为处理中")
            return True
    
    def mark_as_processed(self, event_id: str, success: bool = True) -> None:
        """标记事件为已处理状态"""
        with self._lock:
            if event_id in self.processing_events:
                self.processing_events.remove(event_id)
            
            self.processed_events[event_id] = {
                'timestamp': datetime.utcnow(),
                'success': success
            }
            
            logger.info(f"事件 {event_id} 已标记为已处理，状态: {'成功' if success else '失败'}")
            
            # 清理过期记录
            self._cleanup_old_records()
    
    def _cleanup_old_records(self) -> None:
        """清理过期的处理记录"""
        now = datetime.utcnow()
        cutoff_time = now - self.retention_period
        
        # 删除过期记录
        expired_events = [
            event_id for event_id, data in self.processed_events.items()
            if data['timestamp'] < cutoff_time
        ]
        
        for event_id in expired_events:
            del self.processed_events[event_id]
        
        # 如果记录数超过最大值，删除最早的记录
        if len(self.processed_events) > self.max_history:
            sorted_events = sorted(
                self.processed_events.items(),
                key=lambda x: x[1]['timestamp']
            )
            
            events_to_remove = sorted_events[:len(self.processed_events) - self.max_history]
            for event_id, _ in events_to_remove:
                del self.processed_events[event_id]

# 获取事件跟踪器实例
def get_event_tracker() -> EventTracker:
    return EventTracker() 