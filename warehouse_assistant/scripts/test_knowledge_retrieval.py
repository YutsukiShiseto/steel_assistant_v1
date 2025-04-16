"""测试知识库检索功能"""
import sys
from pathlib import Path
import logging

# 设置Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from warehouse_assistant.app.services.ai.tools.knowledge_tools import knowledge_search_tool

logging.basicConfig(level=logging.INFO)

def test_knowledge_retrieval():
    """测试知识库检索功能"""
    test_queries = [
        "钢材热轧温度标准范围",
        "质检不合格处理流程",
        "设备参数异常判断标准"
    ]
    
    for query in test_queries:
        print(f"\n测试查询: {query}")
        result = knowledge_search_tool._run(query)
        print(f"结果: {result[:500]}...")

if __name__ == "__main__":
    test_knowledge_retrieval() 