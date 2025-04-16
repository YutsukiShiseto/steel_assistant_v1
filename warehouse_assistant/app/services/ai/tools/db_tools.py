from typing import Type, Optional, Dict, Any
from pydantic import BaseModel, Field as PydanticField # 避免与 crewai 的 Field 冲突
from warehouse_assistant.app.services.database.mongo_service import get_db_service # 使用获取实例的函数
import logging
import json
from warehouse_assistant.app.services.database.mongo_service import JSONEncoder # 导入自定义编码器
from crewai.tools import BaseTool  # 只导入BaseTool
from bson import ObjectId


logger = logging.getLogger(__name__)

# 工具是同步执行的，如果数据库操作耗时，会阻塞 CrewAI
# 考虑使用异步工具和异步 CrewAI（如果场景需要高并发）

class GetEventInput(BaseModel):
    event_id: str = PydanticField(description="The MongoDB ObjectId string of the trace event to fetch.")

class GetEventTool(BaseTool):
    """用于获取事件数据的工具"""
    
    name: str = "get_event_tool"
    description: str = "获取指定ID的事件数据"
    
    def _run(self, event_id: str) -> str:
        """
        获取指定ID的事件数据
        
        Args:
            event_id: 事件ID
            
        Returns:
            事件数据的JSON字符串
        """
        try:
            logger.info(f"获取事件数据: {event_id}")
            db_service = get_db_service()
            event = db_service.get_event_by_id(event_id)
            
            if not event:
                return json.dumps({"error": f"未找到ID为 {event_id} 的事件"})
            
            # 将ObjectId转换为字符串
            if "_id" in event:
                event["_id"] = str(event["_id"])
            
            return json.dumps(event, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"获取事件数据时出错: {e}", exc_info=True)
            return json.dumps({"error": f"获取事件数据失败: {str(e)}"})

    async def _arun(self, event_id: str) -> str:
        # 对于同步数据库操作，异步包装可能只是简单的委托
        # 如果使用 Motor (异步 MongoDB驱动)，这里可以实现真正的异步
        return self._run(event_id)

class UpdateRiskInput(BaseModel):
    event_id: str = PydanticField(description="The MongoDB ObjectId string of the trace event to update.")
    risk_assessment: Dict[str, Any] = PydanticField(
        description="A dictionary containing the risk assessment details (e.g., risk_level, risk_type, reason)."
    )

class UpdateRiskTool(BaseTool):
    """用于更新事件风险评估的工具"""
    
    name: str = "update_risk_tool"
    description: str = "更新指定事件的风险评估结果"
    
    def _run(self, event_id: str, risk_assessment: Dict[str, Any]) -> str:
        """
        更新指定事件的风险评估结果
        
        Args:
            event_id: 事件ID
            risk_assessment: 风险评估结果
            
        Returns:
            更新结果的描述
        """
        try:
            logger.info(f"更新事件风险评估: {event_id}")
            
            # 如果risk_assessment是字符串，尝试解析为JSON
            if isinstance(risk_assessment, str):
                try:
                    risk_assessment = json.loads(risk_assessment)
                except json.JSONDecodeError:
                    return f"风险评估数据格式错误: {risk_assessment}"
            
            db_service = get_db_service()
            success = db_service.update_event_risk(event_id, risk_assessment)
            
            if success:
                return f"Successfully updated risk assessment for event {event_id}"
            else:
                return f"Failed to update risk assessment for event {event_id}"
        except Exception as e:
            logger.error(f"更新事件风险评估时出错: {e}", exc_info=True)
            return f"更新风险评估失败: {str(e)}"
    
    async def _arun(self, event_id: str, risk_assessment: Dict[str, Any]) -> str:
        return self._run(event_id, risk_assessment)

# 创建工具实例
get_event_tool = GetEventTool()
update_risk_tool = UpdateRiskTool()
