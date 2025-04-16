# 智能仓储助手 - 后端与 AI 服务

## 1. 项目背景

国家"十四五"规划明确提出要推进产业数字化转型，加快智能制造步伐。工信部《钢铁工业智能制造实施指南》也强调了生产制造全流程数字化、网络化、智能化的重要性。然而，在钢铁仓储领域，依然面临着**知识传承难**（专家经验难复制、新员工培训周期长、标准执行不一致）和**物料追溯慢**（系统数据割裂、跨部门协作效率低、问题定位耗时）的核心痛点。此外，对于流转过程中的**潜在风险识别不足**，可能导致质量问题或安全隐患。

本项目旨在通过构建智能化的后端服务与 AI 工作流，集中解决上述痛点，助力钢铁仓储实现"问得清、查得到、防得住"的目标。

## 2. 项目目标

本项目聚焦于后端服务和 AI 能力的建设，主要目标包括：

*   **构建智能问答服务:** 利用 CrewAI 和 LangChain，结合企业知识库，提供一个能够理解用户意图、精准检索信息并生成清晰答案的智能问答助手接口。
*   **开发高效物料追溯服务:** 提供稳定、高效的 API 接口，支持通过批次号等标识符快速查询物料的全生命周期流转信息。
*   **实现物料流转过程中的实时风险分析与预警:** 利用 CrewAI 和向量知识库，自动分析新产生的物料流转事件，识别潜在的操作违规、参数异常或历史相似风险。
*   **实现服务层核心逻辑:** 使用 Python 和 FastAPI 框架开发健壮、可扩展的后端应用，支撑前端应用的功能需求。

## 3. 核心功能 (后端视角)

### 3.1 智能问答助手 (AI 服务)

*(此部分保持不变，详细描述见原文件)*
*   **API 接口:** `POST /api/ask`
*   **AI 工作流 (CrewAI & LangChain):**
    *   **数据处理:** 向量化知识文档存入 ChromaDB。
    *   **Agent 设计:** IntentAnalyzer, KnowledgeRetriever, InfoEvaluator, AnswerGenerator。
    *   **Crew 定义:** 顺序执行 Agent。
*   **FastAPI 实现:** 实现 `/api/ask` 路由，调用 CrewAI 工作流。

### 3.2 物料追溯与实时风险分析 (数据与 AI 服务)

此功能旨在解决"物料追溯慢"和"风险识别不足"的问题，提供快速、准确的物料流转信息查询能力，并**自动对新的流转事件进行风险评估**。

*   **API 接口 (查询):**
    *   `GET /api/trace/{identifier_type}/{identifier_value}` 或 `GET /api/trace?batch_id={batch_id}`: 查询指定标识符物料的**历史追溯信息，包括已完成的风险分析结果**。风险分析本身是后台自动进行的。
