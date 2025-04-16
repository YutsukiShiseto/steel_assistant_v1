"""
测试风险评估功能
手动触发对特定事件的风险评估
"""
import sys
import os
from pathlib import Path
import argparse

# 设置Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from warehouse_assistant.app.services.ai.crews.risk_crew import run_risk_assessment_for_event

def test_risk_assessment(event_id):
    """测试对特定事件的风险评估"""
    print(f"开始对事件 {event_id} 进行风险评估...")
    run_risk_assessment_for_event(event_id)
    print("风险评估任务已启动，请检查日志和数据库中的结果")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试风险评估功能")
    parser.add_argument("event_id", help="要评估的事件ID")
    args = parser.parse_args()
    
    test_risk_assessment(args.event_id) 