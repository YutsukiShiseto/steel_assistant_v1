import os
from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 确定项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 添加DeepSeek API相关配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat")

class Settings(BaseSettings):
    # MongoDB 设置
    MONGODB_CONNECTION_STRING: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "warehouse_assistant"


    # ChromaDB 设置
    # 使用 os.path.join 确保路径正确
    CHROMA_PERSIST_DIRECTORY: str = os.path.join(BASE_DIR, "chroma_db_store")
    KNOWLEDGE_BASE_COLLECTION_NAME: str = "enterprise_knowledge_base"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


    # 火山引擎 DeepSeek 设置
    VOLCANO_API_KEY: str = os.getenv("ARK_API_KEY")
    VOLCANO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    VOLCANO_MODEL_ENDPOINT_ID: str = os.getenv("MODEL_ENDPOINT_ID")
    

    # 应用设置
    LOG_LEVEL: str = "INFO"

    # DeepSeek API配置
    DEEPSEEK_API_KEY: str = DEEPSEEK_API_KEY
    DEEPSEEK_MODEL: str = DEEPSEEK_MODEL
    
    class Config:
        # 指定 .env 文件路径，相对于BASE_DIR
        env_file = os.path.join(BASE_DIR, ".env")
        env_file_encoding = 'utf-8'
        extra = 'ignore' # 忽略 .env 文件中多余的变量

# 创建配置实例，方便全局导入使用
settings = Settings()

# 配置日志
import logging
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Configuration loaded.")
# 打印关键配置以供检查
logger.info(f"Using LLM Endpoint ID: {settings.VOLCANO_MODEL_ENDPOINT_ID}")
logger.info(f"Using LLM Base URL: {settings.VOLCANO_BASE_URL}")
# 出于安全考虑，避免直接打印 API Key
if settings.VOLCANO_API_KEY and settings.VOLCANO_API_KEY != "YOUR_ARK_API_KEY_HERE":
    logger.info("Volcano API Key is set.")
else:
    logger.warning("Volcano API Key is NOT set or using placeholder!")
logger.info(f"ChromaDB Path: {settings.CHROMA_PERSIST_DIRECTORY}")
