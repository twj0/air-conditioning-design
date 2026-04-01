# Ref: docs/spec/task.md (Task-ID: IMPL-IDF-FLOORPLAN-001)
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from air_conditioning_design.config.paths import (
    paper_figure_path,
    results_dir_for_case,
    results_figure_path,
    system_model_path,
)
from air_conditioning_design.figures.annotations import build_floor_annotations
from air_conditioning_design.figures.annotations import build_building_structure_annotations
from air_conditioning_design.figures.geometry import load_floorplan_geometry
from air_conditioning_design.figures.overlays import (
    build_fcu_doas_overlay,
    build_vrf_doas_overlay,
)
from air_conditioning_design.figures.render import (
    render_building_structure,
    render_base_floorplan,
    render_system_overlay_building,
    render_zoning_floorplan,
)

BASE_FIGURE_NAME = "medium_office_typical_floor_base"
ZONING_FIGURE_NAME = "medium_office_typical_floor_zones"
VRF_DOAS_FIGURE_NAME = "medium_office_typical_floor_vrf_doas"
FCU_DOAS_FIGURE_NAME = "medium_office_typical_floor_fcu_doas"
BUILDING_STRUCTURE_FIGURE_NAME = "medium_office_building_model_structure"
CANONICAL_FIGURE_CASE_NOTE = (
    "Use the Tianjin model family as the current reproducible figure source; "
    "the shared mother-model geometry keeps the plan view consistent across cities."
)


def build_model_figures(
    case_id: str,
    *,
    figure_set: str = "base",
    output_root: Path | None = None,
    paper_output_root: Path | None = None,
    file_formats: tuple[str, ...] = ("svg",),
) -> list[Path]:
    if figure_set not in {"base", "zones", "vrf_doas", "fcu_doas", "building_structure", "all"}:
        raise ValueError(f"Unsupported figure_set for current task: {figure_set}")

    idf_path = system_model_path(case_id)
    requires_dxf = figure_set in {"base", "zones", "vrf_doas", "fcu_doas", "all"}
    geometry = None
    annotations = None
    if requires_dxf:
        dxf_path = results_dir_for_case(case_id) / "eplusout.dxf"
        if not dxf_path.exists():
            raise FileNotFoundError(f"DXF geometry was not found for case: {case_id}")
        geometry = load_floorplan_geometry(dxf_path)
        annotations = build_floor_annotations(idf_path, geometry=geometry)
    structure = (
        build_building_structure_annotations(idf_path)
        if figure_set in {"building_structure", "vrf_doas", "fcu_doas", "all"}
        else None
    )

    outputs: list[Path] = []
    requested_figure_names: list[tuple[str, Callable[..., Path], object]] = []
    if figure_set in {"base", "all"}:
        requested_figure_names.append((BASE_FIGURE_NAME, render_base_floorplan, annotations))
    if figure_set in {"zones", "all"}:
        requested_figure_names.append((ZONING_FIGURE_NAME, render_zoning_floorplan, annotations))
    if figure_set in {"building_structure", "all"}:
        requested_figure_names.append(
            (BUILDING_STRUCTURE_FIGURE_NAME, render_building_structure, structure)
        )
    if figure_set == "vrf_doas":
        overlay = build_vrf_doas_overlay(annotations)
        requested_figure_names.append(
            (
                VRF_DOAS_FIGURE_NAME,
                lambda current_structure, output_path, *, file_format: render_system_overlay_building(
                    current_structure,
                    overlay,
                    output_path,
                    file_format=file_format,
                ),
                structure,
            )
        )
    if figure_set == "fcu_doas":
        overlay = build_fcu_doas_overlay(annotations)
        requested_figure_names.append(
            (
                FCU_DOAS_FIGURE_NAME,
                lambda current_structure, output_path, *, file_format: render_system_overlay_building(
                    current_structure,
                    overlay,
                    output_path,
                    file_format=file_format,
                ),
                structure,
            )
        )

    for file_format in file_formats:
        for figure_name, renderer, payload in requested_figure_names:
            output_path = results_figure_path(
                figure_name,
                file_format,
                output_root=output_root,
            )
            outputs.append(
                renderer(
                    payload,
                    output_path,
                    file_format=file_format,
                )
            )
            if paper_output_root is not None:
                outputs.append(
                    renderer(
                        payload,
                        paper_figure_path(
                            figure_name,
                            file_format,
                            output_root=paper_output_root,
                        ),
                        file_format=file_format,
                    )
                )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=CANONICAL_FIGURE_CASE_NOTE)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--figure-set", default="base")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--paper-output-root", type=Path)
    parser.add_argument("--format", action="append", dest="file_formats")
    args = parser.parse_args()

    formats = tuple(args.file_formats or ("svg",))
    for output_path in build_model_figures(
        args.case_id,
        figure_set=args.figure_set,
        output_root=args.output_root,
        paper_output_root=args.paper_output_root,
        file_formats=formats,
    ):
        print(output_path)
