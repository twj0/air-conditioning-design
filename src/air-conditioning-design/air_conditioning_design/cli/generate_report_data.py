# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
from __future__ import annotations

import argparse
from pathlib import Path

from air_conditioning_design.analysis.report_data import write_report_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--city-id", action="append", dest="city_ids")
    parser.add_argument("--force-case-summaries", action="store_true")
    args = parser.parse_args()

    for path in write_report_data(
        output_root=args.output_root,
        city_ids=args.city_ids,
        force_case_summaries=args.force_case_summaries,
    ):
        print(path)
