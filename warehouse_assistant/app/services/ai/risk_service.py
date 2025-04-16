import logging
from warehouse_assistant.app.services.ai.crews.risk_crew import RiskAssessmentCrew

logger = logging.getLogger(__name__)

def run_risk_assessment_for_event(event_id: str):
    """
    为指定的事件运行风险评估。
    
    Args:
        event_id: 要评估的事件ID
        
    Returns:
        风险评估的结果
    """
    try:
        logger.info(f"开始为事件 {event_id} 运行风险评估...")
        
        # 创建风险评估Crew
        crew = RiskAssessmentCrew(event_id)
        
        # 运行风险评估
        result = crew.run()
        
        logger.info(f"事件 {event_id} 的风险评估完成，结果: {result}")
        return result
    except Exception as e:
        logger.error(f"运行风险评估时出错: {e}", exc_info=True)
        return {"status": "error", "message": f"风险评估失败: {str(e)}"} 