"""
数据库模型定义模块。
定义MongoDB集合的结构和字段。
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

# 物料追溯事件集合结构
class TraceEvent:
    """
    物料追溯事件模型。
    描述物料生命周期中的一个具体操作节点。
    """
    def __init__(
        self,
        batch_id: str,
        timestamp: datetime,
        operation_type: str,
        location_name: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
        related_docs: Optional[List[Dict[str, Any]]] = None,
        equipment_params: Optional[Dict[str, Union[float, str, bool]]] = None,
        quality_inspection: Optional[Dict[str, Any]] = None,
        defect_info: Optional[Dict[str, Any]] = None,
        risk_assessment: Optional[Dict[str, Any]] = None,
        material_properties: Optional[Dict[str, Any]] = None
    ):
        """
        初始化追溯事件。
        
        Args:
            batch_id: 批次号
            timestamp: 操作发生的时间
            operation_type: 操作类型（如入库、出库、转运、质检）
            location_name: 操作发生的地点名称
            operator_id: 操作人员ID
            operator_name: 操作人员姓名
            quantity: 操作涉及的数量
            unit: 数量单位
            notes: 备注信息
            related_docs: 相关文档信息
            
            # 新增字段
            equipment_params: 设备参数，如温度、压力、速度等
            quality_inspection: 质检结果详情，包含各项指标及结果
            defect_info: 缺陷信息，如缺陷类型、严重程度、位置等
            risk_assessment: 风险评估信息，如风险等级、潜在问题、预防措施等
            material_properties: 物料特性，如成分、规格、特性等
        """
        self.batch_id = batch_id
        self.timestamp = timestamp
        self.operation_type = operation_type
        self.location_name = location_name
        self.operator_id = operator_id
        self.operator_name = operator_name
        self.quantity = quantity
        self.unit = unit
        self.notes = notes
        self.related_docs = related_docs or []
        
        # 新增字段初始化
        self.equipment_params = equipment_params
        self.quality_inspection = quality_inspection
        self.defect_info = defect_info
        self.risk_assessment = risk_assessment
        self.material_properties = material_properties
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将对象转换为字典，用于MongoDB存储。
        
        Returns:
            包含所有字段的字典
        """
        return {
            "batch_id": self.batch_id,
            "timestamp": self.timestamp,
            "operation_type": self.operation_type,
            "location_name": self.location_name,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "notes": self.notes,
            "related_docs": self.related_docs,
            
            # 新增字段
            "equipment_params": self.equipment_params,
            "quality_inspection": self.quality_inspection,
            "defect_info": self.defect_info,
            "risk_assessment": self.risk_assessment,
            "material_properties": self.material_properties
        } 