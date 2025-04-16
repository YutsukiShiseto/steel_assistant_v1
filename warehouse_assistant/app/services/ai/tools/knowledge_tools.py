from typing import Type, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from warehouse_assistant.app.services.ai.knowledge_base import get_knowledge_service
import logging
import json

from crewai.tools import BaseTool  # 只导入BaseTool

logger = logging.getLogger(__name__)

class KnowledgeSearchInput(BaseModel):
    query: str = Field(description="The search query for the knowledge base.")
    k: int = Field(default=3, description="Number of most relevant results to return.")

class KnowledgeSearchTool(BaseTool):
    """用于搜索知识库的工具"""
    
    name: str = "knowledge_search_tool"
    description: str = "搜索知识库中与查询相关的内容"
    
    def _run(self, query: str, k: int = 3) -> str:
        """运行知识库搜索工具"""
        try:
            logger.info(f"开始搜索知识库，查询: {query}, 返回结果数: {k}")
            knowledge_service = get_knowledge_service()
            results = knowledge_service.search(query, k=k)
            logger.info(f"知识库搜索完成，找到 {len(results)} 条结果")
            
            # 记录搜索结果的摘要
            for i, result in enumerate(results):
                content_preview = result.get('content', '')[:100] + '...' if len(result.get('content', '')) > 100 else result.get('content', '')
                logger.info(f"知识库结果 {i+1}: {content_preview}")
            
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}", exc_info=True)
            return f"知识库搜索失败: {str(e)}"

# 创建工具实例
knowledge_search_tool = KnowledgeSearchTool()


