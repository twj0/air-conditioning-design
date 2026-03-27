# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-FCU-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.models.systems.fcu_doas import build_fcu_doas_case


def build_tianjin_fcu_doas_case(output_root: Path | None = None) -> Path:
    return build_fcu_doas_case("tianjin", output_root=output_root)
