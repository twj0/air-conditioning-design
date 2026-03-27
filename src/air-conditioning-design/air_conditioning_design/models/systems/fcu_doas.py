# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-FCU-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.config.cities import get_city_config
from air_conditioning_design.config.paths import (
    FCU_DOAS_DONOR_IDF,
    NEUTRAL_MODEL_PATH,
    REFERENCE_MEDIUM_OFFICE_IDF,
    build_case_id,
    city_model_path,
    ensure_directories,
    system_model_path,
)
from air_conditioning_design.idf.io import (
    IdfObject,
    filter_objects,
    load_idf,
    replace_object,
    write_idf,
)
from air_conditioning_design.models.base import neutralize_reference_model
from air_conditioning_design.models.common import (
    build_zone_maps,
    extract_design_objects,
    load_city_manifest,
)

DYNAMIC_DONOR_OBJECTS = {
    ("AirLoopHVAC:ZoneSplitter", "DOAS Zone Splitter"),
    ("AirLoopHVAC:ZoneMixer", "DOAS Zone Mixer"),
    ("BranchList", "Hot Water Loop HW Demand Side Branches"),
    ("BranchList", "Chilled Water Loop ChW Demand Side Branches"),
    ("Connector:Splitter", "Hot Water Loop HW Demand Splitter"),
    ("Connector:Splitter", "Chilled Water Loop ChW Demand Splitter"),
    ("Connector:Mixer", "Hot Water Loop HW Demand Mixer"),
    ("Connector:Mixer", "Chilled Water Loop ChW Demand Mixer"),
    ("ConnectorList", "Hot Water Loop HW Demand Side Connectors"),
    ("ConnectorList", "Chilled Water Loop ChW Demand Side Connectors"),
}

SUPPORT_CLASS_NAMES = {
    "SCHEDULETYPELIMITS",
    "AVAILABILITYMANAGER:SCHEDULED",
    "AVAILABILITYMANAGERASSIGNMENTLIST",
    "FAN:VARIABLEVOLUME",
    "HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT",
    "CONTROLLER:OUTDOORAIR",
    "AIRLOOPHVAC:CONTROLLERLIST",
    "AIRLOOPHVAC",
    "AIRLOOPHVAC:OUTDOORAIRSYSTEM:EQUIPMENTLIST",
    "AIRLOOPHVAC:OUTDOORAIRSYSTEM",
    "AIRLOOPHVAC:SUPPLYPATH",
    "AIRLOOPHVAC:RETURNPATH",
    "OUTDOORAIR:MIXER",
    "OUTDOORAIR:NODE",
    "OUTDOORAIR:NODELIST",
    "COIL:COOLING:WATER",
    "COIL:HEATING:WATER",
    "CONTROLLER:WATERCOIL",
    "SETPOINTMANAGER:MIXEDAIR",
    "SETPOINTMANAGER:OUTDOORAIRRESET",
    "SETPOINTMANAGER:SCHEDULED",
    "SIZING:SYSTEM",
    "PLANTEQUIPMENTLIST",
    "PLANTEQUIPMENTOPERATION:COOLINGLOAD",
    "PLANTEQUIPMENTOPERATION:HEATINGLOAD",
    "PLANTEQUIPMENTOPERATIONSCHEMES",
    "PLANTLOOP",
    "SIZING:PLANT",
    "PUMP:CONSTANTSPEED",
    "PUMP:VARIABLESPEED",
    "BOILER:HOTWATER",
    "CHILLER:ELECTRIC:EIR",
    "COOLINGTOWER:SINGLESPEED",
    "CONDENSEREQUIPMENTLIST",
    "CONDENSEREQUIPMENTOPERATIONSCHEMES",
    "CONDENSERLOOP",
    "PIPE:ADIABATIC",
    "BRANCH",
    "BRANCHLIST",
    "CONNECTOR:SPLITTER",
    "CONNECTOR:MIXER",
    "CONNECTORLIST",
}


