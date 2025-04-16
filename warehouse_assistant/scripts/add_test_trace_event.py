"""
添加测试追溯事件到MongoDB
用于测试风险评估功能
"""
import sys
import os
from pathlib import Path
import datetime
from bson import ObjectId
import json

# 设置Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from warehouse_assistant.app.services.database.mongo_service import get_db_service

def add_test_event():
    """添加测试事件到MongoDB"""
    db_service = get_db_service()
    
    # 创建测试事件数据
    test_event = {
        "batch_id": "BATCH-2025-04-16-001",
        "material_code": "STEEL-HRC-Q235B",
        "operation_type": "热轧",
        "location_name": "1号轧机",
        "operator_id": "OP-10086",
        "timestamp": datetime.datetime.utcnow(),
        "equipment_params": {
            "temperature": 950,  # 摄氏度
            "speed": 25,  # 米/分钟，超出标准范围
            "pressure": 2000,  # kPa
            "thickness": 2.5  # mm
        },
        "quality_inspection": {
            "surface_quality": "合格",
            "dimension_check": "不合格",  # 尺寸检查不合格
            "hardness_test": "合格",
            "overall_result": "不合格"
        },
        "defect_info": {
            "has_defect": True,
            "defect_type": "尺寸偏差",
            "defect_description": "厚度不均匀，局部超差"
        },
        "notes": "轧制速度偏高，可能导致厚度不均"
    }
    
    # 插入事件并获取ID
    result = db_service.trace_events.insert_one(test_event)
    event_id = result.inserted_id
    
    print(f"成功添加测试事件，ID: {event_id}")
    return str(event_id)

if __name__ == "__main__":
    event_id = add_test_event()
    print(f"可以使用以下命令测试风险评估：")
    print(f"python warehouse_assistant/scripts/test_risk_assessment.py {event_id}") 