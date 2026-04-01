# Ref: docs/spec/task.md (Task-ID: IMPL-IDF-FLOORPLAN-001)
from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle

from air_conditioning_design.figures.annotations import (
    BuildingStructureAnnotation,
    FacadeAnnotation,
    FloorAnnotationSet,
    StructureFloorAnnotation,
    ZoneAnnotation,
)
from air_conditioning_design.figures.overlays import SystemOverlay

CORE_FILL = "#d9e2ec"
PERIMETER_FILL = "#bcccdc"
OTHER_FILL = "#f0f4f8"
OUTLINE_COLOR = "#243b53"
PLENUM_FILL = "#f5f7fa"
WINDOW_COLOR = "#2b6cb0"
DIMENSION_COLOR = "#52606d"
MUTED_TEXT = "#52606d"
INFO_PANEL_FILL = "#f8fbff"
SECTION_OCCUPIED_FILL = "#dbeafe"
WALL_FILL = "#e9eef5"
DOAS_COLOR = "#6b7280"
PIPE_COLOR = "#2f855a"
VRF_PLATFORM_FILL = "#fff1b8"


def _figure_bounds(annotations: FloorAnnotationSet) -> tuple[float, float, float, float]:
    return _zone_bounds(annotations.zone_annotations)


def _zone_bounds(zone_annotations: tuple[ZoneAnnotation, ...]) -> tuple[float, float, float, float]:
    xs = [x for zone in zone_annotations for x, _ in zone.boundary]
    ys = [y for zone in zone_annotations for _, y in zone.boundary]
    return min(xs), max(xs), min(ys), max(ys)


def _polygon_bounds(points: tuple[tuple[float, float], ...]) -> tuple[float, float, float, float]:
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), max(xs), min(ys), max(ys)


def _draw_north_arrow(
    ax: plt.Axes,
    bounds: tuple[float, float, float, float],
    *,
    label: str,
) -> None:
    min_x, max_x, min_y, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y
    x = max_x - width * 0.07
    y = max_y - height * 0.18
    arrow_length = height * 0.12

    ax.annotate(
        "",
        xy=(x, y + arrow_length),
        xytext=(x, y),
        arrowprops={"arrowstyle": "-|>", "linewidth": 1.2, "color": "#1f2933"},
    )
    ax.text(
        x,
        y + arrow_length + height * 0.02,
        label,
        ha="center",
        va="bottom",
        fontsize=8,
        color="#1f2933",
    )


def _configure_axes(
    ax: plt.Axes,
    annotations: FloorAnnotationSet,
    *,
    title: str,
) -> tuple[float, float, float, float]:
    bounds = _figure_bounds(annotations)
    min_x, max_x, min_y, max_y = bounds
    pad_x = (max_x - min_x) * 0.08
    pad_y = (max_y - min_y) * 0.08
    ax.set_xlim(min_x - pad_x, max_x + pad_x)
    ax.set_ylim(min_y - pad_y, max_y + pad_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    ax.set_title(title, fontsize=12, color="#102a43")
    return bounds


def _save_figure(fig: plt.Figure, output_path: Path, *, file_format: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format=file_format, dpi=200)
    plt.close(fig)
    return output_path


def render_base_floorplan(
    annotations: FloorAnnotationSet,
    output_path: Path,
    *,
    file_format: str,
) -> Path:
    fig, ax = plt.subplots(figsize=(8.5, 6.5), constrained_layout=True)

    for zone in annotations.zone_annotations:
        patch = Polygon(
            zone.boundary,
            closed=True,
            fill=False,
            linewidth=1.2,
            edgecolor=OUTLINE_COLOR,
            joinstyle="round",
        )
        ax.add_patch(patch)

    bounds = _configure_axes(ax, annotations, title=annotations.floor_title)
    _draw_north_arrow(ax, bounds, label="N")

    return _save_figure(fig, output_path, file_format=file_format)


def _zone_fill_color(zone_category: str) -> str:
    if zone_category == "core":
        return CORE_FILL
    if zone_category == "perimeter":
        return PERIMETER_FILL
    return OTHER_FILL


def render_zoning_floorplan(
    annotations: FloorAnnotationSet,
    output_path: Path,
    *,
    file_format: str,
) -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 6.7), constrained_layout=True)

    for zone in annotations.zone_annotations:
        patch = Polygon(
            zone.boundary,
            closed=True,
            facecolor=_zone_fill_color(zone.zone_category),
            edgecolor=OUTLINE_COLOR,
            linewidth=1.0,
            joinstyle="round",
        )
        ax.add_patch(patch)
        ax.text(
            zone.anchor[0],
            zone.anchor[1],
            zone.zone_name.replace("_", "\n"),
            ha="center",
            va="center",
            fontsize=7.2,
            color="#102a43",
        )

    bounds = _configure_axes(ax, annotations, title="Thermal Zoning Plan")
    _draw_north_arrow(ax, bounds, label="N")

    legend_handles = [
        Patch(facecolor=CORE_FILL, edgecolor=OUTLINE_COLOR, label="Core zone"),
        Patch(facecolor=PERIMETER_FILL, edgecolor=OUTLINE_COLOR, label="Perimeter zone"),
    ]
    ax.legend(
        handles=legend_handles,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.04),
        ncol=2,
        fontsize=8,
    )

    return _save_figure(fig, output_path, file_format=file_format)