def _clone_object(obj: IdfObject) -> IdfObject:
    return IdfObject(obj.class_name, obj.fields.copy())


def _extend_unique_objects(
    base_objects: list[IdfObject], additions: list[IdfObject]
) -> list[IdfObject]:
    named_keys = {(obj.class_name, obj.name) for obj in base_objects if obj.name}
    anonymous_keys = {
        (obj.class_name, tuple(obj.fields)) for obj in base_objects if not obj.name
    }

    merged = base_objects.copy()
    for obj in additions:
        if obj.name:
            key = (obj.class_name, obj.name)
            if key in named_keys:
                continue
            named_keys.add(key)
            merged.append(obj)
            continue

        key = (obj.class_name, tuple(obj.fields))
        if key in anonymous_keys:
            continue
        anonymous_keys.add(key)
        merged.append(obj)

    return merged


def _load_donor_objects() -> list[IdfObject]:
    return load_idf(FCU_DOAS_DONOR_IDF)


def _is_zone_specific_donor_object(obj: IdfObject) -> bool:
    if not obj.name or not obj.name.startswith("SPACE"):
        return False
    return obj.class_name in {
        "ZoneHVAC:FourPipeFanCoil",
        "AirTerminal:SingleDuct:Mixer",
        "ZoneHVAC:AirDistributionUnit",
        "ZoneHVAC:EquipmentConnections",
        "ZoneHVAC:EquipmentList",
        "Fan:ConstantVolume",
        "Coil:Cooling:Water",
        "Coil:Heating:Water",
        "NodeList",
        "Branch",
    }


def _select_donor_support_objects(donor_objects: list[IdfObject]) -> list[IdfObject]:
    selected: list[IdfObject] = []

    for obj in donor_objects:
        class_upper = obj.class_name.upper()
        if class_upper.startswith("SCHEDULE:") or class_upper.startswith("CURVE:"):
            selected.append(_clone_object(obj))
            continue
        if _is_zone_specific_donor_object(obj):
            continue
        if (obj.class_name, obj.name) in DYNAMIC_DONOR_OBJECTS:
            continue
        if class_upper in SUPPORT_CLASS_NAMES:
            selected.append(_clone_object(obj))

    return selected


def _retune_support_objects(objects: list[IdfObject]) -> list[IdfObject]:
    tuned: list[IdfObject] = []
    for obj in objects:
        clone = _clone_object(obj)
        if (
            clone.class_name == "Fan:VariableVolume"
            and clone.name == "DOAS Supply Fan"
            and len(clone.fields) >= 17
        ):
            clone = IdfObject(
                "Fan:ConstantVolume",
                [
                    "DOAS Supply Fan",
                    clone.fields[1],
                    clone.fields[2],
                    clone.fields[3],
                    clone.fields[4],
                    clone.fields[8],
                    clone.fields[9],
                    clone.fields[15],
                    clone.fields[16],
                ],
            )
        elif clone.class_name == "Branch" and clone.name == "DOAS Main Branch":
            clone.fields[14] = "Fan:ConstantVolume"
        elif (
            clone.class_name == "HeatExchanger:AirToAir:SensibleAndLatent"
            and clone.name == "DOAS Heat Recovery"
        ):
            clone.fields[1] = "FanAvailSched"
        elif (
            clone.class_name == "SetpointManager:OutdoorAirReset"
            and clone.name == "Chilled Water Loop ChW Temp Manager"
        ):
            clone.fields[2] = "7.2"
        tuned.append(clone)
    return tuned


def _surface_polygon_area(surface: IdfObject) -> float:
    vertex_count = int(float(surface.fields[10]))
    raw_coords = [float(value) for value in surface.fields[11 : 11 + vertex_count * 3]]
    points = [
        (raw_coords[index], raw_coords[index + 1])
        for index in range(0, len(raw_coords), 3)
    ]

    area = 0.0
    for index, (x_1, y_1) in enumerate(points):
        x_2, y_2 = points[(index + 1) % len(points)]
        area += (x_1 * y_2) - (x_2 * y_1)
    return abs(area) * 0.5


