# Ref: docs/spec/task.md (Task-ID: IMPL-IDF-FLOORPLAN-001)
from __future__ import annotations

from dataclasses import dataclass

from air_conditioning_design.figures.annotations import FloorAnnotationSet


@dataclass(frozen=True, slots=True)
class OverlayTerminal:
    zone_name: str
    position: tuple[float, float]


@dataclass(frozen=True, slots=True)
class LineSegment:
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True, slots=True)
class SystemOverlay:
    system_type: str
    title: str
    terminal_marker: str
    terminal_color: str
    doas_spine: LineSegment
    doas_branches: tuple[LineSegment, ...]
    service_paths: tuple[LineSegment, ...]
    terminals: tuple[OverlayTerminal, ...]
    notes: tuple[str, ...]
    roof_equipment_labels: tuple[str, ...]
    section_service_label: str


def _annotation_bounds(annotations: FloorAnnotationSet) -> tuple[float, float, float, float]:
    xs = [x for zone in annotations.zone_annotations for x, _ in zone.boundary]
    ys = [y for zone in annotations.zone_annotations for _, y in zone.boundary]
    return min(xs), max(xs), min(ys), max(ys)


def build_vrf_doas_overlay(annotations: FloorAnnotationSet) -> SystemOverlay:
    min_x, max_x, min_y, max_y = _annotation_bounds(annotations)
    height = max_y - min_y
    spine_y = max_y + height * 0.04

    terminals = tuple(
        OverlayTerminal(zone_name=zone.zone_name, position=zone.anchor)
        for zone in annotations.zone_annotations
    )
    branches = tuple(
        LineSegment(start=(terminal.position[0], spine_y), end=terminal.position)
        for terminal in terminals
    )

    return SystemOverlay(
        system_type="vrf_doas",
        title="VRF + DOAS Service Overlay",
        terminal_marker="o",
        terminal_color="#d66a35",
        doas_spine=LineSegment(start=(min_x, spine_y), end=(max_x, spine_y)),
        doas_branches=branches,
        service_paths=(),
        terminals=terminals,
        notes=(
            "One VRF terminal per conditioned zone",
            "Dedicated outdoor air spine and branch drops",
            "Shared VRF outdoor unit serves all terminals on the model branch",
        ),
        roof_equipment_labels=("DOAS AHU", "VRF ODU bank"),
        section_service_label="Refrigerant riser",
    )


def build_fcu_doas_overlay(annotations: FloorAnnotationSet) -> SystemOverlay:
    min_x, max_x, min_y, max_y = _annotation_bounds(annotations)
    width = max_x - min_x
    height = max_y - min_y
    spine_y = max_y + height * 0.04
    riser_x = min_x - width * 0.05

    terminals = tuple(
        OverlayTerminal(zone_name=zone.zone_name, position=zone.anchor)
        for zone in annotations.zone_annotations
    )
    doas_branches = tuple(
        LineSegment(start=(terminal.position[0], spine_y), end=terminal.position)
        for terminal in terminals
    )
    service_paths = tuple(
        LineSegment(start=(riser_x, terminal.position[1]), end=terminal.position)
        for terminal in terminals
    )

    return SystemOverlay(
        system_type="fcu_doas",
        title="FCU + DOAS Service Overlay",
        terminal_marker="s",
        terminal_color="#2f855a",
        doas_spine=LineSegment(start=(min_x, spine_y), end=(max_x, spine_y)),
        doas_branches=doas_branches,
        service_paths=(
            LineSegment(start=(riser_x, min_y), end=(riser_x, max_y)),
            *service_paths,
        ),
        terminals=terminals,
        notes=(
            "One fan-coil terminal per conditioned zone",
            "Dedicated outdoor air spine and branch drops",
            "Compact CHW/HW riser indicates plant-side service to floor terminals",
        ),
        roof_equipment_labels=("DOAS AHU",),
        section_service_label="CHW/HW riser",
    )
