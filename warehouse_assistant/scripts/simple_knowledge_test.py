"""简单知识库测试脚本"""
import sys
import os
from pathlib import Path
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取项目根目录
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
logger.info(f"当前目录: {os.getcwd()}")
logger.info(f"项目根目录: {project_root}")

# 添加项目根目录到Python路径
sys.path.insert(0, str(project_root))
logger.info(f"Python路径: {project_root}")

# 导入知识库服务
from warehouse_assistant.app.services.ai.knowledge_base import get_knowledge_service

def test_simple_knowledge_retrieval():
    """测试基本的知识库检索功能"""
    try:
        # 获取知识库服务实例
        logger.info("获取知识库服务实例...")
        kb_service = get_knowledge_service()
        
        # 测试查询
        test_queries = [
            "钢材热轧温度标准范围",
            "质检不合格处理流程",
            "设备参数异常判断标准"
        ]
        
        for query in test_queries:
            logger.info(f"执行查询: {query}")
            results = kb_service.search(query, k=2)
            
            logger.info(f"查询 '{query}' 返回 {len(results)} 条结果")
            
            # 打印结果摘要
            for i, result in enumerate(results):
                content = result.get('content', '')[:100] + '...' if len(result.get('content', '')) > 100 else result.get('content', '')
                logger.info(f"结果 {i+1}: {content}")
                
        logger.info("知识库测试完成")
        return True
    except Exception as e:
        logger.error(f"知识库测试失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_simple_knowledge_retrieval()
    print(f"\n测试结果: {'成功' if success else '失败'}") 