def _retune_outdoor_air_objects(
    objects: list[IdfObject], outdoor_air_map: dict[str, str]
) -> list[IdfObject]:
    zone_floor_areas: dict[str, float] = {}
    zone_area_per_person: dict[str, float] = {}
    dsoa_by_name = {
        obj.name: obj
        for obj in objects
        if obj.class_name == "DesignSpecification:OutdoorAir" and obj.name
    }

    for obj in objects:
        if obj.class_name == "BuildingSurface:Detailed" and obj.fields[1] == "Floor":
            zone_name = obj.fields[3]
            if zone_name in outdoor_air_map:
                zone_floor_areas[zone_name] = zone_floor_areas.get(
                    zone_name, 0.0
                ) + _surface_polygon_area(obj)
            continue
        if obj.class_name == "People" and len(obj.fields) > 6 and obj.fields[3] == "Area/Person":
            zone_area_per_person[obj.fields[1]] = float(obj.fields[6])

    replacements: dict[str, IdfObject] = {}
    for zone_name, dsoa_name in outdoor_air_map.items():
        area_per_person = zone_area_per_person.get(zone_name)
        floor_area = zone_floor_areas.get(zone_name)
        source_dsoa = dsoa_by_name.get(dsoa_name)
        if not area_per_person or floor_area is None or source_dsoa is None:
            continue
        if source_dsoa.fields[1] != "Flow/Person":
            continue

        design_people = floor_area / area_per_person
        flow_per_person = float(source_dsoa.fields[2])
        design_flow_zone = design_people * flow_per_person
        replacements[dsoa_name] = IdfObject(
            "DesignSpecification:OutdoorAir",
            [
                dsoa_name,
                "Flow/Zone",
                "",
                "",
                f"{design_flow_zone:.6f}",
            ],
        )

    if not replacements:
        return objects

    retuned: list[IdfObject] = []
    for obj in objects:
        if obj.class_name == "DesignSpecification:OutdoorAir" and obj.name in replacements:
            retuned.append(replacements[obj.name])
            continue
        retuned.append(obj)
    return retuned


