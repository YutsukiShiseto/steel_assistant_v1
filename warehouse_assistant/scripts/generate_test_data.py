"""
生成模拟钢材批次全生命周期的测试数据并插入到MongoDB数据库
"""
import sys
import os
from pathlib import Path
import logging
import random
import argparse
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import threading
import time
from typing import List, Dict, Any, Optional

# 设置Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from warehouse_assistant.app.core.config import settings

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试数据模板 - 更丰富的操作类型
TEST_OPERATIONS = [
    "原料入库", "炼铁", "炼钢", "连铸", "热轧", "冷轧", "退火", "酸洗", "镀锌", 
    "精整", "检验", "包装", "成品入库", "出库"
]

# 更丰富的位置信息
TEST_LOCATIONS = [
    "原料库", "高炉车间", "转炉车间", "连铸车间", "热轧车间", "冷轧车间", 
    "退火车间", "酸洗车间", "镀锌车间", "精整车间", "质检区", "成品库", "运输中" # 添加运输状态
]

# 钢材规格
STEEL_SPECS = [
    "Q235B", "Q345B", "Q355B", "Q420B", "Q460B", "SPHC", "SPCC", "SGCC", 
    "08Al", "DC01", "DC03", "DC04", "S235JR", "S275JR", "S355JR"
]

# 钢材类型
STEEL_TYPES = [
    "热轧板卷", "冷轧板卷", "镀锌板卷", "彩涂板卷", "中厚板", "型钢", "线材", "棒材"
]

# 客户信息
CUSTOMERS = [
    "上海汽车制造有限公司", "北京建筑工程集团", "广州船舶工业公司", 
    "深圳电子科技有限公司", "天津机械制造厂", "重庆钢结构工程有限公司"
]

# 操作人员
OPERATORS = [
    {"id": "OP001", "name": "张工"},
    {"id": "OP002", "name": "李工"},
    {"id": "OP003", "name": "王工"},
    {"id": "OP004", "name": "赵工"},
    {"id": "OP005", "name": "刘工"},
    {"id": "OP006", "name": "陈工"},
    {"id": "OP007", "name": "周工"}
]

# 设备信息
EQUIPMENT = [
    {"id": "EQ001", "name": "1号高炉", "type": "高炉"},
    {"id": "EQ002", "name": "2号转炉", "type": "转炉"},
    {"id": "EQ003", "name": "1号连铸机", "type": "连铸机"},
    {"id": "EQ004", "name": "热轧主机组", "type": "热轧机"},
    {"id": "EQ005", "name": "冷轧机组", "type": "冷轧机"},
    {"id": "EQ006", "name": "连续退火线", "type": "退火炉"},
    {"id": "EQ007", "name": "酸洗线", "type": "酸洗设备"},
    {"id": "EQ008", "name": "镀锌线", "type": "镀锌设备"},
    {"id": "EQ009", "name": "精整线", "type": "精整设备"},
    {"id": "EQ010", "name": "检测设备", "type": "检测仪器"},
    {"id": "TRUCK01", "name": "运输卡车A", "type": "运输工具"},
    {"id": "CRANE01", "name": "仓库吊车", "type": "搬运设备"}
]

def get_equipment_for_operation(operation_type: str) -> Dict[str, Any]:
    """根据操作类型选择合适的设备"""
    op_lower = operation_type.lower()
    possible_equipment = []
    if "入库" in op_lower or "出库" in op_lower or "包装" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] in ["搬运设备", "运输工具"]]
    elif "炼铁" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "高炉"]
    elif "炼钢" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "转炉"]
    elif "连铸" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "连铸机"]
    elif "热轧" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "热轧机"]
    elif "冷轧" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "冷轧机"]
    elif "退火" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "退火炉"]
    elif "酸洗" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "酸洗设备"]
    elif "镀锌" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "镀锌设备"]
    elif "精整" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "精整设备"]
    elif "检验" in op_lower:
        possible_equipment = [e for e in EQUIPMENT if e["type"] == "检测仪器"]
    # 如果没有匹配到特定设备，随机选一个非运输设备
    if not possible_equipment:
        possible_equipment = [e for e in EQUIPMENT if e["type"] not in ["运输工具"]]

    return random.choice(possible_equipment) if possible_equipment else random.choice(EQUIPMENT)

