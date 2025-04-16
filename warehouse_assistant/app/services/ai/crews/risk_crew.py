from crewai import Crew, Process, Task
import logging
from warehouse_assistant.app.services.ai.agents.risk_agents import (
    data_fetcher_agent, knowledge_retriever_agent, 
    risk_analyzer_agent, result_writer_agent,
    get_event_tool, update_risk_tool, knowledge_search_tool
)

logger = logging.getLogger(__name__)

class RiskAssessmentCrew:
    """
    风险评估Crew，负责协调多个Agent完成对事件的风险评估。
    """

    def __init__(self, event_id: str):
        """
        初始化风险评估Crew。
        
        Args:
            event_id: 要评估的事件ID
        """
        self.event_id = event_id
        
        # 为Agent添加工具 - 使用正确的方式添加工具
        data_fetcher_agent.tools = [get_event_tool]
        knowledge_retriever_agent.tools = [knowledge_search_tool]
        result_writer_agent.tools = [update_risk_tool]
        
        # 创建任务
        fetch_data_task = Task(
            description=f"获取事件ID为 {event_id} 的完整数据",
            expected_output="事件的完整JSON数据",
            agent=data_fetcher_agent
        )
        
        retrieve_knowledge_task = Task(
            description="基于事件数据，从知识库中检索相关的标准、规范或历史风险模式",
            expected_output="与事件相关的知识库内容",
            agent=knowledge_retriever_agent
        )
        
        analyze_risk_task = Task(
            description="分析事件数据和知识库信息，评估潜在风险并提出建议",
            expected_output="包含风险等级、类型、原因和建议的风险评估结果",
            agent=risk_analyzer_agent
        )
        
        write_result_task = Task(
            description=f"将风险评估结果更新到事件 {event_id} 中",
            expected_output="更新操作的结果确认",
            agent=result_writer_agent
        )
        
        # 创建Crew
        self.crew = Crew(
            agents=[
                data_fetcher_agent,
                knowledge_retriever_agent,
                risk_analyzer_agent,
                result_writer_agent
            ],
            tasks=[
                fetch_data_task,
                retrieve_knowledge_task,
                analyze_risk_task,
                write_result_task
            ],
            process=Process.sequential,
            verbose=True,
            memory=False
        )
    
    def run(self):
        """
        运行风险评估Crew。
        
        Returns:
            风险评估的结果
        """
        try:
            logger.info(f"开始为事件 {self.event_id} 运行风险评估，将使用知识库进行分析")
            
            # 运行Crew
            result = self.crew.kickoff()
            
            # 记录原始结果以便调试
            logger.info(f"Crew返回的原始结果: '{result}'")
            
            # 更宽松的成功判断逻辑
            if isinstance(result, str):
                result_lower = result.lower()
                success_indicators = ["success", "updated", "完成", "成功"]
                
                if any(indicator in result_lower for indicator in success_indicators):
                    logger.info(f"事件 {self.event_id} 的风险评估成功完成: {result}")
                    return {"status": "success", "message": result}
            
            # 如果不符合成功条件，则视为失败
            logger.error(f"事件 {self.event_id} 的风险评估更新可能失败。最后输出: {result}")
            return {"status": "error", "message": f"更新失败或确认信息不明确: {result}"}
            
        except Exception as e:
            logger.error(f"执行 event_id {self.event_id} 的 Crew 流程时发生异常: {e}", exc_info=True)
            return {"status": "error", "message": f"Crew 执行失败: {str(e)}"}

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
