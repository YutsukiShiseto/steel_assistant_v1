import asyncio
import logging
from datetime import datetime, timedelta
from bson import ObjectId
from warehouse_assistant.app.services.database.mongo_service import get_db_service
from warehouse_assistant.app.services.ai.crews.risk_crew import run_risk_assessment_for_event
from warehouse_assistant.app.services.background.event_tracker import get_event_tracker

logger = logging.getLogger(__name__)

# 全局变量
last_check_time = datetime.utcnow()
polling_task = None
stop_event = asyncio.Event()
polling_interval = 30  # 轮询间隔，单位为秒

async def poll_new_events_async():
    """轮询检查新的事件记录"""
    global last_check_time
    event_tracker = get_event_tracker()  # 获取事件跟踪器实例
    
    logger.info("[轮询任务] 开始监听新事件...")
    
    while not stop_event.is_set():
        try:
            db_service = get_db_service()
            if not hasattr(db_service, 'trace_events') or db_service.trace_events is None:
                logger.warning("[轮询任务] 数据库集合未初始化，10秒后重试")
                await asyncio.sleep(10)
                continue
                
            # 查询上次检查后的新记录
            current_time = datetime.utcnow()
            query = {"timestamp": {"$gt": last_check_time, "$lte": current_time}}
            
            # 使用兼容单机版MongoDB的方式查询
            cursor = db_service.trace_events.find(query).sort("timestamp", -1)
            new_events = list(cursor)
            
            # 更新最后检查时间
            if new_events:
                logger.info(f"[轮询任务] 发现 {len(new_events)} 个新事件")
                
                # 处理每个新事件
                for event in new_events:
                    event_id = str(event["_id"])
                    
                    # 检查事件是否已在处理中或已处理过
                    if event_tracker.is_processing(event_id) or event_tracker.has_processed(event_id):
                        logger.info(f"[轮询任务] 事件 {event_id} 已在处理中或已处理过，跳过")
                        continue
                    
                    # 标记事件为处理中
                    if event_tracker.mark_as_processing(event_id):
                        # 异步启动风险评估
                        asyncio.create_task(process_event(event_id))
                
                last_check_time = current_time
            
            # 等待一段时间再检查
            await asyncio.sleep(polling_interval)
            
        except Exception as e:
            logger.error(f"[轮询任务] 检查新事件时出错: {e}", exc_info=True)
            await asyncio.sleep(10)  # 出错后等待10秒再重试

# 添加事件处理函数
async def process_event(event_id: str):
    """处理单个事件"""
    event_tracker = get_event_tracker()
    
    try:
        logger.info(f"[轮询任务] 已为事件 {event_id} 异步启动风险评估")
        
        # 在新线程中运行风险评估（因为它是同步的）
        result = await asyncio.to_thread(run_risk_assessment_for_event, event_id)
        
        logger.info(f"[轮询任务] 事件 {event_id} 的风险评估完成: {result}")
        
        # 标记事件为已处理
        success = result.get('status') == 'success'
        event_tracker.mark_as_processed(event_id, success)
        
    except Exception as e:
        logger.error(f"[轮询任务] 处理事件 {event_id} 时出错: {e}", exc_info=True)
        # 标记事件处理失败
        event_tracker.mark_as_processed(event_id, False)

async def start_polling_task():
    """启动轮询任务"""
    global polling_task, stop_event
    logger.info("正在启动事件轮询监听器...")
    stop_event.clear()
    polling_task = asyncio.create_task(poll_new_events_async())
    logger.info("事件轮询监听器已启动")
    
async def stop_polling_task():
    """停止轮询任务"""
    global polling_task, stop_event
    if polling_task is not None:
        logger.info("正在停止事件轮询监听器...")
        stop_event.set()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        polling_task = None
        logger.info("事件轮询监听器已停止") 