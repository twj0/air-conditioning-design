# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
from __future__ import annotations

import argparse
from pathlib import Path

from air_conditioning_design.analysis.report_plots import build_report_figures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--city-id", action="append", dest="city_ids")
    args = parser.parse_args()

    for path in build_report_figures(output_root=args.output_root, city_ids=args.city_ids):
        print(path)
