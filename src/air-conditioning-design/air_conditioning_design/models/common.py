# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.idf.io import IdfObject, find_objects, parse_idf_objects
from air_conditioning_design.weather.catalog import load_weather_manifest


def load_city_manifest(city_id: str) -> dict[str, str]:
    return load_weather_manifest(city_id)


def extract_design_objects(ddy_path: Path) -> list[IdfObject]:
    ddy_text = ddy_path.read_text(encoding="utf-8", errors="ignore")
    objects = parse_idf_objects(ddy_text)
    return [
        obj
        for obj in objects
        if obj.class_name == "Site:Location" or obj.class_name.startswith("SizingPeriod:")
    ]


def build_zone_maps(
    objects: list[IdfObject],
) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    zone_node_map: dict[str, tuple[str, str]] = {}
    for obj in find_objects(objects, "ZoneHVAC:EquipmentConnections"):
        if len(obj.fields) < 6:
            continue
        zone_node_map[obj.fields[0]] = (obj.fields[4], obj.fields[5])

    outdoor_air_map: dict[str, str] = {}
    for obj in find_objects(objects, "Sizing:Zone"):
        if len(obj.fields) < 10:
            continue
        outdoor_air_map[obj.fields[0]] = obj.fields[9]

    return zone_node_map, outdoor_air_map


def conditioned_zone_names(objects: list[IdfObject]) -> list[str]:
    zone_node_map, _ = build_zone_maps(objects)
    return sorted(zone_node_map.keys())
