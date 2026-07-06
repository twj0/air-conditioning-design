#!/usr/bin/env python3
"""Generate room-level load and equipment tables from CLTD outputs."""
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.config.three_story_design import CITY_ENVELOPE_PARAMS, total_conditioned_area

CITY_ORDER = ("shenyang", "tianjin", "chengdu", "chongqing", "shenzhen")
PROCESSED = Path("results/processed")
ROOM_LOADS_CSV = PROCESSED / "cltd_room_loads.csv"
CITY_SUMMARY_CSV = PROCESSED / "cltd_city_summary.csv"
INDOOR_OUTPUT = PROCESSED / "vrf_indoor_unit_selection.csv"
OUTDOOR_OUTPUT = PROCESSED / "vrf_floor_system_selection.csv"

INDOOR_SIZES = [2.8, 3.6, 4.0, 4.5, 5.6, 7.1, 9.0, 11.2, 14.0]
OUTDOOR_SIZES = [22.4, 28.0, 33.5, 40.0, 45.0, 50.0, 56.0, 61.5, 68.0, 73.5, 80.0, 85.0, 90.0]


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _select_one_size(target_kw: float) -> float:
    for size in INDOOR_SIZES:
        if size >= target_kw:
            return size
    return INDOOR_SIZES[-1]


def select_indoor_units(peak_kw: float) -> tuple[int, float, str]:
    target = peak_kw * 1.3
    if target <= INDOOR_SIZES[-1]:
        size = _select_one_size(target)
        return 1, size, f"VRF-C{int(size * 10):03d}"
    count = math.ceil(target / 11.2)
    size = _select_one_size(target / count)
    return count, size, f"VRF-C{int(size * 10):03d}"


def select_outdoor_capacity(indoor_capacity: float) -> tuple[int, float]:
    for count in range(1, 5):
        for size in OUTDOOR_SIZES:
            capacity = count * size
            ratio = indoor_capacity / capacity * 100.0
            if 85.0 <= ratio <= 120.0:
                return count, capacity
    size = OUTDOOR_SIZES[-1]
    count = math.ceil(indoor_capacity / size)
    return count, count * size


def terminal_type(room_type: str) -> str:
    if room_type in {"toilet", "corridor", "archive"}:
        return "薄型风管/壁挂式"
    return "四面出风嵌入式"


def generate_all() -> tuple[list[dict], list[dict]]:
    if not ROOM_LOADS_CSV.exists():
        raise FileNotFoundError(f"Run scripts/run_cltd_load_calculation.py first: {ROOM_LOADS_CSV}")
    room_rows = [row for row in _read_csv(ROOM_LOADS_CSV) if row["scenario"] == "baseline"]
    indoor_rows: list[dict] = []
    floor_capacity: dict[tuple[str, int], float] = defaultdict(float)
    floor_units: dict[tuple[str, int], int] = defaultdict(int)

    for row in room_rows:
        peak_kw = float(row["peak_kw"])
        count, size, model = select_indoor_units(peak_kw)
        capacity = count * size
        key = (row["city_id"], int(row["floor"]))
        floor_capacity[key] += capacity
        floor_units[key] += count
        indoor_rows.append({
            "city_id": row["city_id"],
            "city": row["city"],
            "floor": row["floor"],
            "room_id": row["room_id"],
            "room_name": row["room_name"],
            "room_type": row["room_type"],
            "area_m2": row["area_m2"],
            "people": row["people"],
            "fresh_air_m3h": row["fresh_air_m3h"],
            "lighting_w_m2": row["lighting_w_m2"],
            "equipment_w_m2": row["equipment_w_m2"],
            "peak_load_kw": row["peak_kw"],
            "sizing_load_kw": round(peak_kw * 1.3, 2),
            "terminal_type": terminal_type(row["room_type"]),
            "indoor_model": model,
            "indoor_unit_count": count,
            "unit_capacity_kw": size,
            "selected_capacity_kw": round(capacity, 1),
            "capacity_margin_percent": round((capacity / peak_kw - 1.0) * 100.0, 1) if peak_kw else 0.0,
        })

    outdoor_rows: list[dict] = []
    for city_id in CITY_ORDER:
        for floor in (1, 2, 3):
            indoor_capacity = floor_capacity[(city_id, floor)]
            outdoor_count, outdoor_capacity = select_outdoor_capacity(indoor_capacity)
            ratio = indoor_capacity / outdoor_capacity * 100.0 if outdoor_capacity else 0.0
            outdoor_rows.append({
                "city_id": city_id,
                "city": CITY_ENVELOPE_PARAMS[city_id]["display"],
                "floor": floor,
                "indoor_unit_count": floor_units[(city_id, floor)],
                "indoor_capacity_kw": round(indoor_capacity, 1),
                "outdoor_model": f"VRF-O{int(outdoor_capacity * 10):03d}",
                "outdoor_unit_count": outdoor_count,
                "outdoor_capacity_kw": round(outdoor_capacity, 1),
                "capacity_ratio_percent": round(ratio, 1),
                "ratio_ok": 50.0 <= ratio <= 130.0,
            })

    _write_csv(INDOOR_OUTPUT, indoor_rows)
    _write_csv(OUTDOOR_OUTPUT, outdoor_rows)
    return indoor_rows, outdoor_rows


def print_summary(indoor_rows: list[dict], outdoor_rows: list[dict]) -> None:
    city_rows = _read_csv(CITY_SUMMARY_CSV) if CITY_SUMMARY_CSV.exists() else []
    print("=" * 76)
    print("    三层办公楼 VRF 房间级选型汇总")
    print("=" * 76)
    print(f"建筑面积: {total_conditioned_area():.1f} m²")
    for city_id in CITY_ORDER:
        city = CITY_ENVELOPE_PARAMS[city_id]["display"]
        city_indoor = [row for row in indoor_rows if row["city_id"] == city_id]
        city_outdoor = [row for row in outdoor_rows if row["city_id"] == city_id]
        peak = next((row["peak_kw"] for row in city_rows if row["city_id"] == city_id and row["scenario"] == "baseline"), "-")
        indoor_capacity = sum(float(row["selected_capacity_kw"]) for row in city_indoor)
        indoor_count = sum(int(row["indoor_unit_count"]) for row in city_indoor)
        min_ratio = min(float(row["capacity_ratio_percent"]) for row in city_outdoor)
        max_ratio = max(float(row["capacity_ratio_percent"]) for row in city_outdoor)
        print(f"{city}: 峰值 {peak} kW, 室内机 {indoor_count} 台, 室内容量 {indoor_capacity:.1f} kW, 配比 {min_ratio:.1f}%~{max_ratio:.1f}%")
    print(f"输出: {INDOOR_OUTPUT}, {OUTDOOR_OUTPUT}")


if __name__ == "__main__":
    indoor, outdoor = generate_all()
    print_summary(indoor, outdoor)
