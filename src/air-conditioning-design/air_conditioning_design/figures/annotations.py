# Ref: docs/spec/task.md (Task-ID: IMPL-IDF-FLOORPLAN-001)
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from air_conditioning_design.figures.geometry import FloorplanGeometry
from air_conditioning_design.idf.io import IdfObject, load_idf


@dataclass(frozen=True, slots=True)
class ZoneAnnotation:
    zone_name: str
    floor_elevation: float
    boundary: tuple[tuple[float, float], ...]
    anchor: tuple[float, float]
    zone_category: str


@dataclass(frozen=True, slots=True)
class FloorAnnotationSet:
    floor_elevation: float
    zone_annotations: tuple[ZoneAnnotation, ...]
    north_arrow_label: str
    north_arrow_vector: tuple[float, float]
    floor_title: str
    legend_labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WindowAnnotation:
    floor_elevation: float
    segment: tuple[tuple[float, float], tuple[float, float]]
    orientation: str


@dataclass(frozen=True, slots=True)
class FacadeSurfaceAnnotation:
    surface_name: str
    zone_name: str
    orientation: str
    boundary: tuple[tuple[float, float], ...]
    zone_category: str
    is_plenum: bool


@dataclass(frozen=True, slots=True)
class FacadeWindowAnnotation:
    window_name: str
    orientation: str
    boundary: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class FacadeAnnotation:
    orientation: str
    walls: tuple[FacadeSurfaceAnnotation, ...]
    windows: tuple[FacadeWindowAnnotation, ...]
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class StructureFloorAnnotation:
    floor_elevation: float
    floor_title: str
    occupied_zones: tuple[ZoneAnnotation, ...]
    plenum_boundaries: tuple[tuple[tuple[float, float], ...], ...]
    plenum_elevation: float | None
    windows: tuple[WindowAnnotation, ...]


@dataclass(frozen=True, slots=True)
class BuildingStructureAnnotation:
    floors: tuple[StructureFloorAnnotation, ...]
    roof_outline: tuple[tuple[float, float], ...]
    facades: tuple[FacadeAnnotation, ...]
    footprint_width: float
    footprint_depth: float
    roof_elevation: float
    window_orientation_counts: tuple[tuple[str, int], ...]
    surface_type_counts: tuple[tuple[str, int], ...]
    north_arrow_label: str
    north_arrow_vector: tuple[float, float]


def _surface_vertices(surface: IdfObject) -> tuple[tuple[float, float, float], ...]:
    vertex_count = int(float(surface.fields[10]))
    start = 11
    coordinates = surface.fields[start : start + vertex_count * 3]

    vertices = []
    for index in range(0, len(coordinates), 3):
        x = round(float(coordinates[index]), 6)
        y = round(float(coordinates[index + 1]), 6)
        z = round(float(coordinates[index + 2]), 6)
        vertices.append((x, y, z))
    return tuple(vertices)


def _fenestration_vertices(surface: IdfObject) -> tuple[tuple[float, float, float], ...]:
    vertex_count = int(float(surface.fields[8]))
    start = 9
    coordinates = surface.fields[start : start + vertex_count * 3]

    vertices = []
    for index in range(0, len(coordinates), 3):
        x = round(float(coordinates[index]), 6)
        y = round(float(coordinates[index + 1]), 6)
        z = round(float(coordinates[index + 2]), 6)
        vertices.append((x, y, z))
    return tuple(vertices)


