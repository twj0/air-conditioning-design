# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

from air_conditioning_design.config.cities import has_city
from air_conditioning_design.config.paths import (
    RESULTS_RAW_ROOT,
    TIANJIN_EPW,
    TIANJIN_FCU_DOAS_PATH,
    TIANJIN_FCU_DOAS_RESULTS_ROOT,
    TIANJIN_VRF_PATH,
    TIANJIN_VRF_RESULTS_ROOT,
    ensure_directories,
    results_dir_for_case,
    resolve_energyplus_executable,
    split_case_id,
    system_model_path,
)
from air_conditioning_design.models.tianjin_fcu_doas import build_tianjin_fcu_doas_case
from air_conditioning_design.models.tianjin_vrf import build_tianjin_vrf_case
from air_conditioning_design.models.systems.ideal_loads import build_ideal_loads_case
from air_conditioning_design.weather.catalog import load_weather_manifest


def _handle_rmtree_error(func, path, exc_info) -> None:  # type: ignore[no-untyped-def]
    if not issubclass(exc_info[0], PermissionError):
        raise exc_info[1]

    os.chmod(path, stat.S_IWRITE)
    func(path)


def _safe_reset_output_dir(output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    raw_root = RESULTS_RAW_ROOT.resolve()
    if raw_root not in output_dir.parents:
        raise ValueError(f"Refusing to clear unexpected output dir: {output_dir}")

    if output_dir.exists():
        last_error: PermissionError | None = None
        for attempt in range(5):
            try:
                shutil.rmtree(output_dir, onerror=_handle_rmtree_error)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.5 * (attempt + 1))
        if last_error is not None:
            raise last_error
    output_dir.mkdir(parents=True, exist_ok=True)


def _run_energyplus_case(
    *, idf_path: Path, output_dir: Path, weather_path: Path
) -> Path:
    energyplus_exe = resolve_energyplus_executable()
    _safe_reset_output_dir(output_dir)

    command = [
        str(energyplus_exe),
        "--readvars",
        "-w",
        str(weather_path),
        "-d",
        str(output_dir),
        str(idf_path),
    ]
    subprocess.run(command, check=True)
    return output_dir


def run_case(case_id: str) -> Path:
    ensure_directories()
    city_id, system_id = split_case_id(case_id)
    if system_id == "ideal_loads" and has_city(city_id):
        build_ideal_loads_case(city_id)
        manifest = load_weather_manifest(city_id)
        return _run_energyplus_case(
            idf_path=system_model_path(case_id),
            output_dir=results_dir_for_case(case_id),
            weather_path=Path(manifest["epw_path"]),
        )

    case_builders = {
        "tianjin__vrf": (
            build_tianjin_vrf_case,
            TIANJIN_VRF_PATH,
            TIANJIN_VRF_RESULTS_ROOT,
        ),
        "tianjin__fcu_doas": (
            build_tianjin_fcu_doas_case,
            TIANJIN_FCU_DOAS_PATH,
            TIANJIN_FCU_DOAS_RESULTS_ROOT,
        ),
    }
    if case_id not in case_builders:
        raise ValueError(f"Unsupported case id for current task: {case_id}")

    builder, idf_path, output_dir = case_builders[case_id]
    builder()
    return _run_energyplus_case(
        idf_path=idf_path,
        output_dir=output_dir,
        weather_path=TIANJIN_EPW,
    )