def render_system_overlay_floorplan(
    annotations: FloorAnnotationSet,
    overlay: SystemOverlay,
    output_path: Path,
    *,
    file_format: str,
) -> Path:
    fig, ax = plt.subplots(figsize=(8.8, 6.8), constrained_layout=True)

    for zone in annotations.zone_annotations:
        patch = Polygon(
            zone.boundary,
            closed=True,
            fill=False,
            edgecolor=OUTLINE_COLOR,
            linewidth=1.0,
            joinstyle="round",
        )
        ax.add_patch(patch)

    ax.plot(
        (overlay.doas_spine.start[0], overlay.doas_spine.end[0]),
        (overlay.doas_spine.start[1], overlay.doas_spine.end[1]),
        linestyle="--",
        linewidth=1.6,
        color="#52606d",
    )
    for branch in overlay.doas_branches:
        ax.plot(
            (branch.start[0], branch.end[0]),
            (branch.start[1], branch.end[1]),
            linestyle="--",
            linewidth=1.0,
            color="#7b8794",
        )
    for path in overlay.service_paths:
        ax.plot(
            (path.start[0], path.end[0]),
            (path.start[1], path.end[1]),
            linestyle="-",
            linewidth=1.0,
            color="#486581",
        )

    ax.scatter(
        [terminal.position[0] for terminal in overlay.terminals],
        [terminal.position[1] for terminal in overlay.terminals],
        s=48,
        marker=overlay.terminal_marker,
        facecolor=overlay.terminal_color,
        edgecolor=OUTLINE_COLOR,
        linewidth=0.8,
        zorder=5,
    )

    bounds = _configure_axes(ax, annotations, title=overlay.title)
    _draw_north_arrow(ax, bounds, label="N")

    legend_handles = [
        Patch(facecolor="white", edgecolor=OUTLINE_COLOR, label="Zone boundary"),
        Patch(facecolor=overlay.terminal_color, edgecolor=OUTLINE_COLOR, label=overlay.notes[0]),
        Patch(facecolor="#d9e2ec", edgecolor="#52606d", label=overlay.notes[1]),
    ]
    if len(overlay.notes) > 2:
        legend_handles.append(
            Patch(facecolor="#f0f4f8", edgecolor="#486581", label=overlay.notes[2])
        )
    ax.legend(
        handles=legend_handles,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.06),
        fontsize=7.5,
        ncol=1,
    )

    return _save_figure(fig, output_path, file_format=file_format)


def _draw_dimension_annotations(
    ax: plt.Axes,
    bounds: tuple[float, float, float, float],
) -> None:
    min_x, max_x, min_y, max_y = bounds
    width = max_x - min_x
    depth = max_y - min_y

    horizontal_y = min_y - depth * 0.14
    vertical_x = min_x - width * 0.14

    ax.plot((min_x, min_x), (min_y, horizontal_y), color=DIMENSION_COLOR, linewidth=0.8)
    ax.plot((max_x, max_x), (min_y, horizontal_y), color=DIMENSION_COLOR, linewidth=0.8)
    ax.annotate(
        "",
        xy=(max_x, horizontal_y),
        xytext=(min_x, horizontal_y),
        arrowprops={"arrowstyle": "<->", "color": DIMENSION_COLOR, "linewidth": 0.9},
    )
    ax.text(
        (min_x + max_x) / 2,
        horizontal_y - depth * 0.04,
        f"{width:.3f} m",
        ha="center",
        va="top",
        fontsize=7.6,
        color=MUTED_TEXT,
    )

    ax.plot((vertical_x, min_x), (min_y, min_y), color=DIMENSION_COLOR, linewidth=0.8)
    ax.plot((vertical_x, min_x), (max_y, max_y), color=DIMENSION_COLOR, linewidth=0.8)
    ax.annotate(
        "",
        xy=(vertical_x, max_y),
        xytext=(vertical_x, min_y),
        arrowprops={"arrowstyle": "<->", "color": DIMENSION_COLOR, "linewidth": 0.9},
    )
    ax.text(
        vertical_x - width * 0.03,
        (min_y + max_y) / 2,
        f"{depth:.3f} m",
        ha="right",
        va="center",
        fontsize=7.6,
        color=MUTED_TEXT,
        rotation=90,
    )


def _draw_horizontal_dimension(
    ax: plt.Axes,
    *,
    min_value: float,
    max_value: float,
    anchor_value: float,
    label: str,
) -> None:
    ax.plot(
        (min_value, min_value),
        (0.0, anchor_value),
        color=DIMENSION_COLOR,
        linewidth=0.8,
    )
    ax.plot(
        (max_value, max_value),
        (0.0, anchor_value),
        color=DIMENSION_COLOR,
        linewidth=0.8,
    )
    ax.annotate(
        "",
        xy=(max_value, anchor_value),
        xytext=(min_value, anchor_value),
        arrowprops={"arrowstyle": "<->", "color": DIMENSION_COLOR, "linewidth": 0.9},
    )
    ax.text(
        (min_value + max_value) / 2,
        anchor_value,
        label,
        ha="center",
        va="bottom",
        fontsize=7.4,
        color=MUTED_TEXT,
    )


