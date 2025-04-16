from fastapi import APIRouter, HTTPException
from typing import Dict
import asyncio
from warehouse_assistant.app.core.config import settings
from warehouse_assistant.app.services.ai.crews.risk_crew import run_risk_assessment_for_event
from warehouse_assistant.app.services.ai.tools.db_tools import get_trace_event
from warehouse_assistant.app.services.background.event_tracker import get_event_tracker
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/risk/{event_id}/assess", response_model=Dict[str, str])
async def assess_event_risk(event_id: str):
    """
    手动触发对特定事件的风险评估。
    
    Args:
        event_id: 要评估的事件ID
        
    Returns:
        包含状态和消息的字典
    """
    try:
        logger.info(f"收到为事件运行风险评估的请求：{event_id}")
        
        # 检查事件是否存在
        event = await get_trace_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail=f"事件 {event_id} 不存在")
        
        # 使用事件跟踪器检查是否已处理或正在处理
        event_tracker = get_event_tracker()
        if event_tracker.is_processing(event_id):
            return {"status": "in_progress", "message": f"事件 {event_id} 正在处理中"}
        
        if event_tracker.has_processed(event_id):
            return {"status": "already_processed", "message": f"事件 {event_id} 已处理过"}
        
        # 标记为处理中
        if not event_tracker.mark_as_processing(event_id):
            return {"status": "error", "message": f"无法标记事件 {event_id} 为处理中状态"}
        
        # 异步运行风险评估
        result = await asyncio.to_thread(run_risk_assessment_for_event, event_id)
        
        # 标记为已处理
        success = result.get('status') == 'success'
        event_tracker.mark_as_processed(event_id, success)
        
        return {"status": "success", "message": f"风险评估已触发，结果: {result}"}
    except Exception as e:
        logger.error(f"触发风险评估时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"触发风险评估失败: {str(e)}") 