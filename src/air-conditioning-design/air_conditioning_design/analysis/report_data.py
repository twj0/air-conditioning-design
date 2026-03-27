# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from air_conditioning_design.analysis.fcu_doas_summary import write_fcu_doas_summary
from air_conditioning_design.analysis.ideal_loads_summary import write_ideal_loads_summary
from air_conditioning_design.analysis.vrf_summary import write_vrf_summary
from air_conditioning_design.config.cities import get_city_config, iter_city_ids
from air_conditioning_design.config.paths import (
    MEDIUM_OFFICE_FLOOR_AREA_M2,
    REPORT_CASE_MATRIX_PATH,
    REPORT_EQUIPMENT_SUMMARY_PATH,
    REPORT_IDEAL_LOADS_PATH,
    REPORT_SYSTEM_ENERGY_PATH,
    RESULTS_PROCESSED_ROOT,
    build_case_id,
    ensure_directories,
    results_dir_for_case,
    split_case_id,
    summary_path_for_case,
)

CLIMATE_LABELS = {
    "severe_cold": "Severe Cold",
    "cold": "Cold",
    "hot_summer_cold_winter": "Hot Summer Cold Winter",
    "hot_summer_warm_winter": "Hot Summer Warm Winter",
}

SYSTEM_LABELS = {
    "ideal_loads": "Ideal Loads",
    "vrf": "VRF + DOAS",
    "fcu_doas": "FCU+DOAS",
}


def _city_ids(city_ids: Iterable[str] | None = None) -> tuple[str, ...]:
    return tuple(city_ids) if city_ids is not None else iter_city_ids()


def _case_ids(city_ids: Iterable[str] | None = None) -> tuple[str, ...]:
    ids = []
    for city_id in _city_ids(city_ids):
        ids.extend(
            [
                build_case_id(city_id, "ideal_loads"),
                build_case_id(city_id, "vrf"),
                build_case_id(city_id, "fcu_doas"),
            ]
        )
    return tuple(ids)


def _safe_float(value: str | float | int | None) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: str | float | int | None) -> int:
    return int(round(_safe_float(value)))


def _climate_label(city_id: str) -> str:
    city = get_city_config(city_id)
    return CLIMATE_LABELS.get(city.climate_zone, city.climate_zone)


def ensure_case_summary(case_id: str, *, force: bool = False) -> Path:
    ensure_directories()
    target = summary_path_for_case(case_id)
    if target.exists() and not force:
        return target

    city_id, system_id = split_case_id(case_id)
    results_dir = results_dir_for_case(case_id)
    if system_id == "ideal_loads":
        return write_ideal_loads_summary(city_id, results_dir, target)
    if system_id == "vrf":
        return write_vrf_summary(city_id, results_dir, target)
    if system_id == "fcu_doas":
        return write_fcu_doas_summary(city_id, results_dir, target)
    raise ValueError(f"Unsupported system for summary generation: {case_id}")


def _read_summary(case_id: str) -> dict[str, str]:
    path = ensure_case_summary(case_id)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return next(csv.DictReader(handle))


def _component_sizing_value(
    results_dir: Path,
    component_type: str,
    descriptor: str,
) -> tuple[str, float] | tuple[None, None]:
    eio_path = results_dir / "eplusout.eio"
    if not eio_path.exists():
        return None, None

    with eio_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("Component Sizing Information"):
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 5:
                continue
            _, current_type, component_name, current_descriptor, value = parts[:5]
            if current_type != component_type or current_descriptor != descriptor:
                continue
            return component_name, _safe_float(value)
    return None, None