def _draw_vertical_dimension(
    ax: plt.Axes,
    *,
    anchor_value: float,
    min_value: float,
    max_value: float,
    label: str,
) -> None:
    ax.plot(
        (anchor_value, 0.0),
        (min_value, min_value),
        color=DIMENSION_COLOR,
        linewidth=0.8,
    )
    ax.plot(
        (anchor_value, 0.0),
        (max_value, max_value),
        color=DIMENSION_COLOR,
        linewidth=0.8,
    )
    ax.annotate(
        "",
        xy=(anchor_value, max_value),
        xytext=(anchor_value, min_value),
        arrowprops={"arrowstyle": "<->", "color": DIMENSION_COLOR, "linewidth": 0.9},
    )
    ax.text(
        anchor_value,
        (min_value + max_value) / 2,
        label,
        ha="left",
        va="center",
        fontsize=7.4,
        color=MUTED_TEXT,
        rotation=90,
    )


def _draw_facade_labels(
    ax: plt.Axes,
    bounds: tuple[float, float, float, float],
    floor: StructureFloorAnnotation,
) -> None:
    min_x, max_x, min_y, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y
    counts = Counter(window.orientation for window in floor.windows)
    labels = {
        "North": ((min_x + max_x) / 2, max_y + height * 0.085, "center", "bottom"),
        "South": ((min_x + max_x) / 2, min_y - height * 0.21, "center", "top"),
        "West": (min_x - width * 0.18, (min_y + max_y) / 2, "right", "center"),
        "East": (max_x + width * 0.09, (min_y + max_y) / 2, "left", "center"),
    }

    for orientation, (x, y, ha, va) in labels.items():
        count = counts.get(orientation, 0)
        suffix = f" x{count}" if count > 0 else ""
        ax.text(
            x,
            y,
            f"{orientation[0]}{suffix}",
            ha=ha,
            va=va,
            fontsize=7.1,
            color=MUTED_TEXT,
        )


def _render_floor_structure_panel(
    ax: plt.Axes,
    floor: StructureFloorAnnotation,
    structure: BuildingStructureAnnotation,
) -> None:
    bounds = _zone_bounds(floor.occupied_zones)
    min_x, max_x, min_y, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y

    ax.set_xlim(min_x - width * 0.25, max_x + width * 0.16)
    ax.set_ylim(min_y - height * 0.28, max_y + height * 0.17)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()

    for polygon in floor.plenum_boundaries:
        ax.add_patch(
            Polygon(
                polygon,
                closed=True,
                facecolor=PLENUM_FILL,
                edgecolor="#9aa5b1",
                linewidth=0.9,
                linestyle="--",
                hatch="////",
                alpha=0.55,
                joinstyle="round",
                zorder=1,
            )
        )

    for zone in floor.occupied_zones:
        ax.add_patch(
            Polygon(
                zone.boundary,
                closed=True,
                facecolor=_zone_fill_color(zone.zone_category),
                edgecolor=OUTLINE_COLOR,
                linewidth=1.05,
                joinstyle="round",
                zorder=2,
            )
        )
        ax.text(
            zone.anchor[0],
            zone.anchor[1],
            zone.zone_name.replace("_", "\n"),
            ha="center",
            va="center",
            fontsize=6.3,
            color="#102a43",
            zorder=4,
        )

    for window in floor.windows:
        ax.plot(
            (window.segment[0][0], window.segment[1][0]),
            (window.segment[0][1], window.segment[1][1]),
            color=WINDOW_COLOR,
            linewidth=2.8,
            solid_capstyle="round",
            zorder=5,
        )

    _draw_dimension_annotations(ax, bounds)
    _draw_facade_labels(ax, bounds, floor)
    _draw_north_arrow(ax, bounds, label="N")

    title_lines = [floor.floor_title, f"Occupied z = {floor.floor_elevation:.3f} m"]
    if floor.plenum_elevation is not None:
        title_lines.append(f"Plenum z = {floor.plenum_elevation:.3f} m")
    ax.set_title("\n".join(title_lines), fontsize=10.6, color="#102a43", pad=10)
    ax.text(
        0.02,
        0.98,
        f"{len(floor.occupied_zones)} thermal zones",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.4,
        color=MUTED_TEXT,
    )


def _draw_overlay_on_floor_panel(
    ax: plt.Axes,
    floor: StructureFloorAnnotation,
    overlay: SystemOverlay,
) -> None:
    for branch in overlay.doas_branches:
        ax.plot(
            (branch.start[0], branch.end[0]),
            (branch.start[1], branch.end[1]),
            linestyle="--",
            linewidth=1.1,
            color=DOAS_COLOR,
            zorder=6,
        )

    if overlay.doas_branches:
        spine_y = overlay.doas_branches[0].start[1]
    else:
        bounds = _zone_bounds(floor.occupied_zones)
        spine_y = bounds[3]

    min_x = min(point[0] for zone in floor.occupied_zones for point in zone.boundary)
    max_x = max(point[0] for zone in floor.occupied_zones for point in zone.boundary)
    ax.plot(
        (min_x, max_x),
        (spine_y, spine_y),
        linestyle="--",
        linewidth=1.5,
        color=DOAS_COLOR,
        zorder=6,
    )

    if overlay.system_type == "fcu_doas":
        for path in overlay.service_paths:
            x_values = (path.start[0], path.end[0])
            y_values = (path.start[1], path.end[1])
            ax.plot(
                x_values,
                y_values,
                linestyle="-",
                linewidth=1.1,
                color="#2f855a",
                zorder=6,
            )

    ax.scatter(
        [terminal.position[0] for terminal in overlay.terminals],
        [terminal.position[1] for terminal in overlay.terminals],
        s=42,
        marker=overlay.terminal_marker,
        facecolor=overlay.terminal_color,
        edgecolor=OUTLINE_COLOR,
        linewidth=0.8,
        zorder=7,
    )

    bounds = _zone_bounds(floor.occupied_zones)
    min_x, max_x, min_y, max_y = bounds
    label_x = min_x + (max_x - min_x) * 0.03
    label_y = max_y + (max_y - min_y) * 0.11
    ax.text(
        label_x,
        label_y,
        "DOAS",
        ha="left",
        va="center",
        fontsize=7.2,
        color=DOAS_COLOR,
        zorder=7,
    )