def generate_operation_parameters(operation_type: str) -> Dict[str, Any]:
    """根据操作类型生成更详细、随机化的参数"""
    params = {}
    # 基础参数
    params["duration_minutes"] = random.randint(10, 240) # 操作持续时间（分钟）
    params["energy_consumption_kwh"] = round(random.uniform(50, 1000) * (params["duration_minutes"] / 60), 2)

    # 特定操作参数 (示例，需要根据实际工艺细化)
    if operation_type == "炼铁":
        params["temperature_celsius"] = random.randint(1400, 1600)
        params["iron_content_percent"] = round(random.uniform(94.5, 96.5), 2)
        params["sulfur_content_percent"] = round(random.uniform(0.02, 0.05), 3)
        params["slag_basicity"] = round(random.uniform(1.0, 1.3), 2)
    elif operation_type == "炼钢":
        params["temperature_celsius"] = random.randint(1600, 1700)
        params["carbon_content_percent"] = round(random.uniform(0.05, 0.8), 3) # 范围更广
        params["manganese_content_percent"] = round(random.uniform(0.3, 1.5), 2)
        params["oxygen_ppm"] = random.randint(200, 800) # 吹氧量或钢水氧含量
    elif operation_type == "连铸":
        params["casting_speed_m_min"] = round(random.uniform(0.8, 1.5), 2)
        params["cooling_water_flow_m3_h"] = random.randint(500, 1500)
        params["mold_oscillation_freq_hz"] = round(random.uniform(1.0, 3.0), 1)
    elif operation_type == "热轧":
        params["entry_temperature_celsius"] = random.randint(1100, 1250)
        params["exit_temperature_celsius"] = random.randint(850, 950)
        params["rolling_speed_m_s"] = round(random.uniform(5, 15), 1)
        params["reduction_percent"] = round(random.uniform(10, 30), 1) # 道次压下率
        params["target_thickness_mm"] = round(random.uniform(1.5, 10.0), 2)
    elif operation_type == "冷轧":
        params["rolling_force_kn"] = random.randint(10000, 25000)
        params["tension_kn"] = random.randint(50, 200)
        params["exit_thickness_mm"] = round(random.uniform(0.3, 2.0), 2)
    elif operation_type == "退火":
        params["soaking_temperature_celsius"] = random.randint(650, 800)
        params["soaking_time_minutes"] = random.randint(60, 180)
        params["atmosphere_composition"] = random.choice(["H2/N2", "N2", "Exogas"])
    elif operation_type == "检验":
        params["sample_taken"] = True
        params["test_items"] = random.sample(["尺寸", "表面", "成分", "力学性能", "硬度"], k=random.randint(2, 5))
    elif operation_type == "包装":
        params["packaging_type"] = random.choice(["标准出口包装", "国内简易包装", "客户指定包装"])
        params["weight_kg"] = round(random.uniform(1000, 25000), 1) # 包装后的重量
    elif operation_type == "出库":
        params["destination"] = random.choice(CUSTOMERS)
        params["vehicle_plate"] = f"沪A-{random.randint(10000, 99999)}"

    # 随机加入一些通用参数
    if random.random() < 0.3:
        params["humidity_percent"] = random.randint(40, 80)
    if random.random() < 0.3:
        params["vibration_level"] = round(random.uniform(0.1, 1.5), 2)

    return params

