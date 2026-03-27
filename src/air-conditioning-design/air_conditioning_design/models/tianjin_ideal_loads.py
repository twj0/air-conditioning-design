# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.models.systems.ideal_loads import build_ideal_loads_case


def build_tianjin_ideal_loads_case(output_root: Path | None = None) -> Path:
    return build_ideal_loads_case("tianjin", output_root=output_root)