def _render_roof_plan(
    ax: plt.Axes,
    structure: BuildingStructureAnnotation,
) -> None:
    bounds = _polygon_bounds(structure.roof_outline)
    min_x, max_x, min_y, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y

    ax.set_xlim(min_x - width * 0.25, max_x + width * 0.16)
    ax.set_ylim(min_y - height * 0.28, max_y + height * 0.17)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()

    ax.add_patch(
        Polygon(
            structure.roof_outline,
            closed=True,
            facecolor=WALL_FILL,
            edgecolor=OUTLINE_COLOR,
            linewidth=1.1,
            joinstyle="round",
        )
    )
    ax.text(
        (min_x + max_x) / 2,
        (min_y + max_y) / 2,
        f"Roof slab\nz = {structure.roof_elevation:.4f} m",
        ha="center",
        va="center",
        fontsize=8.2,
        color="#102a43",
    )
    _draw_dimension_annotations(ax, bounds)
    _draw_north_arrow(ax, bounds, label="N")
    ax.set_title("Roof Plan", fontsize=10.8, color="#102a43", pad=10)


def _render_system_roof_plan(
    ax: plt.Axes,
    structure: BuildingStructureAnnotation,
    overlay: SystemOverlay,
) -> None:
    _render_roof_plan(ax, structure)
    min_x, max_x, min_y, max_y = _polygon_bounds(structure.roof_outline)
    width = max_x - min_x
    height = max_y - min_y

    if overlay.system_type == "vrf_doas":
        label_specs = [
            (
                overlay.roof_equipment_labels[0],
                (min_x + width * 0.22, min_y + height * 0.72),
                DOAS_COLOR,
                "round",
            ),
            (
                overlay.roof_equipment_labels[1],
                (min_x + width * 0.68, min_y + height * 0.36),
                overlay.terminal_color,
                "square",
            ),
        ]
    else:
        label_specs = [
            (
                overlay.roof_equipment_labels[0],
                (min_x + width * 0.28, min_y + height * 0.68),
                DOAS_COLOR,
                "round",
            ),
        ]

    for label, (center_x, center_y), color, shape in label_specs:
        if shape == "round":
            patch = plt.Circle((center_x, center_y), radius=min(width, height) * 0.06, facecolor="white", edgecolor=color, linewidth=1.3)
        else:
            patch = Rectangle((center_x - width * 0.06, center_y - height * 0.05), width * 0.12, height * 0.1, facecolor="white", edgecolor=color, linewidth=1.3)
        ax.add_patch(patch)
        ax.text(
            center_x,
            center_y,
            label,
            ha="center",
            va="center",
            fontsize=7.2,
            color="#102a43",
            zorder=6,
        )


