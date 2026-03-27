# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from __future__ import annotations

from air_conditioning_design.models.tianjin_vrf import build_tianjin_vrf_case


def main() -> None:
    print(build_tianjin_vrf_case())
