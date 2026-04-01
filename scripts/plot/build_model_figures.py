# Ref: docs/spec/task.md (Task-ID: IMPL-IDF-FLOORPLAN-001)
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.cli.build_model_figures import main  # noqa: E402


if __name__ == "__main__":
    main()