def generate_material_properties(operation_type: str, previous_properties: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """生成材料属性，可能基于前一阶段属性演变"""
    if operation_type in ["原料入库", "炼铁"]: # 早期阶段可能没有明确的钢材属性
        return None
    elif previous_properties and operation_type not in ["炼钢"]: # 继承大部分属性，除非是炼钢改变成分
        props = previous_properties.copy()
        # 可能在某些工序后更新特定属性，例如退火后更新力学性能
        if operation_type == "退火":
            props["tensile_strength_mpa"] = round(props.get("tensile_strength_mpa", random.randint(300, 500)) * random.uniform(0.9, 1.0), 1) # 退火可能降低强度
            props["elongation_percent"] = round(props.get("elongation_percent", random.randint(20, 40)) * random.uniform(1.0, 1.1), 1) # 退火可能增加延伸率
        elif operation_type == "热轧" or operation_type == "冷轧":
             props["thickness_mm"] = round(random.uniform(0.3, 10.0), 2) # 厚度会变化
        return props
    else: # 炼钢或首次生成属性
        spec = random.choice(STEEL_SPECS)
        stype = random.choice(STEEL_TYPES)
        return {
            "steel_spec": spec,
            "steel_type": stype,
            "chemical_composition": { # 示例成分
                "C": round(random.uniform(0.05, 0.4), 3),
                "Si": round(random.uniform(0.1, 0.5), 3),
                "Mn": round(random.uniform(0.3, 1.5), 3),
                "P": round(random.uniform(0.01, 0.04), 3),
                "S": round(random.uniform(0.01, 0.04), 3),
            },
            "tensile_strength_mpa": random.randint(300, 700),
            "yield_strength_mpa": random.randint(200, 500),
            "elongation_percent": random.randint(15, 40),
            "hardness_hb": random.randint(100, 250),
            "thickness_mm": round(random.uniform(0.5, 10.0), 2), # 初始厚度
            "width_mm": random.randint(1000, 2000),
        }

def generate_quality_inspection(operation_type: str) -> Optional[Dict[str, Any]]:
    """根据操作类型生成质量检验信息"""
    if operation_type not in ["检验", "精整", "成品入库"]: # 只在特定阶段进行检验
        return None

    results = {}
    has_defect = random.random() < 0.1 # 10%的几率有缺陷
    results["inspection_time"] = datetime.now(timezone.utc).isoformat()
    results["inspector_id"] = random.choice(OPERATORS)["id"]
    results["overall_result"] = "不合格" if has_defect else "合格"

    # 模拟一些检验项
    results["surface_check"] = "有划痕" if has_defect and random.random() < 0.5 else "合格"
    results["dimension_check"] = "厚度超差" if has_defect and random.random() >= 0.5 else "合格"
    if operation_type == "检验":
        results["composition_analysis"] = "合格"
        results["mechanical_test"] = "合格"

    if has_defect:
        results["defect_info"] = {
            "has_defect": True,
            "defect_type": random.choice(["表面划痕", "尺寸偏差", "成分不符", "性能不达标"]),
            "defect_description": "检测到轻微问题，待处理" if random.random() > 0.3 else "严重缺陷，建议隔离",
            "severity": "轻微" if random.random() > 0.3 else "严重"
        }
    else:
         results["defect_info"] = {"has_defect": False}

    return results

def define_batch_lifecycle() -> List[str]:
    """定义一个典型的钢材批次生命周期流程"""
    # 可以根据需要定义多种流程模板
    return [
        "原料入库", "炼铁", "炼钢", "连铸", "热轧", "酸洗", "冷轧", "退火", "镀锌", "精整", "检验", "包装", "成品入库", "出库"
    ]

def generate_event_for_step(batch_id: str, operation_type: str, previous_event: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """为生命周期中的一个步骤生成事件数据"""
    # 计算时间戳
    if previous_event and previous_event.get("timestamp"):
        # 在上一个事件时间戳基础上增加随机时间（模拟处理和等待时间）
        time_delta_hours = random.uniform(1, 48) # 随机增加1到48小时
        timestamp = previous_event["timestamp"] + timedelta(hours=time_delta_hours)
    else:
        # 第一个事件的时间戳
        timestamp = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 5)) # 从过去几天开始

    location = random.choice([loc for loc in TEST_LOCATIONS if operation_type.split(" ")[0] in loc or "车间" in loc or "库" in loc or "区" in loc]) \
               if any(operation_type.split(" ")[0] in loc for loc in TEST_LOCATIONS) else random.choice(TEST_LOCATIONS)
    operator = random.choice(OPERATORS)
    equipment = get_equipment_for_operation(operation_type)

    # 获取上一个事件的材料属性（如果存在）
    prev_material_props = previous_event.get("material_properties") if previous_event else None
    material_properties = generate_material_properties(operation_type, prev_material_props)

    event = {
        "batch_id": batch_id,
        "operation_type": operation_type,
        "location": location,
        "timestamp": timestamp,
        "operator_id": operator["id"],
        "operator_name": operator["name"],
        "equipment_id": equipment["id"],
        "equipment_name": equipment["name"],
        "parameters": generate_operation_parameters(operation_type),
        "material_properties": material_properties,
        "quality_inspection": generate_quality_inspection(operation_type),
        "notes": f"{operation_type} 阶段记录。" + (" 轻微延迟。" if random.random() < 0.05 else ""),
        "related_docs": [], # 可以添加相关文档ID或路径
        # "previous_event_id": str(previous_event["_id"]) if previous_event and "_id" in previous_event else None, # 可选：添加前序事件ID链接
        # --- 不包含 risk_assessment 字段 ---
    }

    # 清理空值字段，保持数据整洁
    event = {k: v for k, v in event.items() if v is not None}

    # 如果是出库，添加客户信息
    if operation_type == "出库":
        event["customer"] = random.choice(CUSTOMERS)
        event["order_number"] = f"ORD-{batch_id[-4:]}-{random.randint(100, 999)}"

    return event