def _build_fcu_zone_objects(
    zone_name: str, zone_air_node: str, return_air_node: str
) -> list[IdfObject]:
    equipment_name = f"{zone_name} Equipment"
    inlet_node_list = f"{zone_name} Inlets"
    supply_inlet = f"{zone_name} Supply Inlet"
    secondary_inlet = f"{zone_name} Air Terminal Mixer Secondary Inlet"
    primary_inlet = f"{zone_name} Air Terminal Mixer Primary Inlet"
    fan_coil_name = f"{zone_name} Fan Coil"
    fan_coil_inlet = f"{zone_name} Fan Coil Inlet"
    air_terminal_name = f"{zone_name} DOAS Air Terminal"
    adu_name = f"{zone_name} DOAS ATU"
    fan_name = f"{zone_name} Supply Fan"
    fan_outlet = f"{zone_name} Zone Unit Fan Outlet"
    cooling_coil_name = f"{zone_name} Cooling Coil"
    cooling_water_inlet = f"{zone_name} Cooling Coil ChW Inlet"
    cooling_water_outlet = f"{zone_name} Cooling Coil ChW Outlet"
    cooling_air_outlet = f"{zone_name} Cooling Coil Outlet"
    heating_coil_name = f"{zone_name} Heating Coil"
    heating_water_inlet = f"{zone_name} Heating Coil HW Inlet"
    heating_water_outlet = f"{zone_name} Heating Coil HW Outlet"
    cooling_branch = f"{zone_name} Cooling Coil ChW Branch"
    heating_branch = f"{zone_name} Heating Coil HW Branch"

    return [
        IdfObject("NodeList", [inlet_node_list, supply_inlet]),
        IdfObject(
            "ZoneHVAC:EquipmentConnections",
            [
                zone_name,
                equipment_name,
                inlet_node_list,
                secondary_inlet,
                zone_air_node,
                return_air_node,
            ],
        ),
        IdfObject(
            "ZoneHVAC:EquipmentList",
            [
                equipment_name,
                "SequentialLoad",
                "ZoneHVAC:AirDistributionUnit",
                adu_name,
                "2",
                "2",
                "",
                "",
                "ZoneHVAC:FourPipeFanCoil",
                fan_coil_name,
                "1",
                "1",
                "",
                "",
            ],
        ),
        IdfObject(
            "AirTerminal:SingleDuct:Mixer",
            [
                air_terminal_name,
                "ZoneHVAC:FourPipeFanCoil",
                fan_coil_name,
                fan_coil_inlet,
                primary_inlet,
                secondary_inlet,
                "InletSide",
            ],
        ),
        IdfObject(
            "ZoneHVAC:AirDistributionUnit",
            [adu_name, fan_coil_inlet, "AirTerminal:SingleDuct:Mixer", air_terminal_name],
        ),
        IdfObject(
            "ZoneHVAC:FourPipeFanCoil",
            [
                fan_coil_name,
                "FanAvailSched",
                "ConstantFanVariableFlow",
                "autosize",
                "",
                "",
                "0",
                "",
                fan_coil_inlet,
                supply_inlet,
                "",
                "",
                "Fan:ConstantVolume",
                fan_name,
                "Coil:Cooling:Water",
                cooling_coil_name,
                "autosize",
                "0",
                "0.001",
                "Coil:Heating:Water",
                heating_coil_name,
                "autosize",
                "0",
                "0.001",
            ],
        ),
        IdfObject(
            "Fan:ConstantVolume",
            [
                fan_name,
                "FanAvailSched",
                "0.7",
                "75",
                "autosize",
                "0.9",
                "1",
                fan_coil_inlet,
                fan_outlet,
            ],
        ),
        IdfObject(
            "Coil:Cooling:Water",
            [
                cooling_coil_name,
                "HVACTemplate-Always 1",
                "autosize",
                "autosize",
                "autosize",
                "autosize",
                "autosize",
                "autosize",
                "autosize",
                cooling_water_inlet,
                cooling_water_outlet,
                fan_outlet,
                cooling_air_outlet,
                "DetailedAnalysis",
                "CrossFlow",
            ],
        ),
        IdfObject(
            "Coil:Heating:Water",
            [
                heating_coil_name,
                "HVACTemplate-Always 1",
                "autosize",
                "autosize",
                heating_water_inlet,
                heating_water_outlet,
                cooling_air_outlet,
                supply_inlet,
                "UFactorTimesAreaAndDesignWaterFlowRate",
                "autosize",
                "82.2",
                "16.6",
                "71.1",
                "32.2",
                "1.0",
            ],
        ),
        IdfObject(
            "Branch",
            [
                cooling_branch,
                "",
                "Coil:Cooling:Water",
                cooling_coil_name,
                cooling_water_inlet,
                cooling_water_outlet,
            ],
        ),
        IdfObject(
            "Branch",
            [
                heating_branch,
                "",
                "Coil:Heating:Water",
                heating_coil_name,
                heating_water_inlet,
                heating_water_outlet,
            ],
        ),
    ]


def _build_zone_splitter(zone_names: list[str]) -> IdfObject:
    fields = ["DOAS Zone Splitter", "DOAS Supply Path Inlet"] + [
        f"{zone_name} Air Terminal Mixer Primary Inlet" for zone_name in zone_names
    ]
    return IdfObject("AirLoopHVAC:ZoneSplitter", fields)


def _build_zone_mixer(
    zone_names: list[str], zone_node_map: dict[str, tuple[str, str]]
) -> IdfObject:
    fields = ["DOAS Zone Mixer", "DOAS Return Air Outlet"] + [
        zone_node_map[zone_name][1] for zone_name in zone_names
    ]
    return IdfObject("AirLoopHVAC:ZoneMixer", fields)


