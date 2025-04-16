import asyncio
from motor.motor_asyncio import AsyncIOMotorClient # 导入 motor
from pymongo.errors import PyMongoError, OperationFailure # 使用 pymongo 的错误类型
from warehouse_assistant.app.core.config import settings
from warehouse_assistant.app.services.ai.crews.risk_crew import run_risk_assessment_for_event
import logging
import time 

logger = logging.getLogger(__name__)

# 使用 asyncio.Event 来控制停止
_stop_event = asyncio.Event()
_listener_task = None # 用于存储运行中的监听任务

async def watch_trace_events_async(stop_event: asyncio.Event):
    """异步函数，使用 Motor 监听 MongoDB Change Stream。"""
    client = None
    while not stop_event.is_set():
        try:
            logger.info("[后台任务]正在尝试连接 MongoDB 以启动 Change Stream...")
            # 使用 Motor 建立异步连接
            client = AsyncIOMotorClient(settings.MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=10000)
            # 检查是否连接成功 (motor 连接比较惰性)
            await client.admin.command('ping') # 发送 ping 命令验证连接
            
            db = client[settings.MONGODB_DB_NAME]
            collection = db.trace_events
            logger.info("[后台任务]成功连接到 MongoDB。正在启动 Change Stream 监听器...")

            pipeline = [{'$match': {'operationType':'insert'}}]
            # 使用 async with 异步迭代 Change Stream
            async with collection.watch(pipeline=pipeline, full_document='updateLookup') as stream:
                logger.info("[后台任务] Change Stream 监听器已激活。")
                async for change in stream:
                    if stop_event.is_set():
                        logger.info("[后台任务]收到停止信号，退出监听循环。")
                        break

                    logger.debug(f"[后台任务]检测到变更：{change.get('operationType')}")
                    if change.get('operationType') == 'insert':
                        try:
                            event_id = str(change['documentKey']['_id'])
                            logger.info(f"[后台任务] 检测到新事件插入，ID: {event_id}。正在触发风险评估...")
                            # 异步触发 CrewAI 任务
                            # 由于 run_risk_assessment_for_event 可能是同步/CPU密集型任务
                            # 使用 asyncio.to_thread() 在单独线程中运行它，防止阻塞
                            try:
                                # 将同步函数包装在异步任务中
                                await asyncio.to_thread(run_risk_assessment_for_event, event_id) 
                                logger.info(f"[后台任务] 已为事件 {event_id} 异步启动风险评估。")
                            except Exception as run_err:
                                logger.error(f"[后台任务] 启动事件 {event_id} 的风险评估时出错: {run_err}", exc_info=True)
                        except KeyError as e:
                            logger.error(f"[后台任务] 访问变更文档时发生 KeyError: {e}。变更内容: {change}")
                        except Exception as e:
                            logger.error(f"[后台任务] 处理变更事件 {change.get('documentKey')} 时出错: {e}", exc_info=True)
                    # 在每次迭代后短暂让出控制权，防止事件循环过于繁忙
                    await asyncio.sleep(0.1)

                logger.info("[后台任务] Change Stream 监听结束或被中断。")

        except (ConnectionError, OperationFailure) as e:
            logger.error(f"[后台任务] MongoDB 连接或操作错误: {e}。将在 30 秒后重试...")
        except Exception as e:
            logger.error(f"[后台任务] 监听器发生意外错误: {e}。将在 30 秒后重试...", exc_info=True)
        finally:
            if client:
                client.close() # 关闭 motor 客户端连接
                logger.info("[后台任务] MongoDB 异步连接已关闭。")

        if not stop_event.is_set():
            await asyncio.sleep(30) # 异步等待 30 秒再重试

    logger.info("[后台任务] 监听器任务已完全停止。")

    
def start_change_stream_listener_task():
    """启动 Change Stream 监听器作为 asyncio 任务。"""
    global _listener_task
    if _listener_task is None or _listener_task.done():
        _stop_event.clear() # 重置停止事件
        logger.info("正在启动 MongoDB Change Stream 监听器后台任务...")
        # 使用 asyncio.create_task 启动异步函数
        _listener_task = asyncio.create_task(watch_trace_events_async(_stop_event))
        logger.info("Change Stream 监听器后台任务已启动。")
    else:
        logger.warning("Change Stream 监听器后台任务已在运行中。")

async def stop_change_stream_listener_task():
    """停止 Change Stream 监听器任务。"""
    global _listener_task
    if _listener_task and not _listener_task.done():
        logger.info("正在尝试停止 Change Stream 监听器任务...")
        _stop_event.set() # 发送停止信号
        try:
            # 等待任务结束，设置超时时间
            await asyncio.wait_for(_listener_task, timeout=10.0)
            logger.info("Change Stream 监听器任务已成功停止。")
        except asyncio.TimeoutError:
            logger.warning("监听器任务在 10 秒内未能优雅停止，可能被强制取消。")
            _listener_task.cancel() # 尝试取消任务
            try:
                await _listener_task # 等待取消完成
            except asyncio.CancelledError:
                 logger.info("监听器任务已被取消。")
        except Exception as e:
            logger.error(f"停止监听器任务时发生错误: {e}", exc_info=True)
        finally:
             _listener_task = None # 清理任务引用
    else:
        logger.info("Change Stream 监听器任务未在运行或已停止。")
        _listener_task = None # 确保清理


