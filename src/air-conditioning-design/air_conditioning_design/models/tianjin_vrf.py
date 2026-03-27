# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-VRF-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.models.systems.vrf import build_vrf_case


def build_tianjin_vrf_case(output_root: Path | None = None) -> Path:
    return build_vrf_case("tianjin", output_root=output_root)
