# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

import json
from pathlib import Path

from air_conditioning_design.config.paths import (
    NEUTRAL_MODEL_PATH,
    REFERENCE_MEDIUM_OFFICE_IDF,
    TIANJIN_CITY_MODEL_PATH,
    TIANJIN_IDEAL_LOADS_PATH,
    TIANJIN_MANIFEST,
    ensure_directories,
)
from air_conditioning_design.idf.io import (
    IdfObject,
    filter_objects,
    load_idf,
    replace_object,
    write_idf,
)
from air_conditioning_design.models.base import neutralize_reference_model
from air_conditioning_design.models.tianjin_common import (
    build_zone_maps,
    extract_tianjin_design_objects,
    load_tianjin_manifest,
)
from air_conditioning_design.weather.tianjin import write_tianjin_weather_manifest


def _load_manifest() -> dict[str, str]:
    if not TIANJIN_MANIFEST.exists():
        write_tianjin_weather_manifest()
    return load_tianjin_manifest()


def _make_equipment_objects(
    zone_node_map: dict[str, tuple[str, str]], outdoor_air_map: dict[str, str]
) -> list[IdfObject]:
    objects: list[IdfObject] = []

    for zone_name, (zone_air_node, return_air_node) in zone_node_map.items():
        supply_node = f"{zone_name} Ideal Loads Supply Inlet Node"
        inlet_node_list = f"{zone_name} Ideal Loads Inlet Nodes"
        ideal_loads_name = f"{zone_name} Ideal Loads"

        objects.append(IdfObject("NodeList", [inlet_node_list, supply_node]))
        objects.append(
            IdfObject(
                "ZoneHVAC:EquipmentConnections",
                [
                    zone_name,
                    f"{zone_name} Equipment",
                    inlet_node_list,
                    "",
                    zone_air_node,
                    return_air_node,
                ],
            )
        )
        objects.append(
            IdfObject(
                "ZoneHVAC:EquipmentList",
                [
                    f"{zone_name} Equipment",
                    "SequentialLoad",
                    "ZoneHVAC:IdealLoadsAirSystem",
                    ideal_loads_name,
                    "1",
                    "1",
                    "",
                    "",
                ],
            )
        )
        objects.append(
            IdfObject(
                "ZoneHVAC:IdealLoadsAirSystem",
                [
                    ideal_loads_name,
                    "",
                    supply_node,
                    "",
                    "",
                    "50",
                    "13",
                    "0.015",
                    "0.009",
                    "NoLimit",
                    "autosize",
                    "",
                    "NoLimit",
                    "autosize",
                    "",
                    "",
                    "",
                    "ConstantSupplyHumidityRatio",
                    "",
                    "ConstantSupplyHumidityRatio",
                    outdoor_air_map.get(zone_name, ""),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            )
        )

    return objects


def _make_output_objects() -> list[IdfObject]:
    return [
        IdfObject("OutputControl:Table:Style", ["CommaAndHTML", "JtoKWH"]),
        IdfObject("Output:Table:SummaryReports", ["AllSummary"]),
        IdfObject(
            "Output:Variable",
            ["*", "Zone Ideal Loads Supply Air Sensible Cooling Rate", "Hourly"],
        ),
        IdfObject(
            "Output:Variable",
            ["*", "Zone Ideal Loads Supply Air Sensible Heating Rate", "Hourly"],
        ),
    ]


def build_tianjin_ideal_loads_case(output_root: Path | None = None) -> Path:
    ensure_directories()
    manifest = _load_manifest()

    if not NEUTRAL_MODEL_PATH.exists():
        neutralize_reference_model(REFERENCE_MEDIUM_OFFICE_IDF, NEUTRAL_MODEL_PATH)

    neutral_objects = load_idf(NEUTRAL_MODEL_PATH)
    zone_node_map, outdoor_air_map = build_zone_maps(neutral_objects)

    filtered = filter_objects(
        neutral_objects,
        remove_classes={
            "ZoneHVAC:EquipmentConnections",
            "ZoneHVAC:EquipmentList",
            "ZoneHVAC:AirDistributionUnit",
            "OutputControl:Table:Style",
            "Output:Table:SummaryReports",
            "Output:Table:Monthly",
            "Output:Table:TimeBins",
            "Output:Meter",
        },
        remove_prefixes=(
            "Output:Variable",
            "ZoneHVAC:IdealLoadsAirSystem",
            "AirLoopHVAC",
            "AirTerminal:",
        ),
        remove_name_prefixes=("VAV_",),
    )

    filtered = replace_object(
        filtered,
        "SimulationControl",
        IdfObject(
            "SimulationControl",
            ["YES", "NO", "NO", "YES", "YES", "No", "1"],
        ),
    )
    filtered = replace_object(
        filtered,
        "Building",
        IdfObject(
            "Building",
            [
                "Tianjin Medium Office Ideal Loads Pilot",
                "0.0000",
                "City",
                "0.0400",
                "0.2000",
                "FullInteriorAndExterior",
                "25",
                "6",
            ],
        ),
    )

    design_objects = extract_tianjin_design_objects(Path(manifest["ddy_path"]))
    generated_objects = filtered + design_objects + _make_equipment_objects(
        zone_node_map, outdoor_air_map
    ) + _make_output_objects()

    city_variant_path = (
        (output_root / "medium_office_tianjin.idf")
        if output_root
        else TIANJIN_CITY_MODEL_PATH
    )
    case_path = (
        (output_root / "tianjin__ideal_loads.idf")
        if output_root
        else TIANJIN_IDEAL_LOADS_PATH
    )

    write_idf(city_variant_path, filtered + design_objects)
    write_idf(case_path, generated_objects)
    return case_path
