# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

import csv
from pathlib import Path

from air_conditioning_design.config.paths import (
    MEDIUM_OFFICE_FLOOR_AREA_M2,
    TIANJIN_SUMMARY_PATH,
    ensure_directories,
)

COOLING_KEYWORD = "zone ideal loads supply air sensible cooling rate"
HEATING_KEYWORD = "zone ideal loads supply air sensible heating rate"


def _matching_indexes(headers: list[str], keyword: str) -> list[int]:
    return [index for index, header in enumerate(headers) if keyword in header.lower()]


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_tianjin_summary(
    results_dir: Path,
    *,
    floor_area_m2: float = MEDIUM_OFFICE_FLOOR_AREA_M2,
) -> dict[str, float | str]:
    csv_path = results_dir / "eplusout.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected EnergyPlus CSV output at {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        cooling_indexes = _matching_indexes(headers, COOLING_KEYWORD)
        heating_indexes = _matching_indexes(headers, HEATING_KEYWORD)
        if not cooling_indexes or not heating_indexes:
            raise ValueError(
                "Could not find Tianjin ideal loads cooling/heating rate columns in eplusout.csv"
            )

        cooling_series: list[float] = []
        heating_series: list[float] = []
        for row in reader:
            cooling_value = sum(_safe_float(row[i]) for i in cooling_indexes)
            heating_value = sum(_safe_float(row[i]) for i in heating_indexes)
            cooling_series.append(cooling_value)
            heating_series.append(heating_value)

    peak_cooling_load_kw = max(cooling_series, default=0.0) / 1000.0
    annual_cooling_load_kwh = sum(cooling_series) / 1000.0
    annual_heating_load_kwh = sum(heating_series) / 1000.0

    return {
        "case_id": "tianjin__ideal_loads",
        "city": "tianjin",
        "system": "ideal_loads",
        "peak_cooling_load": round(peak_cooling_load_kw, 3),
        "peak_cooling_load_per_m2": round(
            peak_cooling_load_kw * 1000.0 / floor_area_m2, 3
        ),
        "annual_cooling_load": round(annual_cooling_load_kwh, 3),
        "annual_heating_load": round(annual_heating_load_kwh, 3),
    }


def write_tianjin_summary(results_dir: Path, output_path: Path = TIANJIN_SUMMARY_PATH) -> Path:
    ensure_directories()
    summary = build_tianjin_summary(results_dir)
    fieldnames = list(summary.keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(summary)
    return output_path