*   **后台实时风险分析工作流:**
    *   **触发机制:**
        *   **首选方案: MongoDB Change Streams:** 在 FastAPI 后端应用中启动一个后台任务，实时监听 MongoDB 中 `product_traces` 集合的 `insert` 或 `update` 操作。这是最高效、实时性最好的方式。
        *   **备选方案: 定时轮询 (Polling):** 使用 `APScheduler` 等库创建后台定时任务，每隔一段时间查询数据库，找出上次检查后新增或修改的记录。延迟较高，但实现相对简单。
        *   **备选方案: 消息队列 (Message Queue):** 在数据写入 MongoDB 的同时，将包含关键信息（如 `_id`, `batch_id`）的消息发送到消息队列（如 RabbitMQ, Kafka）。一个独立的风险分析服务或后台任务作为消费者监听队列。解耦性好，但增加了架构复杂度。
    *   **向量知识库 (ChromaDB):**
        *   **构建:** 收集企业知识文档（SOP、操作规程、质量标准、历史风险案例、设备维护手册等）。
        *   **处理:** 使用 LangChain 进行文本切割、添加元数据（来源、类型、风险等级等）。
        *   **存储:** 使用合适的 Embedding 模型（如 Sentence Transformers）将文本块转换为向量，并与文本、元数据一同存入 ChromaDB。
    *   **CrewAI 工作流 (风险分析):**
        *   **Agent 1: 数据获取器 (DataFetcher Agent):**
            *   **任务:** 根据触发机制传递的信息（如 `event_id`, `batch_id`），从 MongoDB 中获取完整的事件数据以及必要的上下文信息（例如，该批次之前的相关事件）。
            *   **工具:** PyMongo/Motor 客户端。
            *   **输入:** 事件标识符 (`_id` 或 `batch_id`)。
            *   **输出:** 结构化的事件数据和上下文信息。
        *   **Agent 2: 知识检索器 (KnowledgeRetriever Agent):**
            *   **任务:** 分析事件数据（如操作类型、物料规格、设备读数、操作地点），提取关键特征，然后查询 ChromaDB 向量知识库，检索相关的企业标准、操作规范、历史相似风险案例等。
            *   **工具:** 配置好的 LangChain Retriever (连接到 ChromaDB)。
            *   **输入:** 结构化的事件数据和上下文信息。
            *   **输出:** 相关知识片段列表（包含内容和元数据）。
        *   **Agent 3: 风险分析师 (RiskAnalyzer Agent):**
            *   **任务:** 结合事件数据和从知识库检索到的信息，调用 LLM 判断当前事件是否存在潜在风险。评估风险等级（例如：高、中、低、无）、风险类型（例如：操作违规、参数异常、设备关联风险、历史相似风险），并生成简明的风险分析说明或原因。
            *   **工具:** LLM API 调用 (通过 LangChain 或直接调用)。
            *   **输入:** 事件数据、上下文信息、检索到的知识片段。
            *   **输出:** 风险评估结果（等级、类型、原因）。
        *   **Agent 4: 结果写入器 (ResultWriter Agent):**
            *   **任务:** 将风险分析师生成的风险评估结果更新回 MongoDB 中对应的 `product_traces` 事件记录中（例如，添加 `risk_level`, `risk_type`, `risk_reason` 字段），或者写入一个专门的风险事件集合中。
            *   **工具:** PyMongo/Motor 客户端。
            *   **输入:** 事件标识符、风险评估结果。
            *   **输出:** 数据库写入操作的状态。
    *   **Crew 定义:**
        *   **流程:** 编排上述 Agent 按顺序或特定逻辑执行。
        *   **模型:** 配置合适的 LLM。
*   **数据库交互 (MongoDB):**
    *   **数据模型:** `product_traces` 集合需要增加用于存储风险分析结果的字段，例如：
        *   `risk_level`: Optional[str] (e.g., "High", "Medium", "Low", "None")
        *   `risk_type`: Optional[str] (e.g., "Operational Violation", "Parameter Anomaly", "Historical Similarity")
        *   `risk_reason`: Optional[str] (Text description of the risk)
        *   `analysis_timestamp`: Optional[datetime.datetime] (Timestamp of when the analysis was completed)
    *   **查询逻辑 (for `/api/trace`):**
        *   接收 API 请求中的查询参数（如 `batch_id`）。
        *   使用 PyMongo/Motor 查询 `product_traces` 集合，获取包含风险分析字段在内的完整流转记录。
        *   按 `timestamp` 排序。
*   **FastAPI 实现:**
    *   实现 `/api/trace/...` GET 路由，用于查询历史追溯信息（包含风险结果）。
    *   实现后台任务（使用 FastAPI Background Tasks, APScheduler, or a separate process/service）来运行数据库变更监听器和触发 CrewAI 风险分析工作流。
    *   调用封装好的数据库查询逻辑。
    *   将查询结果格式化为包含风险信息的 JSON 响应。
    *   处理查询不到结果或数据库错误的情况。

## 4. 技术栈 (后端与 AI)

*   **编程语言:** Python 3.9+
*   **Web 框架:** FastAPI
*   **AI 工作流:** CrewAI
*   **AI 基础库:** LangChain (用于文本处理、向量存储交互、工具集成、LLM 调用)
*   **数据库:** MongoDB (用于存储物料追溯数据及风险分析结果)
*   **数据库访问:** PyMongo/Motor (用于与 MongoDB 交互，包括 Change Streams)
*   **向量数据库:** ChromaDB (用于存储知识库向量)
*   **后台任务 (可选):** APScheduler (如果使用轮询方式)

## 5. 开发流程 (后端与 AI 核心任务)

1.  **环境搭建:**
    *   设置 Python 虚拟环境。
    *   安装 FastAPI, Uvicorn, CrewAI, LangChain, pymongo[srv], motor, chromadb, sentence-transformers, python-dotenv, apscheduler (可选) 等依赖。
2.  **构建向量知识库 (ChromaDB):**
    *   编写脚本或服务，负责收集、处理（切割、加元数据）、向量化知识文档，并存入 ChromaDB。
3.  **智能问答助手开发:**
    *   *(此部分保持不变，参考原文件)*
