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


def make_thermostat_objects(zone_names: list[str]) -> list[IdfObject]:
    """Generate ZoneControl:Thermostat and supporting objects for all zones."""
    objects: list[IdfObject] = []

    objects.append(IdfObject("ScheduleTypeLimits", [
        "Control Type", "0", "4", "DISCRETE",
    ]))

    objects.append(IdfObject("Schedule:Compact", [
        "Htg-SetP-Sch", "Temperature",
        "Through: 12/31", "For: SummerDesignDay", "Until: 24:00", "21.1",
        "For: WinterDesignDay", "Until: 24:00", "21.1",
        "For: WeekDays", "Until: 7:00", "21.1", "Until: 18:00", "21.1", "Until: 24:00", "21.1",
        "For: WeekEnds Holiday", "Until: 7:00", "21.1", "Until: 13:00", "21.1", "Until: 24:00", "21.1",
        "For: AllOtherDays", "Until: 7:00", "21.1", "Until: 18:00", "21.1", "Until: 24:00", "21.1",
    ]))

    objects.append(IdfObject("Schedule:Compact", [
        "Clg-SetP-Sch", "Temperature",
        "Through: 12/31", "For: SummerDesignDay", "Until: 24:00", "23.9",
        "For: WinterDesignDay", "Until: 24:00", "23.9",
        "For: WeekDays", "Until: 7:00", "23.9", "Until: 18:00", "23.9", "Until: 24:00", "23.9",
        "For: WeekEnds Holiday", "Until: 7:00", "23.9", "Until: 13:00", "23.9", "Until: 24:00", "23.9",
        "For: AllOtherDays", "Until: 7:00", "23.9", "Until: 18:00", "23.9", "Until: 24:00", "23.9",
    ]))

    objects.append(IdfObject("Schedule:Compact", [
        "Zone Control Type Sched", "Control Type",
        "Through: 12/31", "For: SummerDesignDay", "Until: 24:00", "4",
        "For: WinterDesignDay", "Until: 24:00", "4",
        "For: AllOtherDays", "Until: 24:00", "4",
    ]))

    objects.append(IdfObject("ThermostatSetpoint:DualSetpoint", [
        "DualSetPoint", "Htg-SetP-Sch", "Clg-SetP-Sch",
    ]))

    for zone_name in zone_names:
        objects.append(IdfObject("ZoneControl:Thermostat", [
            f"{zone_name} Control",
            zone_name,
            "Zone Control Type Sched",
            "ThermostatSetpoint:DualSetpoint",
            "DualSetPoint",
        ]))

    return objects
