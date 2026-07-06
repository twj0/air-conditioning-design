"""
CLTD/CLF 传统冷负荷系数法 Python 实现

模仿天正暖通计算逻辑，基于《实用供热空调设计手册》（第二版）及 ASHRAE Fundamentals
的 CLTD/CLF 表，对五城市办公楼进行逐时冷负荷计算，并与 EnergyPlus 结果对比。

用法: python scripts/run_cltd_load_calculation.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.config.three_story_design import (
    CITY_ENVELOPE_PARAMS,
    FLOOR_DEPTH,
    FLOOR_HEIGHT,
    FLOOR_WIDTH,
    ROOMS,
    RoomSpec,
    total_conditioned_area,
)

# ============================================================================
# 第一部分: CLTD/CLF 数据表
# ============================================================================
# 数据来源: ASHRAE Fundamentals 2009/2013, 实用供热空调设计手册(第二版)
# 墙体类型: Type F (中等热容, 对应 200mm 砖墙+XPS 外保温)
# 屋面类型: 重质屋面 (对应 200mm 钢筋混凝土+XPS 保温)
# 外窗: 双层 3mm 透明玻璃+12mm 空气间层

# --- 1a. 外墙 CLTD (°C) ---
# Type F 墙体 (中等热容), 各朝向逐时值, 已含室外设计温度影响
# 行索引 = 时刻 (0-23), 列 = 朝向
# 基准条件: 室内 25°C, 室外日平均 30°C, 日较差 12°C
WALL_CLTD: dict[str, list[float]] = {
    "S": [
        9, 8, 7, 6, 5, 5, 5, 6, 7, 8, 10, 11,
        12, 13, 14, 14, 14, 14, 13, 12, 11, 10, 10, 9,
    ],
    "N": [
        11, 10, 9, 8, 7, 7, 7, 8, 9, 10, 11, 12,
        13, 13, 13, 13, 12, 11, 10, 10, 9, 9, 10, 11,
    ],
    "W": [
        8, 7, 6, 5, 5, 4, 4, 5, 6, 7, 8, 10,
        11, 13, 15, 17, 18, 19, 19, 18, 16, 14, 12, 10,
    ],
    "E": [
        12, 11, 10, 9, 8, 8, 9, 12, 15, 18, 20, 21,
        21, 20, 19, 18, 16, 15, 14, 13, 12, 12, 12, 12,
    ],
    "H": [  # 水平/屋顶
        6, 5, 4, 3, 3, 3, 4, 5, 7, 9, 12, 15,
        18, 21, 24, 26, 27, 28, 27, 25, 22, 19, 15, 11,
    ],
}

# --- 1b. 屋顶 CLTD (°C) ---
# 重质屋面 (200mm 混凝土+XPS), 已含室外设计温度影响
ROOF_CLTD: list[float] = [
    6, 5, 4, 3, 3, 3, 4, 5, 7, 9, 12, 15,
    18, 21, 24, 26, 27, 28, 27, 25, 22, 19, 15, 11,
]

# --- 1c. 外窗 CLTD (°C) ---
# 标准玻璃窗 (双层), 各朝向逐时值
WINDOW_CLTD: dict[str, list[float]] = {
    "S": [7, 6, 5, 4, 4, 4, 5, 6, 7, 8, 9, 10, 11, 11, 11, 10, 10, 9, 9, 8, 8, 8, 8, 7],
    "N": [8, 7, 6, 5, 5, 5, 6, 7, 8, 9, 10, 11, 11, 11, 10, 10, 9, 9, 8, 8, 8, 8, 8, 8],
    "W": [7, 6, 5, 4, 4, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 14, 14, 13, 12, 11, 10, 9, 8],
    "E": [7, 6, 5, 4, 4, 4, 5, 7, 9, 11, 12, 13, 13, 12, 11, 10, 10, 9, 8, 8, 8, 8, 8, 7],
}

# --- 1d. 太阳辐射得热因子 (W/m²) ---
# 透过标准玻璃的太阳总辐射照度 J_ch_zd, 北纬 30-40°, 各朝向逐时值
# 用于公式: Q_solar = F * Cs * Cn * Ca * [J_ch_zd(t) * C_cl_ch(t) + J_sh_zd(t)]
# 简化: SHGF(t) = J_ch_zd(t), 单位 W/m²
SOLAR_HEAT_GAIN: dict[str, list[float]] = {
    "S": [0, 0, 0, 0, 0, 10, 60, 120, 180, 220, 240, 250, 240, 220, 180, 120, 60, 10, 0, 0, 0, 0, 0, 0],
    "N": [0, 0, 0, 0, 0, 30, 100, 160, 200, 220, 230, 230, 220, 200, 170, 130, 80, 30, 0, 0, 0, 0, 0, 0],
    "W": [0, 0, 0, 0, 0, 10, 40, 70, 100, 130, 160, 230, 320, 410, 480, 510, 490, 420, 300, 160, 50, 0, 0, 0],
    "E": [0, 0, 0, 0, 0, 50, 160, 300, 420, 490, 510, 480, 410, 320, 230, 160, 100, 60, 20, 0, 0, 0, 0, 0],
    "H": [0, 0, 0, 0, 0, 50, 150, 260, 370, 460, 530, 570, 580, 560, 510, 430, 320, 190, 70, 10, 0, 0, 0, 0],
}

# --- 1e. 冷负荷系数 CLF ---
# 人员显热冷负荷系数 (办公, 停留 10h, 8:00-18:00)
# 用于: Q_p_sen(t) = n * q_sen * Cr * CLF_p(t)
PEOPLE_CLF: list[float] = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  # 0-7h
    0.20, 0.38, 0.53, 0.65, 0.74, 0.81, 0.86, 0.90, 0.92, 0.93,  # 8-17h
    0.74, 0.55, 0.36, 0.17, 0.0, 0.0,  # 18-23h
]

# 灯光冷负荷系数 (荧光灯, 开灯 10h, 8:00-18:00)
LIGHT_CLF: list[float] = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.42, 0.69, 0.82, 0.89, 0.93, 0.95, 0.96, 0.97, 0.97, 0.42,
    0.23, 0.15, 0.10, 0.07, 0.04, 0.0,
]

# 设备冷负荷系数 (办公设备, 运行 10h, 8:00-18:00)
EQUIP_CLF: list[float] = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.35, 0.60, 0.75, 0.84, 0.89, 0.92, 0.94, 0.95, 0.96, 0.35,
    0.20, 0.12, 0.08, 0.05, 0.03, 0.0,
]

# 冷负荷系数 - 用于太阳能辐射 (外窗太阳辐射冷负荷系数)
# 各朝向逐时值
SOLAR_CLF: dict[str, list[float]] = {
    "S": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "N": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "W": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "E": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "H": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
}
# 注: 太阳辐射冷负荷系数较复杂, 此处简化处理。
# 中国规范中实际用 J_ch_zd(t) × C_cl_ch(t) 查表乘积, 此处取 C_cl_ch ≈ 0.75 常数
# 故太阳辐射冷负荷 = F * Cs * Cn * Ca * SHGF(t) * 0.75

SOLAR_CLF_FACTOR = 0.75  # 简化系数: 包含 C_cl_ch 平均效应

# ============================================================================
# 第二部分: 建筑参数
# ============================================================================
# ============================================================================
# 第二部分: 三层建筑与房间级参数
# ============================================================================

CITY_PARAMS = CITY_ENVELOPE_PARAMS
CITY_ORDER = ("shenyang", "tianjin", "chengdu", "chongqing", "shenzhen")

T_INDOOR = 26.0
INDOOR_RH = 0.60
Q_SEN_PER_PERSON = 61.0
Q_LAT_PER_PERSON = 73.0
CR = 0.93
H_INDOOR = 58.0
RHO_AIR = 1.13
SOLAR_CLF_FACTOR = 0.75
DEFAULT_WWR = 0.35


def room_people(room: RoomSpec) -> int:
    return max(1, round(room.area / room.people_density_m2_per_person))


def room_exterior_wall_areas(room: RoomSpec) -> dict[str, float]:
    areas: dict[str, float] = {}
    eps = 0.01
    if abs(room.y1) < eps:
        areas["S"] = (room.x2 - room.x1) * FLOOR_HEIGHT
    if abs(room.y2 - FLOOR_DEPTH) < eps:
        areas["N"] = (room.x2 - room.x1) * FLOOR_HEIGHT
    if abs(room.x1) < eps:
        areas["W"] = (room.y2 - room.y1) * FLOOR_HEIGHT
    if abs(room.x2 - FLOOR_WIDTH) < eps:
        areas["E"] = (room.y2 - room.y1) * FLOOR_HEIGHT
    return areas


def room_window_areas(room: RoomSpec, wwr: float = DEFAULT_WWR) -> dict[str, float]:
    if room.room_type in {"archive", "toilet", "stair", "corridor"}:
        wwr *= 0.45
    return {orientation: area * wwr for orientation, area in room_exterior_wall_areas(room).items()}


def cltd_temperature_correction(city: dict, indoor_temp: float = T_INDOOR) -> float:
    return (25.0 - indoor_temp) + (city["t_out_daily_mean"] - 30.0)


# ============================================================================
# 第三部分: 房间级负荷计算
# ============================================================================


def _find_hourly_peak(hourly_loads: list[float]) -> tuple[float, int]:
    peak = max(hourly_loads)
    return peak, hourly_loads.index(peak)


def calc_wall_load(city: dict, room: RoomSpec, hour: int, indoor_temp: float) -> float:
    total = 0.0
    corr = cltd_temperature_correction(city, indoor_temp)
    for orient, area in room_exterior_wall_areas(room).items():
        cltd = WALL_CLTD[orient][hour] + corr + city["t_loc_correction"]
        total += max(0.0, city["K_wall"] * area * cltd)
    return total


def calc_roof_load(city: dict, room: RoomSpec, hour: int, indoor_temp: float) -> float:
    if room.floor != 3:
        return 0.0
    corr = cltd_temperature_correction(city, indoor_temp)
    cltd = ROOF_CLTD[hour] + corr + city["t_loc_correction"]
    return max(0.0, city["K_roof"] * room.area * cltd)


def calc_window_conduction_load(city: dict, room: RoomSpec, hour: int, indoor_temp: float, wwr: float) -> float:
    total = 0.0
    corr = cltd_temperature_correction(city, indoor_temp)
    for orient, area in room_window_areas(room, wwr).items():
        cltd = WINDOW_CLTD[orient][hour] + corr + city["t_loc_correction"]
        total += max(0.0, city["K_win"] * area * cltd * 0.80)
    return total


def calc_window_solar_load(city: dict, room: RoomSpec, hour: int, wwr: float) -> float:
    total = 0.0
    for orient, area in room_window_areas(room, wwr).items():
        shgf = SOLAR_HEAT_GAIN[orient][hour]
        total += area * city["SC"] * 0.75 * 0.85 * shgf * SOLAR_CLF_FACTOR
    return total


def calc_people_load(room: RoomSpec, hour: int) -> float:
    if hour < 8 or hour > 18:
        return 0.0
    n_people = room_people(room)
    q_sensible = n_people * Q_SEN_PER_PERSON * CR * PEOPLE_CLF[hour]
    q_latent = n_people * Q_LAT_PER_PERSON * CR
    return q_sensible + q_latent


def calc_light_load(room: RoomSpec, hour: int) -> float:
    return room.area * room.lighting_w_m2 * 1.2 * LIGHT_CLF[hour]


def calc_equip_load(room: RoomSpec, hour: int, equipment_multiplier: float = 1.0) -> float:
    return room.area * room.equipment_w_m2 * equipment_multiplier * EQUIP_CLF[hour]


def calc_fresh_air_load(city: dict, room: RoomSpec, hour: int, fresh_air_multiplier: float = 1.0) -> float:
    if hour < 8 or hour > 18:
        return 0.0
    n_people = room_people(room)
    fresh_air_m3s = n_people * room.fresh_air_m3h_person * fresh_air_multiplier / 3600.0
    return max(0.0, fresh_air_m3s * RHO_AIR * (city["h_out"] - H_INDOOR) * 1000.0)


def calc_room_hourly_load(
    city: dict,
    room: RoomSpec,
    hour: int,
    *,
    indoor_temp: float = T_INDOOR,
    fresh_air_multiplier: float = 1.0,
    equipment_multiplier: float = 1.0,
    wwr: float = DEFAULT_WWR,
) -> dict[str, float]:
    components = {
        "wall": calc_wall_load(city, room, hour, indoor_temp),
        "roof": calc_roof_load(city, room, hour, indoor_temp),
        "window_conduction": calc_window_conduction_load(city, room, hour, indoor_temp, wwr),
        "window_solar": calc_window_solar_load(city, room, hour, wwr),
        "people": calc_people_load(room, hour),
        "light": calc_light_load(room, hour),
        "equip": calc_equip_load(room, hour, equipment_multiplier),
        "fresh_air": calc_fresh_air_load(city, room, hour, fresh_air_multiplier),
    }
    components["indoor"] = sum(components[k] for k in ("wall", "roof", "window_conduction", "window_solar", "people", "light", "equip"))
    components["total"] = components["indoor"] + components["fresh_air"]
    return components


def _scenario_city(base_city: dict, envelope_multiplier: float = 1.0, shading_multiplier: float = 1.0) -> dict:
    city = dict(base_city)
    city["K_wall"] *= envelope_multiplier
    city["K_roof"] *= envelope_multiplier
    city["K_win"] *= envelope_multiplier
    city["SC"] *= shading_multiplier
    return city


def calc_city_load(
    city_id: str,
    *,
    scenario: str = "baseline",
    indoor_temp: float = T_INDOOR,
    fresh_air_multiplier: float = 1.0,
    equipment_multiplier: float = 1.0,
    wwr: float = DEFAULT_WWR,
    envelope_multiplier: float = 1.0,
    shading_multiplier: float = 1.0,
) -> dict:
    city = _scenario_city(CITY_PARAMS[city_id], envelope_multiplier, shading_multiplier)
    hourly_total = [0.0] * 24
    hourly_components = {
        k: [0.0] * 24
        for k in ["wall", "roof", "window_conduction", "window_solar", "people", "light", "equip", "fresh_air", "indoor"]
    }
    room_rows: list[dict] = []

    for room in ROOMS:
        if not room.conditioned:
            continue
        room_hourly: list[float] = []
        room_components_by_hour: list[dict[str, float]] = []
        for hour in range(24):
            comp = calc_room_hourly_load(
                city,
                room,
                hour,
                indoor_temp=indoor_temp,
                fresh_air_multiplier=fresh_air_multiplier,
                equipment_multiplier=equipment_multiplier,
                wwr=wwr,
            )
            room_hourly.append(comp["total"])
            room_components_by_hour.append(comp)
            hourly_total[hour] += comp["total"]
            for key in hourly_components:
                hourly_components[key][hour] += comp[key]
        peak_w, peak_hour = _find_hourly_peak(room_hourly)
        peak_comp = room_components_by_hour[peak_hour]
        room_rows.append({
            "scenario": scenario,
            "city_id": city_id,
            "city": CITY_PARAMS[city_id]["display"],
            "floor": room.floor,
            "room_id": room.room_id,
            "room_name": room.name,
            "room_type": room.room_type,
            "area_m2": round(room.area, 2),
            "people": room_people(room),
            "fresh_air_m3h": round(room_people(room) * room.fresh_air_m3h_person * fresh_air_multiplier, 1),
            "lighting_w_m2": room.lighting_w_m2,
            "equipment_w_m2": round(room.equipment_w_m2 * equipment_multiplier, 1),
            "peak_hour": peak_hour,
            "peak_kw": round(peak_w / 1000.0, 3),
            "indoor_kw": round(peak_comp["indoor"] / 1000.0, 3),
            "fresh_air_kw": round(peak_comp["fresh_air"] / 1000.0, 3),
        })

    peak_w, peak_hour = _find_hourly_peak(hourly_total)
    peak_comp = {key: values[peak_hour] / 1000.0 for key, values in hourly_components.items()}
    area = total_conditioned_area()
    return {
        "scenario": scenario,
        "city_id": city_id,
        "display": CITY_PARAMS[city_id]["display"],
        "peak_kw": round(peak_w / 1000.0, 2),
        "peak_wpm2": round(peak_w / area, 1),
        "peak_hour": peak_hour,
        "components": peak_comp,
        "hourly_total": [round(v / 1000.0, 2) for v in hourly_total],
        "room_rows": room_rows,
    }


# ============================================================================
# 第四部分: 输出
# ============================================================================


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(results: list[dict]) -> None:
    processed = Path("results/processed")
    summary_rows = []
    room_rows = []
    for result in results:
        c = result["components"]
        summary_rows.append({
            "scenario": result["scenario"],
            "city_id": result["city_id"],
            "city": result["display"],
            "peak_kw": result["peak_kw"],
            "peak_wpm2": result["peak_wpm2"],
            "peak_hour": result["peak_hour"],
            "indoor_kw": round(c["indoor"], 2),
            "fresh_air_kw": round(c["fresh_air"], 2),
            "fresh_air_share": round(c["fresh_air"] / result["peak_kw"], 3) if result["peak_kw"] else 0.0,
            "wall_kw": round(c["wall"], 2),
            "roof_kw": round(c["roof"], 2),
            "window_kw": round(c["window_conduction"] + c["window_solar"], 2),
            "people_kw": round(c["people"], 2),
            "light_kw": round(c["light"], 2),
            "equip_kw": round(c["equip"], 2),
        })
        room_rows.extend(result["room_rows"])
    _write_csv(processed / "cltd_city_summary.csv", summary_rows)
    _write_csv(processed / "cltd_room_loads.csv", room_rows)


def sensitivity_results() -> list[dict]:
    scenarios = [
        ("fresh_air_30", {"fresh_air_multiplier": 30.0 / 40.0}),
        ("fresh_air_50", {"fresh_air_multiplier": 50.0 / 40.0}),
        ("indoor_25", {"indoor_temp": 25.0}),
        ("indoor_27", {"indoor_temp": 27.0}),
        ("wwr_025", {"wwr": 0.25}),
        ("wwr_045", {"wwr": 0.45}),
        ("equipment_10", {"equipment_multiplier": 10.0 / 15.0}),
        ("equipment_20", {"equipment_multiplier": 20.0 / 15.0}),
        ("enhanced_envelope", {"envelope_multiplier": 0.90}),
        ("enhanced_shading", {"shading_multiplier": 0.80}),
    ]
    rows: list[dict] = []
    for city_id in CITY_ORDER:
        baseline = calc_city_load(city_id)
        for scenario, kwargs in scenarios:
            result = calc_city_load(city_id, scenario=scenario, **kwargs)
            rows.append({
                "city_id": city_id,
                "city": result["display"],
                "scenario": scenario,
                "baseline_peak_kw": baseline["peak_kw"],
                "scenario_peak_kw": result["peak_kw"],
                "delta_kw": round(result["peak_kw"] - baseline["peak_kw"], 2),
                "delta_percent": round((result["peak_kw"] - baseline["peak_kw"]) / baseline["peak_kw"] * 100.0, 2),
                "fresh_air_share": round(result["components"]["fresh_air"] / result["peak_kw"], 3),
            })
    return rows


def format_output(results: list[dict]) -> None:
    print("=" * 76)
    print("    三层办公楼房间级 CLTD/CLF 冷负荷计算")
    print("=" * 76)
    print(f"总建筑面积: {total_conditioned_area():.1f} m², 房间数: {len(ROOMS)}")
    print()
    print(f"{'城市':<8} {'峰值冷负荷(kW)':<16} {'指标(W/m²)':<12} {'新风占比':<10} {'峰值时刻':<8}")
    print("-" * 76)
    for result in results:
        share = result["components"]["fresh_air"] / result["peak_kw"] if result["peak_kw"] else 0.0
        print(f"{result['display']:<8} {result['peak_kw']:<16.2f} {result['peak_wpm2']:<12.1f} {share:<10.1%} {result['peak_hour']:>2}:00")
    print("-" * 76)
    print("输出: results/processed/cltd_city_summary.csv, cltd_room_loads.csv, cltd_sensitivity.csv")


def main() -> None:
    results = [calc_city_load(city_id) for city_id in CITY_ORDER]
    write_outputs(results)
    _write_csv(Path("results/processed/cltd_sensitivity.csv"), sensitivity_results())
    format_output(results)


if __name__ == "__main__":
    main()
