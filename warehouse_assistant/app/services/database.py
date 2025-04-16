"""
数据库服务模块。
提供与MongoDB数据库交互的功能，以及备选的本地文件存储方案。
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    """扩展JSON编码器，处理日期和ObjectId"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

class DatabaseService:
    """
    数据库服务类，提供MongoDB连接和操作方法。
    如果MongoDB不可用，则使用本地JSON文件作为备选存储方案。
    """
    def __init__(self, connection_string: Optional[str] = None, use_local_file: bool = False):
        """
        初始化数据库服务。
        
        Args:
            connection_string: MongoDB连接字符串，如果为None则从环境变量获取
            use_local_file: 是否使用本地文件存储（当MongoDB不可用时）
        """
        self.use_local_file = use_local_file
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        if not use_local_file:
            try:
                if connection_string is None:
                    connection_string = os.getenv("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017/")
                
                self.client = MongoClient(connection_string)
                self.db: Database = self.client.get_database("warehouse_assistant")
                
                # 确保创建必要的集合和索引
                self._setup_collections()
                print("成功连接到MongoDB")
            except Exception as e:
                print(f"MongoDB连接失败: {str(e)}，将使用本地文件存储")
                self.use_local_file = True
                self.client = None
                self.db = None
        else:
            print("使用本地文件存储模式")
            self.client = None
            self.db = None
    
    def _setup_collections(self):
        """设置集合和索引"""
        # 物料追溯集合
        trace_events: Collection = self.db.trace_events
        
        # 创建索引以提高查询性能
        trace_events.create_index("batch_id")
        trace_events.create_index("timestamp")
        trace_events.create_index([("batch_id", 1), ("timestamp", 1)])
    
    def _load_trace_events(self) -> List[Dict[str, Any]]:
        """从本地文件加载追溯事件数据"""
        file_path = os.path.join(self.data_dir, "trace_events.json")
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载追溯事件文件失败: {str(e)}")
            return []
    
    def _save_trace_events(self, events: List[Dict[str, Any]]):
        """保存追溯事件数据到本地文件"""
        file_path = os.path.join(self.data_dir, "trace_events.json")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2, cls=JSONEncoder)
        except Exception as e:
            print(f"保存追溯事件文件失败: {str(e)}")
    
    def insert_trace_event(self, event_data: Dict[str, Any]) -> str:
        """
        插入一条追溯事件记录。
        
        Args:
            event_data: 事件数据字典
            
        Returns:
            插入记录的ID
        """
        if self.use_local_file:
            events = self._load_trace_events()
            # 生成一个简单的ID
            event_id = str(ObjectId())
            event_data['_id'] = event_id
            events.append(event_data)
            self._save_trace_events(events)
            return event_id
        else:
            result = self.db.trace_events.insert_one(event_data)
            return str(result.inserted_id)
    
    def get_trace_events_by_batch_id(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        根据批次号查询追溯事件。
        
        Args:
            batch_id: 批次号
            
        Returns:
            按时间排序的追溯事件列表
        """
        if self.use_local_file:
            events = self._load_trace_events()
            # 过滤并排序
            filtered_events = [e for e in events if e.get('batch_id') == batch_id]
            # 按时间戳排序
            return sorted(filtered_events, key=lambda x: x.get('timestamp', ''))
        else:
            cursor = self.db.trace_events.find(
                {"batch_id": batch_id}
            ).sort("timestamp", 1)  # 按时间升序排序
            
            return list(cursor)
    
    def close(self):
        """关闭数据库连接"""
        if not self.use_local_file and self.client:
            self.client.close() 