def build_ideal_loads_comparison(
    city_ids: Iterable[str] | None = None,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for city_id in _city_ids(city_ids):
        summary = _read_summary(build_case_id(city_id, "ideal_loads"))
        annual_cooling = _safe_float(summary["annual_cooling_load"])
        annual_heating = _safe_float(summary["annual_heating_load"])
        annual_total = annual_cooling + annual_heating
        city = get_city_config(city_id)
        rows.append(
            {
                "case_id": summary["case_id"],
                "city": city_id,
                "city_name": city.display_name,
                "climate_zone": city.climate_zone,
                "climate_zone_label": _climate_label(city_id),
                "system": "ideal_loads",
                "system_label": SYSTEM_LABELS["ideal_loads"],
                "peak_cooling_load_kw": round(_safe_float(summary["peak_cooling_load"]), 3),
                "peak_cooling_load_per_m2_w_m2": round(
                    _safe_float(summary["peak_cooling_load_per_m2"]), 3
                ),
                "annual_cooling_load_kwh": round(annual_cooling, 3),
                "annual_heating_load_kwh": round(annual_heating, 3),
                "annual_total_load_kwh": round(annual_total, 3),
                "annual_total_load_per_m2_kwh_m2": round(
                    annual_total / MEDIUM_OFFICE_FLOOR_AREA_M2, 3
                ),
            }
        )
    return rows


def build_system_energy_comparison(
    city_ids: Iterable[str] | None = None,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for city_id in _city_ids(city_ids):
        city = get_city_config(city_id)
        for system_id in ("vrf", "fcu_doas"):
            case_id = build_case_id(city_id, system_id)
            summary = _read_summary(case_id)
            results_dir = results_dir_for_case(case_id)

            if system_id == "vrf":
                cooling_name, cooling_capacity_w = _component_sizing_value(
                    results_dir,
                    "AirConditioner:VariableRefrigerantFlow",
                    "Design Size Rated Total Cooling Capacity (gross) [W]",
                )
                heating_name, heating_capacity_w = _component_sizing_value(
                    results_dir,
                    "AirConditioner:VariableRefrigerantFlow",
                    "Design Size Rated Total Heating Capacity [W]",
                )
                terminal_count = _safe_int(summary.get("vrf_terminal_count"))
                plant_loop_count = 0
            else:
                cooling_name, cooling_capacity_w = _component_sizing_value(
                    results_dir,
                    "Chiller:Electric:EIR",
                    "Design Size Reference Capacity [W]",
                )
                heating_name, heating_capacity_w = _component_sizing_value(
                    results_dir,
                    "Boiler:HotWater",
                    "Design Size Nominal Capacity [W]",
                )
                terminal_count = _safe_int(summary.get("fcu_terminal_count"))
                plant_loop_count = _safe_int(summary.get("plant_loop_count"))

            _, outdoor_air_rate_m3_s = _component_sizing_value(
                results_dir,
                "Controller:OutdoorAir",
                "Maximum Outdoor Air Flow Rate [m3/s]",
            )

            rows.append(
                {
                    "case_id": case_id,
                    "city": city_id,
                    "city_name": city.display_name,
                    "climate_zone": city.climate_zone,
                    "climate_zone_label": _climate_label(city_id),
                    "system": system_id,
                    "system_label": SYSTEM_LABELS[system_id],
                    "annual_hvac_electricity_kwh": round(
                        _safe_float(summary["annual_hvac_electricity"]), 3
                    ),
                    "annual_hvac_electricity_per_m2_kwh_m2": round(
                        _safe_float(summary["annual_hvac_electricity_per_m2"]), 3
                    ),
                    "terminal_count": terminal_count,
                    "plant_loop_count": plant_loop_count,
                    "design_cooling_equipment_name": cooling_name or "",
                    "design_cooling_capacity_kw": round(cooling_capacity_w / 1000.0, 3)
                    if cooling_capacity_w is not None
                    else 0.0,
                    "design_heating_equipment_name": heating_name or "",
                    "design_heating_capacity_kw": round(heating_capacity_w / 1000.0, 3)
                    if heating_capacity_w is not None
                    else 0.0,
                    "outdoor_air_rate_m3_s": round(outdoor_air_rate_m3_s, 6)
                    if outdoor_air_rate_m3_s is not None
                    else 0.0,
                    "outdoor_air_rate_m3_h": round(outdoor_air_rate_m3_s * 3600.0, 3)
                    if outdoor_air_rate_m3_s is not None
                    else 0.0,
                }
            )
    return rows


def build_equipment_summary(
    city_ids: Iterable[str] | None = None,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for system_row in build_system_energy_comparison(city_ids):
        system_id = str(system_row["system"])
        if system_id == "vrf":
            note = "Cooling and heating capacity both come from the shared VRF outdoor unit."
        else:
            note = (
                "Cooling capacity comes from the main chiller and heating capacity from the main boiler."
            )

        rows.append(
            {
                "case_id": system_row["case_id"],
                "city": system_row["city"],
                "city_name": system_row["city_name"],
                "climate_zone_label": system_row["climate_zone_label"],
                "system": system_id,
                "system_label": system_row["system_label"],
                "design_cooling_equipment_name": system_row["design_cooling_equipment_name"],
                "design_cooling_capacity_kw": system_row["design_cooling_capacity_kw"],
                "design_heating_equipment_name": system_row["design_heating_equipment_name"],
                "design_heating_capacity_kw": system_row["design_heating_capacity_kw"],
                "terminal_count": system_row["terminal_count"],
                "outdoor_air_rate_m3_s": system_row["outdoor_air_rate_m3_s"],
                "outdoor_air_rate_m3_h": system_row["outdoor_air_rate_m3_h"],
                "notes": note,
            }
        )
    return rows


def build_case_matrix(city_ids: Iterable[str] | None = None) -> list[dict[str, float | int | str]]:
    ideal_rows = {row["city"]: row for row in build_ideal_loads_comparison(city_ids)}
    system_rows = build_system_energy_comparison(city_ids)

    rows: list[dict[str, float | int | str]] = []
    for city_id in _city_ids(city_ids):
        base = ideal_rows[city_id]
        rows.append(
            {
                "case_id": base["case_id"],
                "city": base["city"],
                "city_name": base["city_name"],
                "climate_zone_label": base["climate_zone_label"],
                "system": base["system"],
                "system_label": base["system_label"],
                "peak_cooling_load_kw": base["peak_cooling_load_kw"],
                "peak_cooling_load_per_m2_w_m2": base["peak_cooling_load_per_m2_w_m2"],
                "annual_cooling_load_kwh": base["annual_cooling_load_kwh"],
                "annual_heating_load_kwh": base["annual_heating_load_kwh"],
                "annual_total_load_kwh": base["annual_total_load_kwh"],
                "annual_total_load_per_m2_kwh_m2": base["annual_total_load_per_m2_kwh_m2"],
                "annual_hvac_electricity_kwh": "",
                "annual_hvac_electricity_per_m2_kwh_m2": "",
                "terminal_count": "",
                "plant_loop_count": "",
                "design_cooling_capacity_kw": "",
                "design_heating_capacity_kw": "",
                "outdoor_air_rate_m3_s": "",
                "outdoor_air_rate_m3_h": "",
            }
        )

    for row in system_rows:
        rows.append(
            {
                "case_id": row["case_id"],
                "city": row["city"],
                "city_name": row["city_name"],
                "climate_zone_label": row["climate_zone_label"],
                "system": row["system"],
                "system_label": row["system_label"],
                "peak_cooling_load_kw": "",
                "peak_cooling_load_per_m2_w_m2": "",
                "annual_cooling_load_kwh": "",
                "annual_heating_load_kwh": "",
                "annual_total_load_kwh": "",
                "annual_total_load_per_m2_kwh_m2": "",
                "annual_hvac_electricity_kwh": row["annual_hvac_electricity_kwh"],
                "annual_hvac_electricity_per_m2_kwh_m2": row[
                    "annual_hvac_electricity_per_m2_kwh_m2"
                ],
                "terminal_count": row["terminal_count"],
                "plant_loop_count": row["plant_loop_count"],
                "design_cooling_capacity_kw": row["design_cooling_capacity_kw"],
                "design_heating_capacity_kw": row["design_heating_capacity_kw"],
                "outdoor_air_rate_m3_s": row["outdoor_air_rate_m3_s"],
                "outdoor_air_rate_m3_h": row["outdoor_air_rate_m3_h"],
            }
        )
    return rows


def _write_rows(path: Path, rows: list[dict[str, float | int | str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows were generated for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_report_data(
    *,
    output_root: Path | None = None,
    city_ids: Iterable[str] | None = None,
    force_case_summaries: bool = False,
) -> list[Path]:
    ensure_directories()
    target_root = output_root or RESULTS_PROCESSED_ROOT
    target_root.mkdir(parents=True, exist_ok=True)

    for case_id in _case_ids(city_ids):
        ensure_case_summary(case_id, force=force_case_summaries)

    outputs = [
        _write_rows(target_root / REPORT_IDEAL_LOADS_PATH.name, build_ideal_loads_comparison(city_ids)),
        _write_rows(target_root / REPORT_SYSTEM_ENERGY_PATH.name, build_system_energy_comparison(city_ids)),
        _write_rows(target_root / REPORT_EQUIPMENT_SUMMARY_PATH.name, build_equipment_summary(city_ids)),
        _write_rows(target_root / REPORT_CASE_MATRIX_PATH.name, build_case_matrix(city_ids)),
    ]
    return outputs
