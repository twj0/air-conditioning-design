# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

from air_conditioning_design.models.tianjin_ideal_loads import build_tianjin_ideal_loads_case


def main() -> None:
    print(build_tianjin_ideal_loads_case())

