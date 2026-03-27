# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from __future__ import annotations

import argparse

from air_conditioning_design.analysis.tianjin_vrf_summary import write_tianjin_vrf_summary
from air_conditioning_design.config.paths import TIANJIN_VRF_RESULTS_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    if args.case_id != "tianjin__vrf":
        raise ValueError(f"Unsupported case id for current task: {args.case_id}")
    print(write_tianjin_vrf_summary(TIANJIN_VRF_RESULTS_ROOT))
