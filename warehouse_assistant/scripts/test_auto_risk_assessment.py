"""
测试自动风险评估功能
"""
import os
import sys
from pathlib import Path
import logging
import time
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# 获取当前脚本所在目录
script_dir = Path(__file__).parent
# 获取项目根目录
project_root = script_dir.parent.parent
# 将项目根目录添加到Python搜索路径
sys.path.insert(0, str(project_root))

from warehouse_assistant.app.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_event():
    """创建一个测试事件"""
    try:
        # 连接MongoDB
        client = MongoClient(settings.MONGODB_CONNECTION_STRING)
        db = client[settings.MONGODB_DB_NAME]
        events_collection = db["trace_events"]
        
        # 创建测试事件 - 确保字段与实际使用的模型匹配
        event = {
            "batch_id": f"BATCH-{int(time.time())}",
            "operation_type": "测试操作",  # 使用正确的字段名
            "location": "测试位置",
            "operator": "测试操作员",
            "parameters": {
                "temperature": 150,
                "pressure": 50,
                "duration": 30
            },
            "quality_check": {
                "result": "合格",
                "inspector": "测试质检员",
                "remarks": "测试备注"
            },
            "timestamp": datetime.utcnow(),  # 使用timestamp而不是created_at
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # 插入事件
        result = events_collection.insert_one(event)
        event_id = str(result.inserted_id)
        
        logger.info(f"创建测试事件成功，ID: {event_id}")
        return event_id
    
    except Exception as e:
        logger.error(f"创建测试事件失败: {e}", exc_info=True)
        return None

def check_risk_assessment(event_id, max_attempts=10, delay=5):
    """检查事件的风险评估结果"""
    try:
        # 连接MongoDB
        client = MongoClient(settings.MONGODB_CONNECTION_STRING)
        db = client[settings.MONGODB_DB_NAME]
        events_collection = db["trace_events"]
        
        for attempt in range(max_attempts):
            # 查询事件
            event = events_collection.find_one({"_id": ObjectId(event_id)})
            
            if event and "risk_assessment" in event and event["risk_assessment"]:
                logger.info(f"事件 {event_id} 的风险评估结果: {event['risk_assessment']}")
                return True
            
            logger.info(f"尝试 {attempt+1}/{max_attempts}: 事件 {event_id} 尚未完成风险评估，等待 {delay} 秒...")
            time.sleep(delay)
        
        logger.warning(f"在 {max_attempts} 次尝试后，事件 {event_id} 仍未完成风险评估")
        return False
    
    except Exception as e:
        logger.error(f"检查风险评估结果失败: {e}", exc_info=True)
        return False

def main():
    """主函数"""
    logger.info("开始测试自动风险评估功能...")
    
    # 创建测试事件
    event_id = create_test_event()
    if not event_id:
        logger.error("创建测试事件失败，测试终止")
        return
    
    # 检查风险评估结果
    logger.info(f"等待系统自动为事件 {event_id} 进行风险评估...")
    success = check_risk_assessment(event_id)
    
    if success:
        logger.info("✅ 测试成功：系统成功自动完成风险评估！")
    else:
        logger.error("❌ 测试失败：系统未能自动完成风险评估")

if __name__ == "__main__":
    main() 