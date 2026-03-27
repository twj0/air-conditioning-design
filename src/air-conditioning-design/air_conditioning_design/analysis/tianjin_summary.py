# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.analysis.ideal_loads_summary import (
    build_ideal_loads_summary,
    write_ideal_loads_summary,
)
from air_conditioning_design.config.paths import MEDIUM_OFFICE_FLOOR_AREA_M2, TIANJIN_SUMMARY_PATH


def build_tianjin_summary(
    results_dir: Path,
    *,
    floor_area_m2: float = MEDIUM_OFFICE_FLOOR_AREA_M2,
) -> dict[str, float | str]:
    return build_ideal_loads_summary(
        "tianjin", results_dir, floor_area_m2=floor_area_m2
    )


def write_tianjin_summary(results_dir: Path, output_path: Path = TIANJIN_SUMMARY_PATH) -> Path:
    return write_ideal_loads_summary("tianjin", results_dir, output_path)