def _render_facade_elevation(
    ax: plt.Axes,
    facade: FacadeAnnotation,
    structure: BuildingStructureAnnotation,
) -> None:
    all_points = [point for wall in facade.walls for point in wall.boundary]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    width = max_x - min_x
    height = max_y - min_y

    ax.set_xlim(min_x - width * 0.05, max_x + width * 0.14)
    ax.set_ylim(min_y - height * 0.12, max_y + height * 0.1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()

    for wall in facade.walls:
        ax.add_patch(
            Polygon(
                wall.boundary,
                closed=True,
                facecolor=PLENUM_FILL if wall.is_plenum else WALL_FILL,
                edgecolor="#7b8794" if wall.is_plenum else OUTLINE_COLOR,
                linewidth=0.95,
                linestyle="--" if wall.is_plenum else "-",
                hatch="////" if wall.is_plenum else None,
                alpha=0.95 if wall.is_plenum else 1.0,
                joinstyle="round",
            )
        )

    for window in facade.windows:
        ax.add_patch(
            Polygon(
                window.boundary,
                closed=True,
                facecolor="#bfdbfe",
                edgecolor=WINDOW_COLOR,
                linewidth=1.05,
                joinstyle="round",
            )
        )

    for floor in structure.floors:
        ax.hlines(
            floor.floor_elevation,
            min_x,
            max_x,
            colors="#9aa5b1",
            linestyles=":",
            linewidth=0.8,
        )
    ax.hlines(
        structure.roof_elevation,
        min_x,
        max_x,
        colors=OUTLINE_COLOR,
        linestyles="-",
        linewidth=1.2,
    )
    ax.hlines(0.0, min_x, max_x, colors="#52606d", linestyles="-", linewidth=1.0)

    _draw_horizontal_dimension(
        ax,
        min_value=min_x,
        max_value=max_x,
        anchor_value=max_y + height * 0.03,
        label=f"{facade.width:.3f} m",
    )
    _draw_vertical_dimension(
        ax,
        anchor_value=max_x + width * 0.08,
        min_value=0.0,
        max_value=structure.roof_elevation,
        label=f"{structure.roof_elevation:.3f} m",
    )

    ax.text(
        min_x,
        max_y + height * 0.11,
        f"{facade.orientation} Elevation",
        ha="left",
        va="bottom",
        fontsize=10.1,
        color="#102a43",
        fontweight="bold",
    )
    ax.text(
        min_x,
        min_y - height * 0.07,
        f"{len(facade.walls)} exterior wall panels, {len(facade.windows)} window bands",
        ha="left",
        va="top",
        fontsize=7.1,
        color=MUTED_TEXT,
    )


def _render_system_facade_elevation(
    ax: plt.Axes,
    facade: FacadeAnnotation,
    structure: BuildingStructureAnnotation,
    overlay: SystemOverlay,
) -> None:
    _render_facade_elevation(ax, facade, structure)
    if overlay.system_type != "vrf_doas" or facade.orientation != "South":
        return

    all_points = [point for wall in facade.walls for point in wall.boundary]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    width = max_x - min_x
    height = max_y - min_y

    bank_left = max_x - width * 0.34
    bank_base_y = structure.roof_elevation + height * 0.018
    unit_width = width * 0.045
    unit_height = height * 0.055
    gap = width * 0.012

    for index in range(5):
        current_x = bank_left + index * (unit_width + gap)
        ax.add_patch(
            Rectangle(
                (current_x, bank_base_y),
                unit_width,
                unit_height,
                facecolor=VRF_PLATFORM_FILL,
                edgecolor=overlay.terminal_color,
                linewidth=1.0,
                zorder=7,
            )
        )
        ax.plot(
            (current_x + unit_width * 0.18, current_x + unit_width * 0.82),
            (bank_base_y + unit_height * 0.5, bank_base_y + unit_height * 0.5),
            color=overlay.terminal_color,
            linewidth=0.8,
            zorder=8,
        )

    leader_x = bank_left + unit_width * 2.6
    leader_y = bank_base_y + unit_height * 1.15
    ax.annotate(
        "Concentrated VRF outdoor-unit bank",
        xy=(leader_x, bank_base_y + unit_height * 0.9),
        xytext=(min_x + width * 0.12, max_y + height * 0.14),
        fontsize=7.6,
        color=overlay.terminal_color,
        ha="left",
        va="bottom",
        arrowprops={
            "arrowstyle": "-|>",
            "linewidth": 1.0,
            "color": overlay.terminal_color,
        },
        zorder=9,
    )
    ax.text(
        bank_left,
        bank_base_y - height * 0.022,
        "Roof edge mechanical platform",
        ha="left",
        va="top",
        fontsize=7.1,
        color=MUTED_TEXT,
        zorder=8,
    )


def _render_story_section(
    ax: plt.Axes,
    structure: BuildingStructureAnnotation,
) -> None:
    ax.set_facecolor(INFO_PANEL_FILL)
    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(-0.6, structure.roof_elevation + 0.9)
    ax.set_axis_off()

    block_left = 3.0
    block_width = 3.5
    block_right = block_left + block_width

    for index, floor in enumerate(structure.floors):
        next_floor_elevation = (
            structure.floors[index + 1].floor_elevation
            if index + 1 < len(structure.floors)
            else structure.roof_elevation
        )
        occupied_top = floor.plenum_elevation or next_floor_elevation

        ax.add_patch(
            Rectangle(
                (block_left, floor.floor_elevation),
                block_width,
                occupied_top - floor.floor_elevation,
                facecolor=SECTION_OCCUPIED_FILL,
                edgecolor=OUTLINE_COLOR,
                linewidth=1.0,
            )
        )
        ax.text(
            block_left + block_width / 2,
            floor.floor_elevation + (occupied_top - floor.floor_elevation) / 2,
            f"{index + 1}F occupied\n{occupied_top - floor.floor_elevation:.3f} m",
            ha="center",
            va="center",
            fontsize=8.1,
            color="#102a43",
        )

        if floor.plenum_elevation is not None and floor.plenum_elevation < next_floor_elevation:
            ax.add_patch(
                Rectangle(
                    (block_left, floor.plenum_elevation),
                    block_width,
                    next_floor_elevation - floor.plenum_elevation,
                    facecolor=PLENUM_FILL,
                    edgecolor="#9aa5b1",
                    linewidth=0.9,
                    linestyle="--",
                    hatch="////",
                    alpha=0.75,
                )
            )
            ax.text(
                block_right + 0.45,
                floor.plenum_elevation + (next_floor_elevation - floor.plenum_elevation) / 2,
                f"Plenum {next_floor_elevation - floor.plenum_elevation:.3f} m",
                ha="left",
                va="center",
                fontsize=7.7,
                color=MUTED_TEXT,
            )

        level_lines = [
            (floor.floor_elevation, f"{floor.floor_elevation:.3f} m"),
        ]
        if floor.plenum_elevation is not None:
            level_lines.append((floor.plenum_elevation, f"{floor.plenum_elevation:.3f} m"))

        for level, label in level_lines:
            ax.hlines(level, 1.4, 8.8, colors="#9aa5b1", linestyles=":", linewidth=0.8)
            ax.text(1.15, level, label, ha="right", va="center", fontsize=7.5, color=MUTED_TEXT)

    ax.hlines(
        structure.roof_elevation,
        1.4,
        8.8,
        colors=OUTLINE_COLOR,
        linestyles="-",
        linewidth=1.3,
    )
    ax.text(
        1.15,
        structure.roof_elevation,
        f"{structure.roof_elevation:.4f} m roof",
        ha="right",
        va="center",
        fontsize=7.7,
        color="#102a43",
    )

    ax.annotate(
        "",
        xy=(2.2, structure.roof_elevation),
        xytext=(2.2, structure.floors[0].floor_elevation),
        arrowprops={"arrowstyle": "<->", "linewidth": 1.0, "color": DIMENSION_COLOR},
    )
    ax.text(
        2.0,
        (structure.roof_elevation + structure.floors[0].floor_elevation) / 2,
        f"Total height\n{structure.roof_elevation - structure.floors[0].floor_elevation:.3f} m",
        ha="right",
        va="center",
        fontsize=7.9,
        color=MUTED_TEXT,
        rotation=90,
    )

    ax.annotate(
        "",
        xy=(block_right, -0.18),
        xytext=(block_left, -0.18),
        arrowprops={"arrowstyle": "<->", "linewidth": 1.0, "color": DIMENSION_COLOR},
    )
    ax.text(
        block_left + block_width / 2,
        -0.38,
        f"Footprint width {structure.footprint_width:.3f} m",
        ha="center",
        va="top",
        fontsize=7.8,
        color=MUTED_TEXT,
    )
    ax.set_title("Sectional Story Stack", fontsize=11, color="#102a43", pad=8)


def _render_system_story_section(
    ax: plt.Axes,
    structure: BuildingStructureAnnotation,
    overlay: SystemOverlay,
) -> None:
    _render_story_section(ax, structure)

    block_left = 3.0
    block_width = 3.5
    center_x = block_left + block_width / 2
    if overlay.system_type == "vrf_doas":
        service_x = 7.7
        ax.plot(
            (service_x, service_x),
            (structure.floors[0].floor_elevation, structure.roof_elevation),
            color=overlay.terminal_color,
            linewidth=1.8,
            zorder=7,
        )
        ax.text(
            service_x + 0.18,
            (structure.floors[0].floor_elevation + structure.roof_elevation) / 2,
            overlay.section_service_label,
            ha="left",
            va="center",
            fontsize=7.8,
            color=overlay.terminal_color,
            rotation=90,
            zorder=8,
        )
        for floor in structure.floors:
            occupied_top = floor.plenum_elevation or structure.roof_elevation
            mid_y = floor.floor_elevation + (occupied_top - floor.floor_elevation) / 2
            ax.plot(
                (center_x + 1.75, service_x),
                (mid_y, mid_y),
                color=overlay.terminal_color,
                linewidth=1.0,
                zorder=7,
            )
            ax.scatter(
                [center_x + 1.75],
                [mid_y],
                s=28,
                marker=overlay.terminal_marker,
                facecolor=overlay.terminal_color,
                edgecolor=OUTLINE_COLOR,
                linewidth=0.7,
                zorder=8,
            )

        doas_x = 8.55
        ax.plot(
            (doas_x, doas_x),
            (structure.floors[0].floor_elevation, structure.roof_elevation),
            color=DOAS_COLOR,
            linewidth=1.5,
            linestyle="--",
            zorder=7,
        )
        ax.text(
            doas_x + 0.12,
            (structure.floors[0].floor_elevation + structure.roof_elevation) / 2,
            "DOAS duct shaft",
            ha="left",
            va="center",
            fontsize=7.5,
            color=DOAS_COLOR,
            rotation=90,
            zorder=8,
        )
        for floor in structure.floors:
            occupied_top = floor.plenum_elevation or structure.roof_elevation
            branch_y = occupied_top - (occupied_top - floor.floor_elevation) * 0.18
            ax.plot(
                (block_left + block_width, doas_x),
                (branch_y, branch_y),
                color=DOAS_COLOR,
                linewidth=0.95,
                linestyle="--",
                zorder=7,
            )

        bank_left = 6.55
        bank_base_y = structure.roof_elevation + 0.12
        unit_width = 0.22
        unit_height = 0.22
        for index in range(4):
            current_x = bank_left + index * (unit_width + 0.07)
            ax.add_patch(
                Rectangle(
                    (current_x, bank_base_y),
                    unit_width,
                    unit_height,
                    facecolor=VRF_PLATFORM_FILL,
                    edgecolor=overlay.terminal_color,
                    linewidth=0.9,
                    zorder=8,
                )
            )
        ax.annotate(
            "ODU bank",
            xy=(bank_left + 0.55, bank_base_y + 0.1),
            xytext=(5.85, structure.roof_elevation + 0.52),
            fontsize=7.5,
            color=overlay.terminal_color,
            ha="left",
            va="bottom",
            arrowprops={"arrowstyle": "-|>", "linewidth": 0.9, "color": overlay.terminal_color},
            zorder=9,
        )
        ax.plot(
            (service_x, bank_left + 0.48),
            (structure.roof_elevation, bank_base_y),
            color=overlay.terminal_color,
            linewidth=1.0,
            zorder=8,
        )
        return

    pipe_x = 7.12
    pipe_width = 0.28
    duct_x = 8.12
    duct_width = 0.34
    base_y = structure.floors[0].floor_elevation
    total_height = structure.roof_elevation - base_y

    ax.add_patch(
        Rectangle(
            (pipe_x, base_y),
            pipe_width,
            total_height,
            facecolor="#dcfce7",
            edgecolor=PIPE_COLOR,
            linewidth=1.2,
            zorder=7,
        )
    )
    ax.add_patch(
        Rectangle(
            (duct_x, base_y),
            duct_width,
            total_height,
            facecolor=PLENUM_FILL,
            edgecolor=DOAS_COLOR,
            linewidth=1.0,
            linestyle="--",
            hatch="////",
            alpha=0.85,
            zorder=7,
        )
    )
    ax.text(
        pipe_x + pipe_width / 2,
        base_y + total_height / 2,
        "CHW/HW\npipe shaft",
        ha="center",
        va="center",
        fontsize=7.3,
        color=PIPE_COLOR,
        rotation=90,
        zorder=8,
    )
    ax.text(
        duct_x + duct_width / 2,
        base_y + total_height / 2,
        "DOAS\nduct shaft",
        ha="center",
        va="center",
        fontsize=7.3,
        color=DOAS_COLOR,
        rotation=90,
        zorder=8,
    )
    for floor in structure.floors:
        occupied_top = floor.plenum_elevation or structure.roof_elevation
        terminal_y = floor.floor_elevation + (occupied_top - floor.floor_elevation) / 2
        plenum_y = occupied_top - (occupied_top - floor.floor_elevation) * 0.16
        ax.plot(
            (center_x + 1.75, pipe_x),
            (terminal_y, terminal_y),
            color=PIPE_COLOR,
            linewidth=1.0,
            zorder=8,
        )
        ax.plot(
            (block_left + block_width, duct_x),
            (plenum_y, plenum_y),
            color=DOAS_COLOR,
            linewidth=0.95,
            linestyle="--",
            zorder=8,
        )
        ax.scatter(
            [center_x + 1.75],
            [terminal_y],
            s=28,
            marker=overlay.terminal_marker,
            facecolor=overlay.terminal_color,
            edgecolor=OUTLINE_COLOR,
            linewidth=0.7,
            zorder=9,
        )
    ax.annotate(
        "Separated shafts improve duct and hydronic routing clarity",
        xy=(duct_x + duct_width / 2, structure.roof_elevation - 0.2),
        xytext=(5.85, structure.roof_elevation + 0.42),
        fontsize=7.3,
        color=MUTED_TEXT,
        ha="left",
        va="bottom",
        arrowprops={"arrowstyle": "-|>", "linewidth": 0.8, "color": MUTED_TEXT},
        zorder=9,
    )


def _render_structure_info_panel(
    ax: plt.Axes,
    structure: BuildingStructureAnnotation,
) -> None:
    ax.set_facecolor(INFO_PANEL_FILL)
    ax.set_axis_off()

    occupied_levels = ", ".join(f"{floor.floor_elevation:.3f}" for floor in structure.floors)
    plenum_levels = ", ".join(
        f"{floor.plenum_elevation:.3f}"
        for floor in structure.floors
        if floor.plenum_elevation is not None
    )
    window_summary = ", ".join(f"{name} {count}" for name, count in structure.window_orientation_counts)
    surface_summary = ", ".join(f"{name} {count}" for name, count in structure.surface_type_counts)
    total_windows = sum(count for _, count in structure.window_orientation_counts)

    ax.text(
        0.05,
        0.97,
        "Model Summary",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11.2,
        color="#102a43",
        fontweight="bold",
    )

    summary_text = "\n".join(
        [
            f"Occupied stories: {len(structure.floors)}",
            f"Footprint: {structure.footprint_width:.3f} m x {structure.footprint_depth:.3f} m",
            f"Roof elevation: {structure.roof_elevation:.4f} m",
            f"Occupied levels: {occupied_levels} m",
            f"Plenum levels: {plenum_levels} m",
            f"Facade window bands: {total_windows}",
            f"Window orientations: {window_summary}",
            f"Envelope surfaces: {surface_summary}",
        ]
    )
    ax.text(
        0.05,
        0.86,
        summary_text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.3,
        color="#243b53",
        linespacing=1.55,
    )

    legend_handles = [
        Patch(facecolor=CORE_FILL, edgecolor=OUTLINE_COLOR, label="Core zone"),
        Patch(facecolor=PERIMETER_FILL, edgecolor=OUTLINE_COLOR, label="Perimeter zone"),
        Patch(
            facecolor=PLENUM_FILL,
            edgecolor="#9aa5b1",
            label="Plenum footprint",
            hatch="////",
        ),
        Line2D([0], [0], color=WINDOW_COLOR, linewidth=2.8, label="Facade window band"),
        Patch(facecolor=SECTION_OCCUPIED_FILL, edgecolor=OUTLINE_COLOR, label="Occupied section"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(0.03, 0.04),
        frameon=False,
        fontsize=7.9,
        handlelength=2.2,
        labelspacing=0.9,
    )


def _render_system_info_panel(
    ax: plt.Axes,
    structure: BuildingStructureAnnotation,
    overlay: SystemOverlay,
) -> None:
    ax.set_facecolor(INFO_PANEL_FILL)
    ax.set_axis_off()

    terminal_count = len(overlay.terminals) * len(structure.floors)
    roof_equipment = ", ".join(overlay.roof_equipment_labels)

    ax.text(
        0.05,
        0.97,
        overlay.title,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11.2,
        color="#102a43",
        fontweight="bold",
    )

    summary_text = "\n".join(
        [
            f"Occupied stories served: {len(structure.floors)}",
            f"Per-floor terminals: {len(overlay.terminals)}",
            f"Model total terminals: {terminal_count}",
            f"Roof equipment: {roof_equipment}",
            f"Outdoor air distribution: one main spine plus zone branches",
            f"Vertical service: {overlay.section_service_label}",
            (
                "Facade emphasis: concentrated rooftop ODU bank on south elevation"
                if overlay.system_type == "vrf_doas"
                else "Section emphasis: separated DOAS duct shaft and CHW/HW pipe shaft"
            ),
            f"Building footprint: {structure.footprint_width:.3f} m x {structure.footprint_depth:.3f} m",
            f"Roof elevation: {structure.roof_elevation:.4f} m",
        ]
    )
    ax.text(
        0.05,
        0.84,
        summary_text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.3,
        color="#243b53",
        linespacing=1.55,
    )

    legend_handles = [
        Patch(facecolor=CORE_FILL, edgecolor=OUTLINE_COLOR, label="Conditioned zone"),
        Line2D([0], [0], color=DOAS_COLOR, linewidth=1.5, linestyle="--", label="DOAS duct / shaft"),
        Line2D([0], [0], color=overlay.terminal_color, linewidth=1.5, label=overlay.section_service_label),
        Line2D(
            [0],
            [0],
            color=overlay.terminal_color,
            marker=overlay.terminal_marker,
            linewidth=0,
            markeredgecolor=OUTLINE_COLOR,
            markerfacecolor=overlay.terminal_color,
            label=overlay.notes[0],
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        bbox_to_anchor=(0.03, 0.04),
        frameon=False,
        fontsize=7.9,
        handlelength=2.2,
        labelspacing=0.9,
    )

    ax.text(
        0.05,
        0.36,
        "\n".join(overlay.notes),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.0,
        color=MUTED_TEXT,
        linespacing=1.55,
    )


def render_building_structure(
    structure: BuildingStructureAnnotation,
    output_path: Path,
    *,
    file_format: str,
) -> Path:
    fig = plt.figure(figsize=(19.2, 14.0), constrained_layout=True)
    outer = fig.add_gridspec(
        3,
        2,
        width_ratios=(5.2, 1.45),
        height_ratios=(2.3, 2.0, 1.45),
    )

    plans_grid = outer[0, 0].subgridspec(1, 4, wspace=0.08)
    for index, floor in enumerate(structure.floors):
        ax = fig.add_subplot(plans_grid[0, index])
        _render_floor_structure_panel(ax, floor, structure)
    roof_ax = fig.add_subplot(plans_grid[0, 3])
    _render_roof_plan(roof_ax, structure)

    facades_grid = outer[1, 0].subgridspec(2, 2, hspace=0.1, wspace=0.08)
    for index, facade in enumerate(structure.facades):
        ax = fig.add_subplot(facades_grid[index // 2, index % 2])
        _render_facade_elevation(ax, facade, structure)

    section_ax = fig.add_subplot(outer[2, 0])
    _render_story_section(section_ax, structure)

    info_ax = fig.add_subplot(outer[:, 1])
    _render_structure_info_panel(info_ax, structure)

    fig.suptitle(
        "IDF-Derived Medium Office Building Structure\n"
        "Plan, roof, facade, and section views reconstructed from EnergyPlus model geometry",
        fontsize=14,
        color="#102a43",
    )
    return _save_figure(fig, output_path, file_format=file_format)


def render_system_overlay_building(
    structure: BuildingStructureAnnotation,
    overlay: SystemOverlay,
    output_path: Path,
    *,
    file_format: str,
) -> Path:
    fig = plt.figure(figsize=(19.2, 14.0), constrained_layout=True)
    outer = fig.add_gridspec(
        3,
        2,
        width_ratios=(5.2, 1.45),
        height_ratios=(2.3, 2.0, 1.45),
    )

    plans_grid = outer[0, 0].subgridspec(1, 4, wspace=0.08)
    for index, floor in enumerate(structure.floors):
        ax = fig.add_subplot(plans_grid[0, index])
        _render_floor_structure_panel(ax, floor, structure)
        _draw_overlay_on_floor_panel(ax, floor, overlay)
    roof_ax = fig.add_subplot(plans_grid[0, 3])
    _render_system_roof_plan(roof_ax, structure, overlay)

    facades_grid = outer[1, 0].subgridspec(2, 2, hspace=0.1, wspace=0.08)
    for index, facade in enumerate(structure.facades):
        ax = fig.add_subplot(facades_grid[index // 2, index % 2])
        _render_system_facade_elevation(ax, facade, structure, overlay)

    section_ax = fig.add_subplot(outer[2, 0])
    _render_system_story_section(section_ax, structure, overlay)

    info_ax = fig.add_subplot(outer[:, 1])
    _render_system_info_panel(info_ax, structure, overlay)

    fig.suptitle(
        f"{overlay.title}\nSystem topology overlaid on plan, roof, facade, and section views",
        fontsize=14,
        color="#102a43",
    )
    return _save_figure(fig, output_path, file_format=file_format)
