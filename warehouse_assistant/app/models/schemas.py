"""
API模型定义模块。
使用Pydantic定义API请求和响应的数据模型。
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# 物料追溯相关模型
class TraceEventResponse(BaseModel):
    """
    追溯事件响应模型。
    用于API返回单个追溯事件的信息。
    """
    timestamp: datetime = Field(..., description="操作发生的时间")
    operation_type: str = Field(..., description="操作类型，如入库、出库、转运、质检等")
    location_name: Optional[str] = Field(None, description="操作发生的地点名称")
    operator_id: Optional[str] = Field(None, description="操作人员ID")
    operator_name: Optional[str] = Field(None, description="操作人员姓名")
    quantity: Optional[float] = Field(None, description="操作涉及的数量")
    unit: Optional[str] = Field(None, description="数量单位")
    notes: Optional[str] = Field(None, description="备注信息")
    
    # 新增字段
    related_docs: Optional[List[Dict[str, Any]]] = Field(None, description="相关文档信息列表")
    equipment_params: Optional[Dict[str, Any]] = Field(None, description="设备参数，如温度、压力、速度等")
    quality_inspection: Optional[Dict[str, Any]] = Field(None, description="质检结果详情，包含各项指标及结果")
    defect_info: Optional[Dict[str, Any]] = Field(None, description="缺陷信息，如缺陷类型、严重程度、位置等")
    risk_assessment: Optional[Dict[str, Any]] = Field(None, description="风险评估信息，如风险等级、潜在问题等")
    material_properties: Optional[Dict[str, Any]] = Field(None, description="物料特性，如成分、规格、特性等")
    
    class Config:
        """Pydantic配置类"""
        json_encoders = {
            # 自定义JSON编码器，处理datetime类型
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "timestamp": "2023-08-15T10:30:00",
                "operation_type": "入库",
                "location_name": "原料仓库-A区",
                "operator_id": "OP001",
                "operator_name": "张三",
                "quantity": 50.5,
                "unit": "吨",
                "notes": "正常入库",
                "related_docs": [
                    {
                        "doc_id": "RK12345",
                        "doc_type": "入库单",
                        "file_name": "入库单_20230815_001.pdf",
                        "url": "https://storage.example.com/inbound/1234.pdf"
                    }
                ],
                "equipment_params": {
                    "equipment_id": "EQ001",
                    "equipment_type": "叉车",
                    "operation_time": 45.8,
                    "load_capacity": 5.0
                },
                "quality_inspection": {
                    "inspector_id": "QC001",
                    "inspection_time": "2023-08-15T11:00:00",
                    "overall_result": "合格",
                    "metrics": [
                        {"name": "硬度", "value": 85.6, "unit": "HRC", "standard": "≥80", "result": "合格"},
                        {"name": "抗拉强度", "value": 620, "unit": "MPa", "standard": "≥580", "result": "合格"}
                    ]
                },
                "defect_info": None,
                "risk_assessment": None,
                "material_properties": {
                    "material_type": "Q235B",
                    "thickness": 1.5,
                    "width": 1200,
                    "length": 3000,
                    "surface_treatment": "热镀锌"
                }
            }
        }

class TraceResponse(BaseModel):
    """
    物料追溯响应模型。
    用于API返回完整的物料追溯信息。
    """
    batch_id: str = Field(..., description="批次号")
    events_count: int = Field(..., description="追溯事件数量")
    events: List[TraceEventResponse] = Field(..., description="追溯事件列表，按时间排序")
    
    class Config:
        """Pydantic配置类"""
        json_schema_extra = {
            "example": {
                "batch_id": "P20230815001",
                "events_count": 2,
                "events": [
                    {
                        "timestamp": "2023-08-15T10:30:00",
                        "operation_type": "入库",
                        "location_name": "原料仓库-A区",
                        "operator_id": "OP001",
                        "operator_name": "张三",
                        "quantity": 50.5,
                        "unit": "吨",
                        "notes": "正常入库",
                        "related_docs": [
                            {
                                "doc_id": "RK12345",
                                "doc_type": "入库单",
                                "file_name": "入库单_20230815_001.pdf",
                                "url": "https://storage.example.com/inbound/1234.pdf"
                            }
                        ],
                        "equipment_params": {
                            "equipment_id": "EQ001",
                            "equipment_type": "叉车",
                            "operation_time": 45.8,
                            "load_capacity": 5.0
                        },
                        "quality_inspection": None,
                        "defect_info": None,
                        "risk_assessment": None,
                        "material_properties": {
                            "material_type": "Q235B",
                            "thickness": 1.5,
                            "width": 1200,
                            "length": 3000,
                            "surface_treatment": "热镀锌"
                        }
                    },
                    {
                        "timestamp": "2023-08-16T14:20:00",
                        "operation_type": "质检",
                        "location_name": "质检中心",
                        "operator_id": "OP002",
                        "operator_name": "李四",
                        "quantity": 50.5,
                        "unit": "吨",
                        "notes": "例行质检",
                        "related_docs": [],
                        "equipment_params": {
                            "equipment_id": "TS001",
                            "equipment_type": "拉力试验机",
                            "last_calibration": "2023-07-01",
                            "accuracy": "±0.5%"
                        },
                        "quality_inspection": {
                            "inspector_id": "QC002",
                            "inspection_time": "2023-08-16T14:30:00",
                            "overall_result": "合格",
                            "metrics": [
                                {"name": "硬度", "value": 85.6, "unit": "HRC", "standard": "≥80", "result": "合格"},
                                {"name": "抗拉强度", "value": 620, "unit": "MPa", "standard": "≥580", "result": "合格"}
                            ]
                        },
                        "defect_info": None,
                        "risk_assessment": None,
                        "material_properties": {
                            "material_type": "Q235B",
                            "thickness": 1.5,
                            "width": 1200,
                            "length": 3000,
                            "surface_treatment": "热镀锌"
                        }
                    }
                ]
            }
        }

class RiskAssessmentResponse(BaseModel):
    """风险评估结果响应模型"""
    event_id: str = Field(..., description="事件ID")
    batch_id: str = Field(..., description="批次ID")
    operation_type: str = Field(..., description="操作类型")
    timestamp: datetime = Field(..., description="事件时间")
    risk_assessment: Optional[Dict[str, Any]] = Field(None, description="风险评估结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "67ff485b72a67bbac831e9c8",
                "batch_id": "BATCH-2025-04-16-001",
                "operation_type": "热轧",
                "timestamp": "2025-04-16T14:04:11.230Z",
                "risk_assessment": {
                    "risk_level": "高",
                    "risk_type": "参数偏差",
                    "reason": "轧制速度超出标准范围，可能导致厚度不均",
                    "suggestion": "降低轧制速度至20米/分钟以下，增加质检频率"
                }
            }
        }