def _polygon_centroid(points: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    x_total = sum(point[0] for point in points)
    y_total = sum(point[1] for point in points)
    count = len(points)
    return (round(x_total / count, 6), round(y_total / count, 6))


def _zone_category(zone_name: str) -> str:
    upper_name = zone_name.upper()
    if "CORE" in upper_name:
        return "core"
    if "PERIMETER" in upper_name:
        return "perimeter"
    return "other"


def _floor_title(zone_names: tuple[str, ...]) -> str:
    upper_names = tuple(name.upper() for name in zone_names)
    if any("_MID" in name for name in upper_names):
        return "Typical Floor Plan"
    if any("_TOP" in name for name in upper_names):
        return "Top Floor Plan"
    if any("_BOT" in name or "BOTTOM" in name for name in upper_names):
        return "Ground Floor Plan"
    return "Floor Plan"


def _legend_labels(zone_annotations: tuple[ZoneAnnotation, ...]) -> tuple[str, ...]:
    labels = []
    categories = {zone.zone_category for zone in zone_annotations}
    if "core" in categories:
        labels.append("Core zone")
    if "perimeter" in categories:
        labels.append("Perimeter zone")
    if "other" in categories:
        labels.append("Other zone")
    return tuple(labels)


def _floor_surfaces_from_objects(
    objects: list[IdfObject],
) -> list[tuple[str, float, tuple[tuple[float, float], ...]]]:
    surfaces: list[tuple[str, float, tuple[tuple[float, float], ...]]] = []

    for obj in objects:
        if obj.class_name != "BuildingSurface:Detailed":
            continue
        if len(obj.fields) < 10 or obj.fields[1] != "Floor":
            continue

        zone_name = obj.fields[3]
        vertices = _surface_vertices(obj)
        elevations = {round(vertex[2], 3) for vertex in vertices}
        if len(elevations) != 1:
            continue

        surfaces.append(
            (
                zone_name,
                next(iter(elevations)),
                tuple((x, y) for x, y, _ in vertices),
            )
        )

    return surfaces


def _floor_surfaces(idf_path: Path) -> list[tuple[str, float, tuple[tuple[float, float], ...]]]:
    return _floor_surfaces_from_objects(load_idf(idf_path))


def _window_segment(
    vertices: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float], tuple[float, float]]:
    unique_points: list[tuple[float, float]] = []
    for x, y, _ in vertices:
        point = (x, y)
        if point not in unique_points:
            unique_points.append(point)
    if len(unique_points) < 2:
        raise ValueError("Fenestration surface does not project to a valid 2D window segment.")
    ordered = tuple(sorted(unique_points[:2]))
    return ordered[0], ordered[1]


def _window_orientation(window_name: str, parent_surface_name: str) -> str:
    text = f"{window_name} {parent_surface_name}".upper()
    for orientation in ("SOUTH", "EAST", "NORTH", "WEST"):
        if orientation in text:
            return orientation.title()
    return "Unknown"


def _surface_orientation(surface_name: str) -> str:
    upper_name = surface_name.upper()
    for orientation in ("SOUTH", "EAST", "NORTH", "WEST"):
        if orientation in upper_name:
            return orientation.title()
    return "Unknown"


def _project_vertices_to_facade(
    vertices: tuple[tuple[float, float, float], ...],
    orientation: str,
) -> tuple[tuple[float, float], ...]:
    if orientation in {"South", "North"}:
        return tuple((x, z) for x, _, z in vertices)
    if orientation in {"East", "West"}:
        return tuple((y, z) for _, y, z in vertices)
    raise ValueError(f"Unsupported facade orientation: {orientation}")


def _window_annotations_from_objects(
    objects: list[IdfObject],
    occupied_elevations: tuple[float, ...],
) -> tuple[WindowAnnotation, ...]:
    windows: list[WindowAnnotation] = []

    for obj in objects:
        if obj.class_name != "FenestrationSurface:Detailed" or len(obj.fields) < 10:
            continue
        vertices = _fenestration_vertices(obj)
        average_z = round(sum(vertex[2] for vertex in vertices) / len(vertices), 3)
        floor_elevation = max(
            (elevation for elevation in occupied_elevations if elevation <= average_z),
            default=occupied_elevations[0],
        )
        windows.append(
            WindowAnnotation(
                floor_elevation=floor_elevation,
                segment=_window_segment(vertices),
                orientation=_window_orientation(obj.fields[0], obj.fields[3]),
            )
        )

    return tuple(windows)


def _roof_outline_from_objects(objects: list[IdfObject]) -> tuple[tuple[float, float], ...]:
    for obj in objects:
        if obj.class_name != "BuildingSurface:Detailed" or len(obj.fields) < 11:
            continue
        if obj.fields[1] != "Roof":
            continue
        return tuple((x, y) for x, y, _ in _surface_vertices(obj))
    raise ValueError("No roof surface was found in the IDF objects.")


