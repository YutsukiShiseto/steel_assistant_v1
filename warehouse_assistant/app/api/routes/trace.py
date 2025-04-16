"""
物料追溯API路由模块。
提供物料追溯相关的API接口。
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime

from warehouse_assistant.app.models.schemas import TraceResponse, TraceEventResponse, RiskAssessmentResponse
from warehouse_assistant.app.services.database import DatabaseService
from warehouse_assistant.app.services.ai.crews.risk_crew import run_risk_assessment_for_event

import logging

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/api/trace",
    tags=["trace"],
    responses={404: {"description": "未找到"}}
)

# 依赖项：获取数据库服务实例
def get_db_service():
    """
    依赖项函数，用于获取数据库服务实例。
    
    在请求处理完成后会自动关闭数据库连接。
    
    Returns:
        DatabaseService: 数据库服务实例
    """
    db_service = DatabaseService()
    try:
        yield db_service
    finally:
        db_service.close()

@router.get("", response_model=TraceResponse)
async def trace_by_batch_id(
    batch_id: str = Query(..., description="批次号，例如：P20230815001"),
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    根据批次号查询物料追溯信息。
    
    Args:
        batch_id: 批次号
        db_service: 数据库服务实例（通过依赖注入）
    
    Returns:
        TraceResponse: 包含追溯事件列表的响应
    
    Raises:
        HTTPException: 当找不到指定批次号的追溯信息时抛出404错误
    """
    # 从数据库查询追溯事件
    trace_events = db_service.get_trace_events_by_batch_id(batch_id)
    
    # 如果没有找到追溯事件，抛出404错误
    if not trace_events:
        raise HTTPException(
            status_code=404,
            detail=f"未找到批次号为 {batch_id} 的追溯信息"
        )
    
    # 将数据库查询结果转换为API响应模型
    events = [
        TraceEventResponse(
            timestamp=event["timestamp"],
            operation_type=event["operation_type"],
            location_name=event.get("location_name"),
            operator_id=event.get("operator_id"),
            operator_name=event.get("operator_name"),
            quantity=event.get("quantity"),
            unit=event.get("unit"),
            notes=event.get("notes"),
            related_docs=event.get("related_docs"),
            equipment_params=event.get("equipment_params"),
            quality_inspection=event.get("quality_inspection"),
            defect_info=event.get("defect_info"),
            risk_assessment=event.get("risk_assessment"),
            material_properties=event.get("material_properties")
        )
        for event in trace_events
    ]
    
    # 构建并返回响应
    return TraceResponse(
        batch_id=batch_id,
        events_count=len(events),
        events=events
    )

@router.get("/{batch_id}", response_model=TraceResponse)
async def trace_by_batch_id_path(
    batch_id: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    根据批次号查询物料追溯信息（路径参数版本）。
    
    这是一个替代路由，允许通过路径参数而非查询参数来指定批次号。
    功能与 trace_by_batch_id 相同。
    
    Args:
        batch_id: 批次号（路径参数）
        db_service: 数据库服务实例（通过依赖注入）
    
    Returns:
        TraceResponse: 包含追溯事件列表的响应
    
    Raises:
        HTTPException: 当找不到指定批次号的追溯信息时抛出404错误
    """
    # 从数据库查询追溯事件
    trace_events = db_service.get_trace_events_by_batch_id(batch_id)
    
    # 如果没有找到追溯事件，抛出404错误
    if not trace_events:
        raise HTTPException(
            status_code=404,
            detail=f"未找到批次号为 {batch_id} 的追溯信息"
        )
    
    # 将数据库查询结果转换为API响应模型
    events = [
        TraceEventResponse(
            timestamp=event["timestamp"],
            operation_type=event["operation_type"],
            location_name=event.get("location_name"),
            operator_id=event.get("operator_id"),
            operator_name=event.get("operator_name"),
            quantity=event.get("quantity"),
            unit=event.get("unit"),
            notes=event.get("notes"),
            related_docs=event.get("related_docs"),
            equipment_params=event.get("equipment_params"),
            quality_inspection=event.get("quality_inspection"),
            defect_info=event.get("defect_info"),
            risk_assessment=event.get("risk_assessment"),
            material_properties=event.get("material_properties")
        )
        for event in trace_events
    ]
    
    # 构建并返回响应
    return TraceResponse(
        batch_id=batch_id,
        events_count=len(events),
        events=events
    )

@router.get("/risk/{event_id}", response_model=RiskAssessmentResponse)
async def get_event_risk_assessment(
    event_id: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    获取特定事件的风险评估结果
    
    Args:
        event_id: 事件ID (MongoDB ObjectId的字符串表示)
        db_service: 数据库服务实例
        
    Returns:
        包含事件信息和风险评估结果的响应
        
    Raises:
        HTTPException: 当找不到指定ID的事件时抛出404错误
    """
    # 从数据库获取事件
    event = db_service.get_event_by_id(event_id)
    
    # 如果未找到事件，抛出404错误
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"未找到ID为 {event_id} 的事件"
        )
    
    # 构建响应
    return RiskAssessmentResponse(
        event_id=str(event["_id"]),
        batch_id=event.get("batch_id", "未知批次"),
        operation_type=event.get("operation_type", "未知操作"),
        timestamp=event.get("timestamp", datetime.now()),
        risk_assessment=event.get("risk_assessment")
    )

@router.post("/risk/{event_id}/assess", response_model=dict)
async def trigger_risk_assessment(
    event_id: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """
    手动触发对特定事件的风险评估
    
    Args:
        event_id: 事件ID (MongoDB ObjectId的字符串表示)
        db_service: 数据库服务实例
        
    Returns:
        包含操作状态的响应
        
    Raises:
        HTTPException: 当找不到指定ID的事件或评估失败时抛出错误
    """
    # 检查事件是否存在
    event = db_service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"未找到ID为 {event_id} 的事件"
        )
    
    try:
        # 异步触发风险评估
        import asyncio
        asyncio.create_task(run_risk_assessment_in_background(event_id))
        
        return {
            "status": "success",
            "message": f"已成功触发事件 {event_id} 的风险评估，请稍后查询结果",
            "event_id": event_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"触发风险评估失败: {str(e)}"
        )

async def run_risk_assessment_in_background(event_id: str):
    """在后台运行风险评估"""
    try:
        import asyncio
        # 使用线程运行同步函数
        await asyncio.to_thread(run_risk_assessment_for_event, event_id)
    except Exception as e:
        logger.error(f"后台风险评估失败: {e}", exc_info=True) 