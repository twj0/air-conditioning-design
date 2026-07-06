# Ref: docs/个性化设计-约束边界与方向一计划.md §三 阶段3
from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.analysis.direction1_plots import build_direction1_figures
from air_conditioning_design.analysis.suitability import write_scores


if __name__ == "__main__":
    scores = write_scores()
    print(f"Wrote {scores}")
    for path in build_direction1_figures():
        print(f"Figure: {path}")