def _build_chilled_water_demand_objects(zone_names: list[str]) -> list[IdfObject]:
    zone_branches = [f"{zone_name} Cooling Coil ChW Branch" for zone_name in zone_names]
    return [
        IdfObject(
            "BranchList",
            [
                "Chilled Water Loop ChW Demand Side Branches",
                "Chilled Water Loop ChW Demand Inlet Branch",
                *zone_branches,
                "DOAS Cooling Coil ChW Branch",
                "Chilled Water Loop ChW Demand Bypass Branch",
                "Chilled Water Loop ChW Demand Outlet Branch",
            ],
        ),
        IdfObject(
            "Connector:Splitter",
            [
                "Chilled Water Loop ChW Demand Splitter",
                "Chilled Water Loop ChW Demand Inlet Branch",
                *zone_branches,
                "DOAS Cooling Coil ChW Branch",
                "Chilled Water Loop ChW Demand Bypass Branch",
            ],
        ),
        IdfObject(
            "Connector:Mixer",
            [
                "Chilled Water Loop ChW Demand Mixer",
                "Chilled Water Loop ChW Demand Outlet Branch",
                *zone_branches,
                "DOAS Cooling Coil ChW Branch",
                "Chilled Water Loop ChW Demand Bypass Branch",
            ],
        ),
        IdfObject(
            "ConnectorList",
            [
                "Chilled Water Loop ChW Demand Side Connectors",
                "Connector:Splitter",
                "Chilled Water Loop ChW Demand Splitter",
                "Connector:Mixer",
                "Chilled Water Loop ChW Demand Mixer",
            ],
        ),
    ]


def _build_hot_water_demand_objects(zone_names: list[str]) -> list[IdfObject]:
    zone_branches = [f"{zone_name} Heating Coil HW Branch" for zone_name in zone_names]
    return [
        IdfObject(
            "BranchList",
            [
                "Hot Water Loop HW Demand Side Branches",
                "Hot Water Loop HW Demand Inlet Branch",
                *zone_branches,
                "DOAS Heating Coil HW Branch",
                "Hot Water Loop HW Demand Bypass Branch",
                "Hot Water Loop HW Demand Outlet Branch",
            ],
        ),
        IdfObject(
            "Connector:Splitter",
            [
                "Hot Water Loop HW Demand Splitter",
                "Hot Water Loop HW Demand Inlet Branch",
                *zone_branches,
                "DOAS Heating Coil HW Branch",
                "Hot Water Loop HW Demand Bypass Branch",
            ],
        ),
        IdfObject(
            "Connector:Mixer",
            [
                "Hot Water Loop HW Demand Mixer",
                "Hot Water Loop HW Demand Outlet Branch",
                *zone_branches,
                "DOAS Heating Coil HW Branch",
                "Hot Water Loop HW Demand Bypass Branch",
            ],
        ),
        IdfObject(
            "ConnectorList",
            [
                "Hot Water Loop HW Demand Side Connectors",
                "Connector:Splitter",
                "Hot Water Loop HW Demand Splitter",
                "Connector:Mixer",
                "Hot Water Loop HW Demand Mixer",
            ],
        ),
    ]


def _make_fcu_output_objects() -> list[IdfObject]:
    return [
        IdfObject("OutputControl:Table:Style", ["CommaAndHTML", "JtoKWH"]),
        IdfObject("Output:Table:SummaryReports", ["AllSummary"]),
        IdfObject("Output:Meter", ["Electricity:HVAC", "Monthly"]),
        IdfObject("Output:Meter", ["Fans:Electricity", "Monthly"]),
        IdfObject("Output:Meter", ["Cooling:Electricity", "Monthly"]),
        IdfObject("Output:Meter", ["Heating:Electricity", "Monthly"]),
        IdfObject(
            "Output:Variable",
            ["DOAS Outdoor Air Inlet", "System Node Mass Flow Rate", "Hourly"],
        ),
        IdfObject(
            "Output:Variable",
            ["DOAS Supply Fan Outlet", "System Node Mass Flow Rate", "Hourly"],
        ),
        IdfObject(
            "Output:Variable",
            [
                "DOAS Heat Recovery",
                "Heat Exchanger Supply Air Bypass Mass Flow Rate",
                "Hourly",
            ],
        ),
        IdfObject(
            "Output:Variable",
            [
                "DOAS Heat Recovery",
                "Heat Exchanger Exhaust Air Bypass Mass Flow Rate",
                "Hourly",
            ],
        ),
    ]