def _facade_annotations_from_objects(objects: list[IdfObject]) -> tuple[FacadeAnnotation, ...]:
    orientation_order = ("South", "East", "North", "West")
    wall_groups: dict[str, list[FacadeSurfaceAnnotation]] = {orientation: [] for orientation in orientation_order}
    window_groups: dict[str, list[FacadeWindowAnnotation]] = {
        orientation: [] for orientation in orientation_order
    }

    for obj in objects:
        if obj.class_name == "BuildingSurface:Detailed" and len(obj.fields) > 10:
            if obj.fields[1] != "Wall" or obj.fields[5] != "Outdoors":
                continue
            orientation = _surface_orientation(obj.fields[0])
            if orientation == "Unknown":
                continue
            zone_name = obj.fields[3]
            wall_groups[orientation].append(
                FacadeSurfaceAnnotation(
                    surface_name=obj.fields[0],
                    zone_name=zone_name,
                    orientation=orientation,
                    boundary=_project_vertices_to_facade(_surface_vertices(obj), orientation),
                    zone_category=_zone_category(zone_name),
                    is_plenum="PLENUM" in zone_name.upper(),
                )
            )
        if obj.class_name == "FenestrationSurface:Detailed" and len(obj.fields) > 9:
            orientation = _window_orientation(obj.fields[0], obj.fields[3])
            if orientation == "Unknown":
                continue
            window_groups[orientation].append(
                FacadeWindowAnnotation(
                    window_name=obj.fields[0],
                    orientation=orientation,
                    boundary=_project_vertices_to_facade(
                        _fenestration_vertices(obj),
                        orientation,
                    ),
                )
            )

    facades: list[FacadeAnnotation] = []
    for orientation in orientation_order:
        walls = tuple(wall_groups[orientation])
        windows = tuple(window_groups[orientation])
        points = [point for wall in walls for point in wall.boundary]
        if not points:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        facades.append(
            FacadeAnnotation(
                orientation=orientation,
                walls=walls,
                windows=windows,
                width=round(max(xs) - min(xs), 3),
                height=round(max(ys) - min(ys), 4),
            )
        )
    return tuple(facades)