4.  **物料追溯查询与风险分析服务开发:**
    *   **与数据层协作:** 确认 MongoDB `product_traces` 集合结构，包括新增的风险字段。确认索引设计。
    *   **实现数据库变更监听器:**
        *   选择监听方式 (Change Streams 优先)。
        *   在 FastAPI 应用中实现后台逻辑，监听 `product_traces` 变化，并在检测到新事件时触发风险分析流程。
    *   **风险分析 CrewAI 开发:**
        *   实现 `DataFetcher`, `KnowledgeRetriever`, `RiskAnalyzer`, `ResultWriter` 四个 Agent 类。
        *   为 `KnowledgeRetriever` 配置 LangChain Retriever 工具以连接 ChromaDB。
        *   为 `DataFetcher` 和 `ResultWriter` 配置 MongoDB 操作工具。
        *   编写清晰的 Prompt 指导 `RiskAnalyzer`。
        *   定义包含这些 Agent 的 Crew，设置执行流程和 LLM。
    *   **数据库查询逻辑实现 (for API):**
        *   实现根据 `batch_id` 等查询 `product_traces` 记录（包含风险字段）的函数。
    *   **FastAPI 接口开发 (`/api/trace`):**
        *   定义 `/api/trace/...` GET 路由。
        *   调用数据库查询逻辑函数。
        *   定义包含风险字段的响应模型 (Pydantic)。
        *   处理未找到记录或数据库错误。
5.  **配置与部署准备:**
    *   使用 `.env` 文件管理敏感配置。
    *   编写 `Dockerfile`。
    *   配置 Uvicorn/Gunicorn。

