# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.cli.build_tianjin_vrf import main  # noqa: E402
from air_conditioning_design.models.tianjin_vrf import build_tianjin_vrf_case  # noqa: E402


if __name__ == "__main__":
    main()
