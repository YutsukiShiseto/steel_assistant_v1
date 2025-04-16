"""
MongoDB数据库服务模块
提供数据库连接和操作功能
"""
import logging
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId
import json
import os
from datetime import datetime

# 修改导入路径为绝对路径
from warehouse_assistant.app.core.config import settings

logger = logging.getLogger(__name__)

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)


class DatabaseService:
    """MongoDB数据库服务类，提供数据库连接和操作功能"""
    
    _instance = None  # 单例实例
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            logger.info("Initializing DatabaseService instance...")
            cls._instance = super(DatabaseService, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.db = None
            cls._instance.trace_events = None
            cls._instance.knowledge_items = None
            cls._instance.use_local_file = False
            logger.info("Return DatabaseService __init__...")
        return cls._instance
    
    def __init__(self):
        """初始化数据库连接"""
        if self.client is None:
            self.connect()
    
    def connect(self):
        """连接到MongoDB数据库"""
        try:
            # 尝试连接MongoDB
            logger.info(f"Attemping to connect to MongoDB: {settings.MONGODB_CONNECTION_STRING} / DB: {settings.MONGODB_DB_NAME}")
            self.client = MongoClient(settings.MONGODB_CONNECTION_STRING)
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # 初始化集合
            self.trace_events = self.db["trace_events"]
            self.knowledge_items = self.db["knowledge_items"]
            
            # 创建索引
            self.trace_events.create_index([("timestamp", DESCENDING)])
            self.trace_events.create_index("batch_id")
            self.trace_events.create_index("material_code")
            
            logger.info("MongoDB collection and indexes setup complete.")
            
            # 测试连接
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB.")
            
        except Exception as e:
            logger.warning(f"Failed to connect to MongoDB: {e}. Using local file storage instead.")
            self.use_local_file = True
            self.client = None
            self.db = None
            
            # 创建本地存储目录
            os.makedirs("local_storage", exist_ok=True)
    
    def _setup_collection(self):
        """设置MongoDB集合和索引"""
        try:
            if self.db is not None:  # 使用 is not None 而不是布尔测试
                # 确保集合存在，并创建必要的索引
                self.trace_events = self.db["trace_events"]
                # 创建或确认索引
                self.trace_events.create_index([("batch_id", 1)])
                self.trace_events.create_index([("timestamp", -1)])
                logger.info("MongoDB collection and indexes setup complete.")
        except Exception as e:
            logger.error(f"Error setting up MongoDB collection: {e}")
            self.use_local_file = True  # 降级到本地文件模式

    # 本地文件读写方法（—_load_trace_events, _save_trace_events）保持不变
    def _load_trace_events(self) -> List[Dict[str, Any]]:
        """从本地文件加载追溯事件数据"""
        file_path = os.path.join(self.data_dir, "trace_events.json")
        if not os.path.exists(file_path): return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception as e:
            logger.error(f"加载追溯事件文件失败: {e}", exc_info=True)
            return []
        

    def _save_trace_events(self, events: List[Dict[str, Any]]):
        """保存追溯事件数据到本地文件"""
        file_path = os.path.join(self.data_dir, "trace_events.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2, cls=JSONEncoder)
        except Exception as e:
            logger.error(f"保存追溯事件文件失败: {e}", exc_info=True)

    # insert_trace_event, get_trace_events_by_batch_id 保持不变
    def insert_trace_event(self, event_data: Dict[str, Any]) -> str:
        if self.use_local_file:
            events = self._load_trace_events()
            event_id = str(ObjectId())
            event_data['_id'] = event_id
            # 确保时间是 datatime 对象，以便后面排序
            if isinstance(event_data.get('timestamp'), str):
                try:
                    event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
                except ValueError:
                    event_data['timestamp'] = datetime.now() # Fallback
            elif not isinstance(event_data.get('timestamp'), datetime):
                event_data['timestamp'] = datetime.now() # Fallback

            events.append(event_data)
            self._save_trace_events(events)
            logger.info(f"Inserted event {event_id} into local file.")
            return event_id
        
        elif self.db:
            try:
                result = self.db.trace_events.insert_one(event_data)
                logger.info(f"Inserted event {result.inserted_id} into MongoDB.")
                return str(result.inserted_id)
            except Exception as e:
                logger.error(f"Error inserting event into MongoDB: {e}", exc_info=True)
                raise # 重新抛出异常或返回错误标识

        else:
            logger.error("Database not available for inserting event.")
            raise ConnectionError("Database service not properly initialized.")
        
    def get_trace_events_by_batch_id(self, batch_id: str) -> List[Dict[str, Any]]:
        if self.use_local_file:
            events = self._load_trace_events()
            filtered_events = [e for e in events if e.get('batch_id') == batch_id]
            # 解析字符串时间排序
            def get_timestamp(event):
                ts = event.get('timestamp')
                if isinstance(ts, str):
                    try: return datetime.fromisoformat(ts)
                    except ValueError: return datetime.min
                elif isinstance(ts, datetime):
                    return ts
                return datetime.min
            return sorted(filtered_events, key=get_timestamp)
        elif self.db:
            try:
                cursor = self.db.trace_events.find({"batch_id": batch_id}).sort("timestamp", 1)
                return list(cursor)
            except Exception as e:
                logger.error(f"Error getting events by batch_id {batch_id}: {e}", exc_info=True)
                return []
        else:
             logger.error("Database not available for get_trace_events_by_batch_id.")
             return []
        
    # 新增方法
    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        根据事件ID获取单个事件详情
        
        Args:
            event_id: 事件ID (MongoDB ObjectId的字符串表示)
            
        Returns:
            事件详情字典，如果未找到则返回None
        """
        try:
            if self.use_local_file:
                # 本地文件模式
                events = self._load_trace_events()
                for event in events:
                    if str(event.get("_id", "")) == event_id:
                        return event
                return None
            else:
                # MongoDB模式
                result = self.trace_events.find_one({"_id": ObjectId(event_id)})
                return result
        except Exception as e:
            logger.error(f"获取事件详情失败: {e}", exc_info=True)
            return None

    def update_event_risk(self, event_id:str, risk_assessment: Dict[str, Any]) -> bool:
        """
        更新指定事件的 risk_assessment 字段。
        """
        if self.use_local_file:
            logger.warning("update_event_risk is inefficient in local file mode")
            events = self._load_trace_events()
            update = False
            for i, event in enumerate(events):
                if event.get('_id') == event_id:
                    events[i]['risk_assessment'] = risk_assessment
                    updated = True
                    break
            if updated:
                self._save_trace_events(events)
                logger.info(f"Updated risk assessment for event {event_id} in local file.")
                return True
            else:
                logger.warning(f"Event {event_id} not found for risk update in local file.")
                return False
        elif self.db is not None:
            try:
                old = ObjectId(event_id)
                result = self.db.trace_events.update_one(
                    {"_id": old},
                    {"$set": {"risk_assessment": risk_assessment}}
                )
                if result.modified_count > 0:
                    logger.info(f"Successfully updated risk assessment for event {event_id}")
                    return True
                elif result.matched_count > 0:
                    logger.info(f"Risk assessment data was the same for event {event_id}, no MongoDB update needed.")
                    return True #认为逻辑上是成功的
                else:
                    logger.warning(f"Event {event_id} not found for risk update in MongoDB.")
                    return False
            except Exception as e:
                logger.error(f"Error updating risk for event {event_id} in MongoDB: {e}", exc_info=True)
                return False
        else:
            logger.error("Database not available for update_event_risk.")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if not self.use_local_file and self.client:
            logger.info("Closing MongoDB connection.")
            self.client.close()
            DatabaseService._instance = None # 清除单例，以便下次连接
            self.initialized = False 

# 提供获取数据库服务实例的函数
def get_db_service() -> DatabaseService:
    # 返回单例实例
    # 这里的 use_local_file 默认是false，除非初始化时强制或失败
    return DatabaseService()


                