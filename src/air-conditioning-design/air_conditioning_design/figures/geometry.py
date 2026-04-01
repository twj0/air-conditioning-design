# Ref: docs/spec/task.md (Task-ID: IMPL-IDF-FLOORPLAN-001)
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import ezdxf

_DEFAULT_LAYER = "1"
_PLENUM_TOKEN = "PLENUM"


@dataclass(frozen=True, slots=True)
class PlanPolygon:
    layer: str
    elevation: float
    points: tuple[tuple[float, float], ...]

    @property
    def is_plenum(self) -> bool:
        return _PLENUM_TOKEN in self.layer.upper()

    @property
    def is_default_layer(self) -> bool:
        return self.layer == _DEFAULT_LAYER


@dataclass(frozen=True, slots=True)
class PlanText:
    layer: str
    text: str
    position: tuple[float, float]


@dataclass(frozen=True, slots=True)
class FloorLevelGeometry:
    elevation: float
    polygons: tuple[PlanPolygon, ...]

    @property
    def layers(self) -> tuple[str, ...]:
        return tuple(polygon.layer for polygon in self.polygons)


@dataclass(frozen=True, slots=True)
class FloorplanGeometry:
    polygons: tuple[PlanPolygon, ...]
    texts: tuple[PlanText, ...]

    @property
    def horizontal_elevations(self) -> tuple[float, ...]:
        return tuple(sorted({polygon.elevation for polygon in self.polygons}))

    @property
    def occupied_zone_polygons(self) -> tuple[PlanPolygon, ...]:
        return tuple(
            polygon
            for polygon in self.polygons
            if not polygon.is_plenum and not polygon.is_default_layer
        )

    def occupied_floor_levels(self) -> tuple[FloorLevelGeometry, ...]:
        floor_elevations_by_layer: dict[str, float] = {}
        for polygon in self.occupied_zone_polygons:
            current = floor_elevations_by_layer.get(polygon.layer)
            if current is None or polygon.elevation < current:
                floor_elevations_by_layer[polygon.layer] = polygon.elevation

        polygons_by_elevation: dict[float, list[PlanPolygon]] = defaultdict(list)
        for polygon in self.occupied_zone_polygons:
            if polygon.elevation == floor_elevations_by_layer[polygon.layer]:
                polygons_by_elevation[polygon.elevation].append(polygon)

        return tuple(
            FloorLevelGeometry(
                elevation=elevation,
                polygons=tuple(
                    sorted(polygons_by_elevation[elevation], key=lambda polygon: polygon.layer)
                ),
            )
            for elevation in sorted(polygons_by_elevation)
        )

    def representative_floor_level(self) -> FloorLevelGeometry:
        levels = self.occupied_floor_levels()
        if not levels:
            raise ValueError("No occupied floor levels were found in the DXF geometry.")
        return levels[len(levels) // 2]


def _face_vertices(entity) -> tuple[tuple[float, float, float], ...]:  # type: ignore[no-untyped-def]
    vertices = []
    for field_name in ("vtx0", "vtx1", "vtx2", "vtx3"):
        vertex = getattr(entity.dxf, field_name)
        point = (round(vertex.x, 6), round(vertex.y, 6), round(vertex.z, 6))
        if point not in vertices:
            vertices.append(point)
    return tuple(vertices)


def _horizontal_polygon_from_face(entity) -> PlanPolygon | None:  # type: ignore[no-untyped-def]
    vertices = _face_vertices(entity)
    elevations = {vertex[2] for vertex in vertices}
    if len(elevations) != 1:
        return None

    return PlanPolygon(
        layer=entity.dxf.layer,
        elevation=round(next(iter(elevations)), 3),
        points=tuple((x, y) for x, y, _ in vertices),
    )


def load_floorplan_geometry(dxf_path: Path) -> FloorplanGeometry:
    doc = ezdxf.readfile(dxf_path)
    modelspace = doc.modelspace()

    polygons: list[PlanPolygon] = []
    texts: list[PlanText] = []

    for entity in modelspace:
        entity_type = entity.dxftype()
        if entity_type == "3DFACE":
            polygon = _horizontal_polygon_from_face(entity)
            if polygon is not None:
                polygons.append(polygon)
        elif entity_type == "TEXT":
            texts.append(
                PlanText(
                    layer=entity.dxf.layer,
                    text=entity.dxf.text.strip(),
                    position=(
                        round(entity.dxf.insert.x, 6),
                        round(entity.dxf.insert.y, 6),
                    ),
                )
            )

    return FloorplanGeometry(
        polygons=tuple(polygons),
        texts=tuple(texts),
    )