def generate_batch_lifecycle_events(batch_id: str) -> List[Dict[str, Any]]:
    """为一个批次生成完整的生命周期事件列表"""
    lifecycle_steps = define_batch_lifecycle()
    batch_events = []
    previous_event = None
    for step in lifecycle_steps:
        current_event = generate_event_for_step(batch_id, step, previous_event)
        batch_events.append(current_event)
        # 为下一次迭代准备 'previous_event'，即使没有 _id 也可以传递时间戳和属性
        previous_event = current_event
        # 可以在事件之间加入微小的随机延时，使时间戳更真实
        time.sleep(random.uniform(0.01, 0.05))
    return batch_events

def insert_batch_events(batches_to_generate: int = 1, interval_between_events: float = 0.1):
    """生成指定数量批次的生命周期事件并插入MongoDB"""
    all_inserted_ids = {}
    try:
        client = MongoClient(settings.MONGODB_CONNECTION_STRING)
        db = client[settings.MONGODB_DB_NAME]
        collection = db["trace_events"]
        logger.info(f"连接到 MongoDB: {settings.MONGODB_DB_NAME}, 集合: trace_events")

        for i in range(batches_to_generate):
            # 生成唯一的批次ID
            batch_id = f"BATCH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
            logger.info(f"--- 开始生成批次 {i+1}/{batches_to_generate} 的生命周期事件: {batch_id} ---")

            batch_events = generate_batch_lifecycle_events(batch_id)
            batch_inserted_ids = []

            logger.info(f"为批次 {batch_id} 生成了 {len(batch_events)} 个事件，准备插入...")

            initial_count = collection.count_documents({})
            logger.info(f"插入前集合中有 {initial_count} 个文档")

            for j, event in enumerate(batch_events):
                # 打印将要插入的事件（用于调试）
                # logger.debug(f"准备插入事件 {j+1}/{len(batch_events)} for batch {batch_id}: {event}")
                try:
                    result = collection.insert_one(event)
                    inserted_id = result.inserted_id
                    batch_inserted_ids.append(inserted_id)
                    logger.info(f"  插入事件 {j+1}/{len(batch_events)} (Op: {event['operation_type']}): ID={inserted_id}")

                    # 如果设置了间隔，则等待
                    if interval_between_events > 0 and j < len(batch_events) - 1:
                        # logger.debug(f"等待 {interval_between_events} 秒...")
                        time.sleep(interval_between_events)
                except Exception as insert_error:
                     logger.error(f"插入事件时出错 (Batch: {batch_id}, Op: {event.get('operation_type', 'N/A')}): {insert_error}", exc_info=True)
                     logger.error(f"出错的事件数据: {event}")


            final_count = collection.count_documents({})
            logger.info(f"插入后集合中有 {final_count} 个文档，本次批次新增 {final_count - initial_count} 个")
            logger.info(f"批次 {batch_id} 插入完成，共 {len(batch_inserted_ids)} 个事件。")
            all_inserted_ids[batch_id] = [str(id) for id in batch_inserted_ids]
            logger.info(f"--- 批次 {batch_id} 生成结束 ---")

        client.close()
        return all_inserted_ids

    except Exception as e:
        logger.error(f"生成或插入批次事件时出错: {e}", exc_info=True)
        return {}

def background_insert_batches(batches_to_generate, interval_between_events):
    """在后台线程中插入批次事件"""
    thread = threading.Thread(target=insert_batch_events, args=(batches_to_generate, interval_between_events))
    thread.daemon = True
    thread.start()
    return thread

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成模拟钢材批次全生命周期的测试数据")
    parser.add_argument("--batches", type=int, default=1, help="要生成的批次数量，默认为1")
    parser.add_argument("--interval", type=float, default=0.1, help="同一批次内事件插入的最小间隔（秒），默认为0.1")
    parser.add_argument("--background", action="store_true", help="在后台运行，立即返回")

    args = parser.parse_args()

    logger.info(f"开始生成 {args.batches} 个批次的生命周期事件...")

    if args.background:
        thread = background_insert_batches(args.batches, args.interval)
        logger.info(f"已在后台启动数据生成任务，将生成 {args.batches} 个批次，事件间隔约 {args.interval} 秒")
        logger.info("主程序可以继续运行，数据将在后台生成")
    else:
        inserted_batch_data = insert_batch_events(args.batches, args.interval)

        if inserted_batch_data:
            logger.info("测试数据生成完成。生成的批次及事件ID:")
            for batch_id, event_ids in inserted_batch_data.items():
                 logger.info(f"  批次: {batch_id}")
                 # for k, event_id in enumerate(event_ids):
                 #     logger.info(f"    {k+1}. {event_id}") # 可以取消注释以显示每个事件ID
        else:
            logger.error("未能成功生成任何测试数据。") 