# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from air_conditioning_design.analysis.report_data import (
    build_equipment_summary,
    build_ideal_loads_comparison,
    build_system_energy_comparison,
)
from air_conditioning_design.config.paths import RESULTS_PLOTS_ROOT, ensure_directories

PLOT_FILENAMES = {
    "peak_cooling_load": "peak_cooling_load_by_city",
    "peak_cooling_density": "peak_cooling_load_density_by_city",
    "annual_loads": "annual_ideal_loads_by_city",
    "system_electricity": "system_electricity_by_city",
    "system_electricity_per_m2": "system_electricity_per_m2_by_city",
    "design_cooling_capacity": "design_cooling_capacity_by_city",
}

SYSTEM_ORDER = ("fcu_doas", "vrf")
SYSTEM_COLORS = {"fcu_doas": "#24577a", "vrf": "#d66a35"}
CITY_COLOR = "#24577a"
COOLING_COLOR = "#d66a35"
HEATING_COLOR = "#4e8c63"


def _figure_path(output_root: Path, key: str, file_format: str) -> Path:
    return output_root / f"{PLOT_FILENAMES[key]}.{file_format}"


def _base_axes(figsize: tuple[float, float] = (9, 5)) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    return fig, ax


def _save(fig: plt.Figure, path: Path, *, file_format: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


def _city_labels(rows: list[dict[str, float | str]]) -> list[str]:
    return [f"{row['city_name']}\n{row['climate_zone_label']}" for row in rows]


def _plot_single_series(
    rows: list[dict[str, float | str]],
    *,
    field: str,
    title: str,
    ylabel: str,
    output_path: Path,
    color: str,
    file_format: str,
) -> Path:
    fig, ax = _base_axes()
    labels = _city_labels(rows)
    values = [float(row[field]) for row in rows]
    positions = np.arange(len(labels))
    ax.bar(positions, values, color=color, width=0.6)
    ax.set_xticks(positions, labels)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    return _save(fig, output_path, file_format=file_format)


def _plot_grouped_system_series(
    rows: list[dict[str, float | int | str]],
    *,
    field: str,
    title: str,
    ylabel: str,
    output_path: Path,
    file_format: str,
) -> Path:
    grouped: dict[str, dict[str, dict[str, float | int | str]]] = {}
    for row in rows:
        grouped.setdefault(str(row["city"]), {})[str(row["system"])] = row

    city_ids = list(grouped)
    labels = [
        f"{grouped[city_id][SYSTEM_ORDER[0]]['city_name']}\n"
        f"{grouped[city_id][SYSTEM_ORDER[0]]['climate_zone_label']}"
        for city_id in city_ids
    ]
    positions = np.arange(len(city_ids))
    width = 0.36

    fig, ax = _base_axes(figsize=(10, 5))
    for offset, system_id in enumerate(SYSTEM_ORDER):
        values = [float(grouped[city_id][system_id][field]) for city_id in city_ids]
        ax.bar(
            positions + (offset - 0.5) * width,
            values,
            width=width,
            label=str(grouped[city_ids[0]][system_id]["system_label"]),
            color=SYSTEM_COLORS[system_id],
        )

    ax.set_xticks(positions, labels)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(frameon=False)
    return _save(fig, output_path, file_format=file_format)


def build_report_figures(
    *,
    output_root: Path | None = None,
    city_ids: Iterable[str] | None = None,
    file_format: str = "svg",
) -> list[Path]:
    ensure_directories()
    target_root = output_root or RESULTS_PLOTS_ROOT
    target_root.mkdir(parents=True, exist_ok=True)

    ideal_rows = build_ideal_loads_comparison(city_ids)
    system_rows = build_system_energy_comparison(city_ids)
    equipment_rows = build_equipment_summary(city_ids)

    outputs = [
        _plot_single_series(
            ideal_rows,
            field="peak_cooling_load_kw",
            title="Peak Cooling Load by City",
            ylabel="Peak Cooling Load (kW)",
            output_path=_figure_path(target_root, "peak_cooling_load", file_format),
            color=CITY_COLOR,
            file_format=file_format,
        ),
        _plot_single_series(
            ideal_rows,
            field="peak_cooling_load_per_m2_w_m2",
            title="Peak Cooling Load Density by City",
            ylabel="Peak Cooling Load Density (W/m²)",
            output_path=_figure_path(target_root, "peak_cooling_density", file_format),
            color=CITY_COLOR,
            file_format=file_format,
        ),
    ]

    fig, ax = _base_axes(figsize=(10, 5))
    labels = _city_labels(ideal_rows)
    positions = np.arange(len(labels))
    width = 0.36
    cooling_values = [float(row["annual_cooling_load_kwh"]) for row in ideal_rows]
    heating_values = [float(row["annual_heating_load_kwh"]) for row in ideal_rows]
    ax.bar(
        positions - width / 2,
        cooling_values,
        width=width,
        color=COOLING_COLOR,
        label="Annual Cooling Load",
    )
    ax.bar(
        positions + width / 2,
        heating_values,
        width=width,
        color=HEATING_COLOR,
        label="Annual Heating Load",
    )
    ax.set_xticks(positions, labels)
    ax.set_title("Annual Ideal Loads by City")
    ax.set_ylabel("Load (kWh)")
    ax.legend(frameon=False)
    outputs.append(
        _save(
            fig,
            _figure_path(target_root, "annual_loads", file_format),
            file_format=file_format,
        )
    )

    outputs.append(
        _plot_grouped_system_series(
            system_rows,
            field="annual_hvac_electricity_kwh",
            title="Annual HVAC Electricity by City",
            ylabel="Annual HVAC Electricity (kWh)",
            output_path=_figure_path(target_root, "system_electricity", file_format),
            file_format=file_format,
        )
    )
    outputs.append(
        _plot_grouped_system_series(
            system_rows,
            field="annual_hvac_electricity_per_m2_kwh_m2",
            title="Annual HVAC Electricity per Area by City",
            ylabel="HVAC Electricity Intensity (kWh/m²)",
            output_path=_figure_path(target_root, "system_electricity_per_m2", file_format),
            file_format=file_format,
        )
    )
    outputs.append(
        _plot_grouped_system_series(
            equipment_rows,
            field="design_cooling_capacity_kw",
            title="Design Cooling Capacity by City",
            ylabel="Design Cooling Capacity (kW)",
            output_path=_figure_path(target_root, "design_cooling_capacity", file_format),
            file_format=file_format,
        )
    )
    return outputs
