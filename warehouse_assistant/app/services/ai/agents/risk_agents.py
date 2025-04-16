from crewai import Agent
from langchain_openai import ChatOpenAI  # 使用langchain_openai
from warehouse_assistant.app.core.config import settings #导入配置
from warehouse_assistant.app.services.ai.tools.db_tools import GetEventTool, UpdateRiskTool
from warehouse_assistant.app.services.ai.tools.knowledge_tools import KnowledgeSearchTool
import logging
import os

logger = logging.getLogger(__name__)

# --- DeepSeek 官方 API 配置 ---
# 优先从环境变量获取，提供一个明确的占位符
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY_PLACEHOLDER")
# 使用带提供商前缀的模型名称
DEEPSEEK_MODEL_WITH_PROVIDER = "deepseek/deepseek-chat"  # 或者 "deepseek/deepseek-coder"

# 配置 DeepSeek LLM
try:
    # 检查 DeepSeek API Key
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "YOUR_DEEPSEEK_API_KEY_PLACEHOLDER":
        raise ValueError("DeepSeek API Key 未配置。请设置 DEEPSEEK_API_KEY 环境变量。")
    
    logger.info(f"使用 DeepSeek 模型 (带提供商前缀): {DEEPSEEK_MODEL_WITH_PROVIDER}")
    
    # 创建 ChatOpenAI 实例，明确传入模型名称和 API Key
    llm = ChatOpenAI(
        model=DEEPSEEK_MODEL_WITH_PROVIDER,
        api_key=DEEPSEEK_API_KEY,
        temperature=0.7,
        max_tokens=2000
    )
    
    logger.info("已初始化LLM，使用DeepSeek官方API")
except Exception as ve: # 捕获配置错误
    logger.error(f"LLM 配置错误: {ve}")
    raise ve # 重新抛出，组织应用继续运行
except Exception as e:
    logger.error(f"使用DeepSeek初始化LLM失败: {e}。请检查 API Key 和网络连接。", exc_info=True)
    raise e

# 初始化工具
get_event_tool = GetEventTool()
update_risk_tool = UpdateRiskTool()
knowledge_search_tool = KnowledgeSearchTool()

# 定义Agent
data_fetcher_agent = Agent(
    role="追溯事件数据获取器",
    goal="使用提供的唯一 MongoDB ObjectId 字符串，从数据库中检索特定追溯事件的完整数据记录。",
    backstory=(
        "你是一位数据库查询专家。你的唯一任务是使用提供的事件 ID 和 'get_trace_event_details' 工具来获取相应的事件数据。"
        "你不需要解读数据，只需准确地检索它。"
    ),
    llm=llm,  # 使用配置好的LLM
    verbose=True,
    allow_delegation=False,
)

knowledge_retriever_agent = Agent(
    role="企业知识检索专家",
    goal=(
        "基于给定追溯事件的详细信息（如操作类型、参数、位置、质检结果），智能地搜索企业知识库，"
        "以查找相关的标准操作程序（SOP）、质量标准、设备规格或已记录的历史风险模式，这些信息有助于评估该事件。"
    ),
    backstory=(
        "你擅长理解操作背景，并将其转化为针对向量知识库的有效搜索查询。"
        "你使用 'knowledge_base_search' 工具来查找与风险分析最相关的信息。"
    ),
    llm=llm,  # 使用配置好的LLM
    verbose=True,
    allow_delegation=False,
)

risk_analyzer_agent = Agent(
    role="钢铁仓储运营风险分析师",
    goal=(
        "结合从知识库检索到的相关信息，分析提供的追溯事件数据。"
        "将事件细节（例如，设备参数、质量指标、过程持续时间、位置）与文档化的标准或典型模式进行比较。"
        "识别任何偏差、异常或违规行为。基于此分析，确定风险评估结果，包括："
        "1. 'risk_level'（风险等级：'高', '中', '低', 或 '无'）。"
        "2. 'risk_type'（风险类型：例如，'参数偏差', '质量问题', '程序违规', '操作延迟', '数据不一致', '无'）。"
        "3. 'reason'（原因：对评估的简明解释）。"
        "4. （可选）'suggestion'（建议：简短的后续行动或预防措施）。"
        "将评估结果严格以 JSON 对象格式输出。"
    ),
    backstory=(
        "你是一位严谨的分析师，对钢铁仓储流程和质量控制有深入了解。"
        "你会根据既定规范和知识库背景严格评估运营数据。"
        "你的输出是一个结构化、可操作的 JSON 格式风险评估报告。"
        "你不直接使用工具，而是综合处理提供给你的信息。"
    ),
    llm=llm,  # 使用配置好的LLM
    verbose=True,
    allow_delegation=False,
)

result_writer_agent = Agent(
    role="风险评估数据库更新器",
    goal=(
        "获取分析师生成的最终 JSON 风险评估结果，并使用 'update_event_risk_assessment' 工具，"
        "通过事件的 ObjectId 字符串，将此信息持久化（写回）到 MongoDB 数据库中特定的追溯事件记录里。"
    ),
    backstory=(
        "你是一个可靠的数据库交互代理。你的工作是确保最终的分析结果（JSON 风险评估）使用提供的工具和事件 ID，"
        "被正确地关联并保存到相应的事件记录中。准确性和确认是关键。"
    ),
    llm=llm,  # 使用配置好的LLM
    verbose=True,
    allow_delegation=False,
)




