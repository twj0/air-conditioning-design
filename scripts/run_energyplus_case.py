# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.cli.run_energyplus_case import main  # noqa: E402
from air_conditioning_design.simulation.runner import (  # noqa: E402
    _handle_rmtree_error,
    _safe_reset_output_dir,
    run_case,
    shutil,
    time,
)


if __name__ == "__main__":
    main()
