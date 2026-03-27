# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-VRF-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.analysis.vrf_summary import (
    build_vrf_summary,
    write_vrf_summary,
)
from air_conditioning_design.config.paths import (
    MEDIUM_OFFICE_FLOOR_AREA_M2,
    TIANJIN_VRF_PATH,
    TIANJIN_VRF_SUMMARY_PATH,
)


def build_tianjin_vrf_summary(
    results_dir: Path,
    *,
    idf_path: Path = TIANJIN_VRF_PATH,
    floor_area_m2: float = MEDIUM_OFFICE_FLOOR_AREA_M2,
) -> dict[str, float | int | str]:
    return build_vrf_summary(
        "tianjin",
        results_dir,
        idf_path=idf_path,
        floor_area_m2=floor_area_m2,
    )


def write_tianjin_vrf_summary(
    results_dir: Path, output_path: Path = TIANJIN_VRF_SUMMARY_PATH
) -> Path:
    return write_vrf_summary("tianjin", results_dir, output_path)