def build_fcu_doas_case(city_id: str, output_root: Path | None = None) -> Path:
    ensure_directories()
    city = get_city_config(city_id)
    manifest = load_city_manifest(city_id)

    if not NEUTRAL_MODEL_PATH.exists():
        neutralize_reference_model(REFERENCE_MEDIUM_OFFICE_IDF, NEUTRAL_MODEL_PATH)

    neutral_objects = load_idf(NEUTRAL_MODEL_PATH)
    donor_objects = _load_donor_objects()
    zone_node_map, outdoor_air_map = build_zone_maps(neutral_objects)
    zone_names = sorted(zone_node_map)

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
            "AvailabilityManagerAssignmentList",
            "NodeList",
            "OutdoorAir:NodeList",
        },
        remove_prefixes=(
            "Output:Variable",
            "ZoneHVAC:IdealLoadsAirSystem",
            "AirLoopHVAC",
            "AirTerminal:",
            "Sizing:System",
            "Sizing:Plant",
            "PlantLoop",
            "Condenser",
            "CoolingTower",
            "Boiler:",
            "Chiller:",
            "Branch",
            "Connector",
            "Pipe:",
            "Pump:",
            "PlantEquipment",
            "SetpointManager:",
            "AvailabilityManager:",
            "OutdoorAir:",
            "Controller:OutdoorAir",
            "Controller:WaterCoil",
            "Coil:",
            "CoilSystem:",
            "Fan:",
            "WaterHeater:",
            "WaterUse:",
        ),
        remove_name_prefixes=("VAV_",),
    )
    filtered = _retune_outdoor_air_objects(filtered, outdoor_air_map)

    filtered = replace_object(
        filtered,
        "SimulationControl",
        IdfObject(
            "SimulationControl",
            ["YES", "YES", "YES", "YES", "YES", "No", "1"],
        ),
    )
    filtered = replace_object(
        filtered,
        "Building",
        IdfObject(
            "Building",
            [
                f"{city.display_name} Medium Office FCU DOAS Pilot",
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

    design_objects = extract_design_objects(Path(manifest["ddy_path"]))
    support_objects = _retune_support_objects(_select_donor_support_objects(donor_objects))

    generated_zone_objects: list[IdfObject] = []
    for zone_name in zone_names:
        zone_air_node, return_air_node = zone_node_map[zone_name]
        generated_zone_objects.extend(
            _build_fcu_zone_objects(zone_name, zone_air_node, return_air_node)
        )

    generated_objects = [
        _build_zone_splitter(zone_names),
        _build_zone_mixer(zone_names, zone_node_map),
        *_build_chilled_water_demand_objects(zone_names),
        *_build_hot_water_demand_objects(zone_names),
        *_make_fcu_output_objects(),
    ]
    case_id = build_case_id(city_id, "fcu_doas")

    city_variant_path = (
        (output_root / f"medium_office_{city_id}.idf")
        if output_root
        else city_model_path(city_id)
    )
    case_path = (
        (output_root / f"{case_id}.idf") if output_root else system_model_path(case_id)
    )

    city_objects = _extend_unique_objects(filtered + design_objects, [])
    write_idf(city_variant_path, city_objects)

    case_objects = _extend_unique_objects(
        city_objects,
        support_objects + generated_zone_objects + generated_objects,
    )
    write_idf(case_path, case_objects)
    return case_path
