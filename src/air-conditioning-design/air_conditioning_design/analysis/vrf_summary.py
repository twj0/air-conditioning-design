# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-VRF-001)
from __future__ import annotations

import csv
from pathlib import Path

from air_conditioning_design.config.paths import (
    MEDIUM_OFFICE_FLOOR_AREA_M2,
    build_case_id,
    ensure_directories,
    summary_path_for_case,
    system_model_path,
)
from air_conditioning_design.idf.io import load_idf

PRIMARY_METER_KEYWORD = "electricity:hvac"
FALLBACK_METER_KEYWORDS = (
    "fans:electricity",
    "cooling:electricity",
    "heating:electricity",
)


def _matching_indexes(headers: list[str], keyword: str) -> list[int]:
    return [index for index, header in enumerate(headers) if keyword in header.lower()]


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _annual_meter_kwh(meter_csv_path: Path) -> float:
    with meter_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        indexes = _matching_indexes(headers, PRIMARY_METER_KEYWORD)
        if indexes:
            series = [sum(_safe_float(row[i]) for i in indexes) for row in reader]
            return sum(series) / 3_600_000.0

    with meter_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        fallback_indexes: list[int] = []
        for keyword in FALLBACK_METER_KEYWORDS:
            fallback_indexes.extend(_matching_indexes(headers, keyword))
        if not fallback_indexes:
            raise ValueError(
                "Could not find Electricity:HVAC or fallback HVAC electricity meters in eplusmtr.csv"
            )
        series = [sum(_safe_float(row[i]) for i in fallback_indexes) for row in reader]
        return sum(series) / 3_600_000.0


def _vrf_terminal_count(idf_path: Path) -> int:
    objects = load_idf(idf_path)
    return sum(
        1
        for obj in objects
        if obj.class_name.upper() == "ZONEHVAC:TERMINALUNIT:VARIABLEREFRIGERANTFLOW"
    )


def build_vrf_summary(
    city_id: str,
    results_dir: Path,
    *,
    idf_path: Path | None = None,
    floor_area_m2: float = MEDIUM_OFFICE_FLOOR_AREA_M2,
) -> dict[str, float | int | str]:
    meter_csv_path = results_dir / "eplusmtr.csv"
    if not meter_csv_path.exists():
        raise FileNotFoundError(f"Expected EnergyPlus meter output at {meter_csv_path}")

    annual_hvac_electricity = _annual_meter_kwh(meter_csv_path)
    target_idf_path = idf_path or system_model_path(build_case_id(city_id, "vrf"))
    terminal_count = _vrf_terminal_count(target_idf_path)

    return {
        "case_id": build_case_id(city_id, "vrf"),
        "city": city_id,
        "system": "vrf",
        "annual_hvac_electricity": round(annual_hvac_electricity, 3),
        "annual_hvac_electricity_per_m2": round(
            annual_hvac_electricity / floor_area_m2, 3
        ),
        "vrf_terminal_count": terminal_count,
    }


def write_vrf_summary(
    city_id: str,
    results_dir: Path,
    output_path: Path | None = None,
) -> Path:
    ensure_directories()
    summary = build_vrf_summary(city_id, results_dir)
    target = output_path or summary_path_for_case(build_case_id(city_id, "vrf"))
    fieldnames = list(summary.keys())
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(summary)
    return target
