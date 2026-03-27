# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-FCU-001)
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

from air_conditioning_design.config.paths import (
    RESULTS_RAW_ROOT,
    TIANJIN_EPW,
    TIANJIN_FCU_DOAS_PATH,
    TIANJIN_FCU_DOAS_RESULTS_ROOT,
    TIANJIN_IDEAL_LOADS_PATH,
    TIANJIN_RESULTS_ROOT,
    TIANJIN_VRF_PATH,
    TIANJIN_VRF_RESULTS_ROOT,
    ensure_directories,
    resolve_energyplus_executable,
)
from air_conditioning_design.models.tianjin_fcu_doas import build_tianjin_fcu_doas_case
from air_conditioning_design.models.tianjin_ideal_loads import build_tianjin_ideal_loads_case
from air_conditioning_design.models.tianjin_vrf import build_tianjin_vrf_case


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


def run_case(case_id: str) -> Path:
    ensure_directories()
    case_builders = {
        "tianjin__ideal_loads": (
            build_tianjin_ideal_loads_case,
            TIANJIN_IDEAL_LOADS_PATH,
            TIANJIN_RESULTS_ROOT,
        ),
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
    energyplus_exe = resolve_energyplus_executable()
    _safe_reset_output_dir(output_dir)

    command = [
        str(energyplus_exe),
        "--readvars",
        "-w",
        str(TIANJIN_EPW),
        "-d",
        str(output_dir),
        str(idf_path),
    ]
    subprocess.run(command, check=True)
    return output_dir
