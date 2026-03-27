# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-FCU-001)
from __future__ import annotations

from air_conditioning_design.models.tianjin_fcu_doas import build_tianjin_fcu_doas_case


def main() -> None:
    print(build_tianjin_fcu_doas_case())
