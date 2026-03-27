# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

import argparse

from air_conditioning_design.analysis.tianjin_summary import write_tianjin_summary
from air_conditioning_design.config.paths import TIANJIN_RESULTS_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    if args.case_id != "tianjin__ideal_loads":
        raise ValueError(f"Unsupported case id for current task: {args.case_id}")
    print(write_tianjin_summary(TIANJIN_RESULTS_ROOT))
