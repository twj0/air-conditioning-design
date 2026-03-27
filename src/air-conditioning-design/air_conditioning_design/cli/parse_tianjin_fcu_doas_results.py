# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-FCU-001)
from __future__ import annotations

import argparse

from air_conditioning_design.analysis.tianjin_fcu_doas_summary import (
    write_tianjin_fcu_doas_summary,
)
from air_conditioning_design.config.paths import TIANJIN_FCU_DOAS_RESULTS_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    if args.case_id != "tianjin__fcu_doas":
        raise ValueError(f"Unsupported case id for current task: {args.case_id}")
    print(write_tianjin_fcu_doas_summary(TIANJIN_FCU_DOAS_RESULTS_ROOT))
