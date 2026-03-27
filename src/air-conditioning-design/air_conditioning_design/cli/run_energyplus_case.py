# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

import argparse

from air_conditioning_design.simulation.runner import run_case


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    print(run_case(args.case_id))

