import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from typing import List, Optional, Type, Dict, Any
import logging
from warehouse_assistant.app.core.config import settings # 导入配置实例
import glob  # 导入 glob 模块用于查找文件
from dotenv import load_dotenv
# 不再需要从 langchain_community.document_loaders 导入 DirectoryLoader
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import traceback
import chromadb

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    _instance = None
    vectorstore: Optional[Chroma] = None
    embeddings: Optional[HuggingFaceEmbeddings] = None

    def __new__(cls):
        # 单例模式，确保只初始化一次
        if cls._instance is None:
            logger.info("Initializing KnowledgeBaseService instance...")
            cls._instance = super(KnowledgeBaseService, cls).__new__(cls)
            # 在初始化时加载向量数据库
            cls._instance._load_vectorstore()
        return cls._instance
    
    def _load_vectorstore(self):
        """初始化或加载向量数据库"""
        try:
            # 加载预训练的嵌入模型
            logger.info(f"Loading embeddings model: {settings.EMBEDDING_MODEL_NAME}")
            self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
            
            # 确保持久化目录存在
            os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
            
            # 尝试加载向量数据库
            logger.info(f"Loading vectorstore from: {settings.CHROMA_PERSIST_DIRECTORY}")
            
            try:
                # 首先检查集合是否存在
                client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
                collections = client.list_collections()
                collection_exists = any(c.name == settings.KNOWLEDGE_BASE_COLLECTION_NAME for c in collections)
                
                if collection_exists:
                    self.vectorstore = Chroma(
                        persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
                        embedding_function=self.embeddings,
                        collection_name=settings.KNOWLEDGE_BASE_COLLECTION_NAME
                    )
                    logger.info(f"Successfully loaded existing vectorstore with {self.vectorstore._collection.count()} documents")
                else:
                    logger.warning(f"Collection '{settings.KNOWLEDGE_BASE_COLLECTION_NAME}' does not exist in ChromaDB. Please run init_knowledge_base.py script first.")
                    self.vectorstore = None
                    
            except Exception as e:
                logger.error(f"Failed to load vectorstore: {e}", exc_info=True)
                self.vectorstore = None
                
        except Exception as e:
            logger.error(f"Error initializing embeddings: {e}", exc_info=True)
            self.embeddings = None
            self.vectorstore = None

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            k: 返回的最相关结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"搜索知识库: {query}, k={k}")
            
            # 使用向量存储进行搜索
            docs = self.vectorstore.similarity_search_with_score(query, k=k)
            
            # 格式化结果
            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)  # 确保分数是可序列化的
                })
            
            logger.info(f"搜索完成，找到 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"搜索知识库时出错: {e}", exc_info=True)
            return []  # 返回空列表而不是抛出异常，避免中断流程
    

# 创建单例实例，应用启动时或首次导入时会加载数据库
knowledge_service = KnowledgeBaseService()

# 提供一个获取服务实例的函数
def get_knowledge_service() -> KnowledgeBaseService:
     """获取知识库服务的单例实例。"""
     # 直接返回在模块级别创建的实例
     # 如果 KnowledgeBaseService 没有正确初始化，这里会返回 None 或引发错误，需要调用方处理
     global knowledge_service
     if knowledge_service is None:
         # 尝试重新初始化，或者记录错误
         logger.warning("Knowledge service instance was None, attempting re-initialization.")
         knowledge_service = KnowledgeBaseService()
     elif knowledge_service.vectorstore is None:
         # 如果实例存在但 vectorstore 未加载，也尝试重新加载
          logger.warning("Knowledge service vectorstore is None, attempting reload.")
          knowledge_service._load_vectorstore()

     return knowledge_service
# --- 函数添加结束 ---


