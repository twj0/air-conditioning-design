# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.analysis.tianjin_vrf_summary import (  # noqa: E402
    build_tianjin_vrf_summary,
    write_tianjin_vrf_summary,
)
from air_conditioning_design.cli.parse_tianjin_vrf_results import main  # noqa: E402


if __name__ == "__main__":
    main()
