# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
from __future__ import annotations

import argparse
from pathlib import Path

from air_conditioning_design.analysis.report_data import write_report_data
from air_conditioning_design.analysis.report_plots import build_report_figures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-output-root", type=Path)
    parser.add_argument("--plot-output-root", type=Path)
    parser.add_argument("--city-id", action="append", dest="city_ids")
    parser.add_argument("--force-case-summaries", action="store_true")
    parser.add_argument("--format", default="svg", dest="file_format")
    args = parser.parse_args()

    for path in write_report_data(
        output_root=args.data_output_root,
        city_ids=args.city_ids,
        force_case_summaries=args.force_case_summaries,
    ):
        print(path)

    for path in build_report_figures(
        output_root=args.plot_output_root,
        city_ids=args.city_ids,
        file_format=args.file_format,
    ):
        print(path)