## 6. API 接口定义 (示例)
python
示例：用于说明接口契约，非实际运行代码
使用 Pydantic 定义数据模型，FastAPI 会自动处理数据校验和文档生成
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import datetime
--- 智能问答 ---
class AskRequest(BaseModel):
"""
智能问答请求体模型。
"""
question: str = Field(..., description="用户提出的问题文本", examples=["钢卷堆放有什么要求？"])
user_id: Optional[str] = Field(None, description="用户唯一标识符，可选")
session_id: Optional[str] = Field(None, description="会话ID，可选")
class SourceDocument(BaseModel):
"""
答案来源文档信息模型。
"""
title: Optional[str] = Field(None, description="来源文档标题或名称", examples=["SOP-仓储-001"])
type: Optional[str] = Field(None, description="来源类型", examples=["SOP"])
snippet: Optional[str] = Field(None, description="相关的文本片段摘要")
class AskResponse(BaseModel):
"""
智能问答响应体模型。
"""
answer: str = Field(..., description="由 AI 生成的最终答案文本")
sources: List[SourceDocument] = Field([], description="答案所依据的来源文档信息列表")
debug_info: Optional[Dict[str, Any]] = Field(None, description="内部调试信息，可选")
FastAPI 路由定义 (示意性注释)
@app.post("/api/ask", response_model=AskResponse, summary="智能问答接口")
async def handle_ask(request: AskRequest):
"""接收用户问题，调用 CrewAI 工作流处理并返回答案。"""
pass
--- 物料追溯与风险分析 ---
class TraceEvent(BaseModel):
"""
单个物料追溯事件模型 (包含风险分析结果)。
描述物料生命周期中的一个具体操作节点及其风险评估。
"""
event_id: str = Field(..., description="事件唯一标识符 (例如 MongoDB ObjectId)", examples=["60f1b9b3b6a9a7b3d8f0b1a2"])
timestamp: datetime.datetime = Field(..., description="操作发生的精确时间", examples=["2024-07-26T10:30:00Z"])
operation_type: str = Field(..., description="操作类型", examples=["入库", "出库", "转运", "质检"])
location_name: Optional[str] = Field(None, description="操作发生的地点名称", examples=["A区-01架", "质检中心"])
operator_name: Optional[str] = Field(None, description="执行操作的员工姓名", examples=["张三"])
quantity: Optional[float] = Field(None, description="该操作涉及的物料数量", examples=[10.5])
unit: Optional[str] = Field(None, description="数量单位", examples=["吨"])
notes: Optional[str] = Field(None, description="与此事件相关的备注信息", examples=["客户紧急订单"])
# 新增风险分析相关字段
risk_level: Optional[str] = Field(None, description="风险等级评估结果", examples=["Medium", "Low", "None"])
risk_type: Optional[str] = Field(None, description="风险类型", examples=["Parameter Anomaly", "Operational Violation"])
risk_reason: Optional[str] = Field(None, description="风险分析说明", examples=["检测到温度超出标准范围", "未按规定使用垫木"])
analysis_timestamp: Optional[datetime.datetime] = Field(None, description="风险分析完成时间", examples=["2024-07-26T10:35:00Z"])
# 可以根据实际数据库模型添加其他字段
class TraceResponse(BaseModel):
"""
物料追溯响应体模型。
包含查询标识符和按时间排序的追溯事件列表（含风险信息）。
"""
identifier: str = Field(..., description="用于查询的标识符值 (例如批次号)", examples=["P20240726001"])
identifier_type: str = Field(..., description="查询使用的标识符类型", examples=["batch_id"])
trace_events: List[TraceEvent] = Field(..., description="按时间顺序排列的物料追溯事件列表 (包含风险分析结果)")
FastAPI 路由定义 (示意性注释)
@app.get("/api/trace/{identifier_type}/{identifier_value}",
response_model=TraceResponse,
summary="物料追溯查询接口 (含风险分析结果)")
async def handle_trace(identifier_type: str, identifier_value: str):
"""
根据指定的标识符类型和值，查询物料的历史追溯信息，包括后台自动完成的风险分析结果。
#
- identifier_type: 标识符类型 (路径参数, 如 'batch_id', 'scan_code').
- identifier_value: 标识符的具体值 (路径参数).
- return: 包含追溯事件列表（含风险信息）的响应体。
"""
# 1. 校验 identifier_type
# 2. 调用数据库服务层函数查询 (包含风险字段)
# trace_data = await get_trace_from_db_with_risk(identifier_type, identifier_value)
# 3. 处理未找到记录 (404)
# 4. 转换数据为 TraceEvent 列表
# 5. 构建 TraceResponse 对象
# 6. 返回响应
# 7. 处理数据库异常
pass
注意：风险分析本身由后台任务（如监听 MongoDB Change Streams）触发 CrewAI 工作流自动完成，
并将结果写回数据库。此 API 仅用于查询包含这些结果的历史记录。
## 7. 部署 (待定)
## 8. 项目结构 (建议调整)
warehouse_assistant/
├── app/
│ ├── init.py
│ ├── main.py # FastAPI 应用入口, 可能包含后台任务启动
│ ├── api/ # API 路由
│ │ ├── init.py
│ │ └── routes/
│ │ ├── init.py
│ │ ├── ask.py # 问答接口路由
│ │ └── trace.py # 追溯查询接口路由
│ ├── core/ # 核心配置
│ │ ├── init.py
│ │ └── config.py # 配置管理 (环境变量、数据库连接等)
│ ├── models/ # 数据模型
│ │ ├── init.py
│ │ ├── schemas.py # Pydantic API 模型 (AskRequest, TraceResponse 等)
│ │ └── database.py # MongoDB 数据模型 (如果使用 ODM 如 Beanie) 或常量
│ ├── services/ # 业务逻辑与外部服务交互
│ │ ├── init.py
│ │ ├── ai/ # AI 相关服务
│ │ │ ├── init.py
│ │ │ ├── agents/ # CrewAI Agent 定义 (问答 + 风险分析)
│ │ │ │ ├── init.py
│ │ │ │ ├── ask_agents.py
│ │ │ │ └── risk_agents.py
│ │ │ ├── crews/ # CrewAI Crew 定义
│ │ │ │ ├── init.py
│ │ │ │ ├── ask_crew.py
│ │ │ │ └── risk_crew.py
│ │ │ ├── tools/ # LangChain 工具 (知识库检索, DB 操作等)
│ │ │ │ ├── init.py
│ │ │ │ └── knowledge_tools.py
│ │ │ └── knowledge_base.py # 知识库管理/交互 (ChromaDB)
│ │ ├── database/ # 数据库交互逻辑
│ │ │ ├── init.py
│ │ │ └── mongo_service.py # MongoDB 查询/写入函数
│ │ └── background/ # 后台任务相关
│ │ ├── init.py
│ │ └── change_stream_listener.py # MongoDB Change Stream 监听器逻辑
│ ├── utils/ # 通用工具函数
│ │ └── init.py
├── .env # 环境变量
├── requirements.txt # 依赖列表
├── scripts/ # 辅助脚本 (如知识库初始化)
│ └── init_knowledge_base.py
└── README.md # 项目说明文档


---

**注意:** 本文档聚焦于后端服务和 AI 工作流的规划与设计。前端界面、数据库的具体搭建、数据迁移、ETL 过程以及车辆管理功能的实现细节，均不在此文档的覆盖范围内。