def _ordered_counts(
    counter: Counter[str],
    *,
    preferred_order: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    ordered: list[tuple[str, int]] = []
    for key in preferred_order:
        count = counter.get(key, 0)
        if count > 0:
            ordered.append((key, count))

    for key in sorted(counter):
        if key not in preferred_order and counter[key] > 0:
            ordered.append((key, counter[key]))
    return tuple(ordered)


def _window_orientation_counts(
    windows: tuple[WindowAnnotation, ...],
) -> tuple[tuple[str, int], ...]:
    return _ordered_counts(
        Counter(window.orientation for window in windows),
        preferred_order=("South", "East", "North", "West"),
    )


def _surface_type_counts_from_objects(
    objects: list[IdfObject],
) -> tuple[tuple[str, int], ...]:
    counter = Counter(
        obj.fields[1]
        for obj in objects
        if obj.class_name == "BuildingSurface:Detailed" and len(obj.fields) > 1
    )
    return _ordered_counts(
        counter,
        preferred_order=("Wall", "Floor", "Ceiling", "Roof"),
    )


def _roof_elevation_from_objects(objects: list[IdfObject]) -> float:
    elevations = [
        vertex[2]
        for obj in objects
        if obj.class_name == "BuildingSurface:Detailed"
        for vertex in _surface_vertices(obj)
    ]
    if not elevations:
        raise ValueError("No building surfaces were found in the IDF objects.")
    return round(max(elevations), 4)


def _representative_floor_elevation(
    surfaces: list[tuple[str, float, tuple[tuple[float, float], ...]]],
    geometry: FloorplanGeometry | None,
) -> float:
    if geometry is not None:
        return geometry.representative_floor_level().elevation

    occupied_levels = sorted(
        {
            elevation
            for zone_name, elevation, _ in surfaces
            if "PLENUM" not in zone_name.upper()
        }
    )
    if not occupied_levels:
        raise ValueError("No occupied floor elevations were found in the IDF surfaces.")
    return occupied_levels[len(occupied_levels) // 2]


def build_building_structure_annotations(idf_path: Path) -> BuildingStructureAnnotation:
    objects = load_idf(idf_path)
    surfaces = _floor_surfaces_from_objects(objects)

    occupied_elevations = tuple(
        sorted({elevation for zone_name, elevation, _ in surfaces if "PLENUM" not in zone_name.upper()})
    )
    plenum_elevations = tuple(
        sorted({elevation for zone_name, elevation, _ in surfaces if "PLENUM" in zone_name.upper()})
    )
    if not occupied_elevations:
        raise ValueError("No occupied floor elevations were found in the IDF surfaces.")

    windows = _window_annotations_from_objects(objects, occupied_elevations)
    roof_outline = _roof_outline_from_objects(objects)
    facades = _facade_annotations_from_objects(objects)
    roof_elevation = _roof_elevation_from_objects(objects)

    floors: list[StructureFloorAnnotation] = []
    for index, elevation in enumerate(occupied_elevations):
        occupied_zones = tuple(
            sorted(
                (
                    ZoneAnnotation(
                        zone_name=zone_name,
                        floor_elevation=elevation,
                        boundary=boundary,
                        anchor=_polygon_centroid(boundary),
                        zone_category=_zone_category(zone_name),
                    )
                    for zone_name, current_elevation, boundary in surfaces
                    if current_elevation == elevation and "PLENUM" not in zone_name.upper()
                ),
                key=lambda zone: zone.zone_name.upper(),
            )
        )
        plenum_elevation = plenum_elevations[index] if index < len(plenum_elevations) else None
        plenum_boundaries = tuple(
            boundary
            for zone_name, current_elevation, boundary in surfaces
            if current_elevation == plenum_elevation and "PLENUM" in zone_name.upper()
        )
        floor_title = _floor_title(tuple(zone.zone_name for zone in occupied_zones))
        floor_windows = tuple(window for window in windows if window.floor_elevation == elevation)
        floors.append(
            StructureFloorAnnotation(
                floor_elevation=elevation,
                floor_title=floor_title,
                occupied_zones=occupied_zones,
                plenum_boundaries=plenum_boundaries,
                plenum_elevation=plenum_elevation,
                windows=floor_windows,
            )
        )

    footprint_points = [
        point
        for floor in floors
        for zone in floor.occupied_zones
        for point in zone.boundary
    ]
    xs = [point[0] for point in footprint_points]
    ys = [point[1] for point in footprint_points]
    return BuildingStructureAnnotation(
        floors=tuple(floors),
        roof_outline=roof_outline,
        facades=facades,
        footprint_width=round(max(xs) - min(xs), 3),
        footprint_depth=round(max(ys) - min(ys), 3),
        roof_elevation=roof_elevation,
        window_orientation_counts=_window_orientation_counts(windows),
        surface_type_counts=_surface_type_counts_from_objects(objects),
        north_arrow_label="True North",
        north_arrow_vector=(0.0, 1.0),
    )


def build_floor_annotations(
    idf_path: Path,
    *,
    geometry: FloorplanGeometry | None = None,
    floor_elevation: float | None = None,
) -> FloorAnnotationSet:
    surfaces = _floor_surfaces(idf_path)
    target_elevation = (
        round(floor_elevation, 3)
        if floor_elevation is not None
        else _representative_floor_elevation(surfaces, geometry)
    )

    zone_annotations = tuple(
        sorted(
            (
                ZoneAnnotation(
                    zone_name=zone_name,
                    floor_elevation=elevation,
                    boundary=boundary,
                    anchor=_polygon_centroid(boundary),
                    zone_category=_zone_category(zone_name),
                )
                for zone_name, elevation, boundary in surfaces
                if elevation == target_elevation and "PLENUM" not in zone_name.upper()
            ),
            key=lambda zone: zone.zone_name.upper(),
        )
    )
    if not zone_annotations:
        raise ValueError(f"No zone annotations were found at elevation {target_elevation}.")

    zone_names = tuple(zone.zone_name for zone in zone_annotations)
    return FloorAnnotationSet(
        floor_elevation=target_elevation,
        zone_annotations=zone_annotations,
        north_arrow_label="True North",
        north_arrow_vector=(0.0, 1.0),
        floor_title=_floor_title(zone_names),
        legend_labels=_legend_labels(zone_annotations),
    )
