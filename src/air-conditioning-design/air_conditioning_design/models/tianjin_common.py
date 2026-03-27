# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from __future__ import annotations

import json
from pathlib import Path

from air_conditioning_design.config.paths import TIANJIN_MANIFEST
from air_conditioning_design.idf.io import IdfObject, find_objects, parse_idf_objects
from air_conditioning_design.weather.tianjin import write_tianjin_weather_manifest


def load_tianjin_manifest() -> dict[str, str]:
    if not TIANJIN_MANIFEST.exists():
        write_tianjin_weather_manifest()
    return json.loads(TIANJIN_MANIFEST.read_text(encoding="utf-8"))


def extract_tianjin_design_objects(ddy_path: Path) -> list[IdfObject]:
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
