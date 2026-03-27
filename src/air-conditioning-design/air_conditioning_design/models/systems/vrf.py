# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-VRF-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.config.cities import get_city_config
from air_conditioning_design.config.paths import (
    NEUTRAL_MODEL_PATH,
    REFERENCE_MEDIUM_OFFICE_IDF,
    VRF_DOAS_DONOR_IDF,
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

DONOR_SCHEDULE_NAMES = {
    "VRFCondAvailSched",
    "VRFFanSchedule",
    "VRFAvailSched",
    "FanAvailSched",
}

DONOR_CURVE_NAMES = {
    "VRFCoolCapFT",
    "VRFCoolCapFTBoundary",
    "VRFCoolCapFTHi",
    "VRFCoolEIRFT",
    "VRFCoolEIRFTBoundary",
    "VRFCoolEIRFTHi",
    "CoolingEIRLowPLR",
    "CoolingEIRHiPLR",
    "CoolingCombRatio",
    "VRFCPLFFPLR",
    "VRFHeatCapFT",
    "VRFHeatCapFTBoundary",
    "VRFHeatCapFTHi",
    "VRFHeatEIRFT",
    "VRFHeatEIRFTBoundary",
    "VRFHeatEIRFTHi",
    "HeatingEIRLowPLR",
    "HeatingEIRHiPLR",
    "HeatingCombRatio",
    "CoolingLengthCorrectionFactor",
    "VRFTUCoolCapFT",
    "VRFTUHeatCapFT",
    "VRFACCoolCapFFF",
}

DONOR_NAMED_OBJECTS = {
    ("AvailabilityManager:Scheduled", "DOAS Availability"),
    ("AvailabilityManagerAssignmentList", "DOAS Availability Managers"),
    ("Fan:VariableVolume", "DOAS Supply Fan"),
    ("HeatExchanger:AirToAir:SensibleAndLatent", "DOAS Heat Recovery"),
    ("Controller:OutdoorAir", "DOAS OA Controller"),
    ("AirLoopHVAC:ControllerList", "DOAS OA System Controllers"),
    ("AirLoopHVAC", "DOAS"),
    ("AirLoopHVAC:OutdoorAirSystem:EquipmentList", "DOAS OA System Equipment"),
    ("AirLoopHVAC:OutdoorAirSystem", "DOAS OA System"),
    ("OutdoorAir:Mixer", "DOAS OA Mixing Box"),
    ("AirLoopHVAC:SupplyPath", "DOAS Supply Path"),
    ("AirLoopHVAC:ReturnPath", "DOAS Return Path"),
    ("Branch", "DOAS Main Branch"),
    ("BranchList", "DOAS Branches"),
    ("OutdoorAir:NodeList", "OutsideAirInletNodes"),
    ("NodeList", "OutsideAirInletNodes"),
    ("Sizing:System", "DOAS"),
}

HEAT_RECOVERY_AVAILABILITY_SCHEDULE = "DOAS Heat Recovery Availability"
HEAT_RECOVERY_FLOW_SENSOR = "DOAS_HX_SupplyMassFlow"
HEAT_RECOVERY_AVAILABILITY_ACTUATOR = "DOAS_HX_AvailabilityActuator"
HEAT_RECOVERY_LOCKOUT_PROGRAM = "DOAS_HX_LowFlowLockout"
HEAT_RECOVERY_LOCKOUT_MANAGER = "DOAS_HX_LowFlowLockout_Manager"
# Pilot diagnostics showed recurring HX warnings below roughly half of the sized
# DOAS supply mass flow, with the 50% boundary landing near 2.02 kg/s.
HEAT_RECOVERY_MIN_FLOW_KG_S = 2.02


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
    return load_idf(VRF_DOAS_DONOR_IDF)


def _select_donor_support_objects(donor_objects: list[IdfObject]) -> list[IdfObject]:
    selected: list[IdfObject] = []

    for obj in donor_objects:
        class_upper = obj.class_name.upper()
        if class_upper.startswith("SCHEDULE:") and obj.name in DONOR_SCHEDULE_NAMES:
            selected.append(_clone_object(obj))
            continue
        if class_upper.startswith("CURVE:") and obj.name in DONOR_CURVE_NAMES:
            selected.append(_clone_object(obj))
            continue
        if (obj.class_name, obj.name) in DONOR_NAMED_OBJECTS:
            selected.append(_clone_object(obj))

    return selected


def _retune_support_objects(objects: list[IdfObject]) -> list[IdfObject]:
    tuned: list[IdfObject] = []
    for obj in objects:
        clone = _clone_object(obj)
        if (
            clone.class_name == "HeatExchanger:AirToAir:SensibleAndLatent"
            and clone.name == "DOAS Heat Recovery"
        ):
            # Drive ERV availability through an EMS-controlled schedule so low-flow
            # hours bypass the heat exchanger instead of repeatedly tripping warnings.
            clone.fields[1] = HEAT_RECOVERY_AVAILABILITY_SCHEDULE
        elif clone.class_name == "Fan:VariableVolume" and clone.name == "DOAS Supply Fan":
            # Use a constant-volume DOAS fan so the ERV operates closer to its valid flow band.
            clone = IdfObject(
                "Fan:ConstantVolume",
                [
                    "DOAS Supply Fan",
                    "FanAvailSched",
                    clone.fields[2],
                    clone.fields[3],
                    clone.fields[4],
                    clone.fields[9],
                    clone.fields[10],
                    clone.fields[15],
                    clone.fields[16],
                ],
            )
        elif clone.class_name == "Branch" and clone.name == "DOAS Main Branch":
            clone.fields[6] = "Fan:ConstantVolume"
        tuned.append(clone)
    return tuned


def _surface_polygon_area(surface: IdfObject) -> float:
    vertex_count = int(float(surface.fields[10]))
    raw_coords = [float(value) for value in surface.fields[11 : 11 + vertex_count * 3]]
    points = [(raw_coords[index], raw_coords[index + 1]) for index in range(0, len(raw_coords), 3)]

    area = 0.0
    for index, (x_1, y_1) in enumerate(points):
        x_2, y_2 = points[(index + 1) % len(points)]
        area += (x_1 * y_2) - (x_2 * y_1)
    return abs(area) * 0.5


def _retune_vrf_outdoor_air_objects(
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
                zone_floor_areas[zone_name] = zone_floor_areas.get(zone_name, 0.0) + _surface_polygon_area(
                    obj
                )
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


def _make_heat_recovery_lockout_objects() -> list[IdfObject]:
    threshold = f"{HEAT_RECOVERY_MIN_FLOW_KG_S:.3f}"
    return [
        IdfObject(
            "Schedule:Constant",
            [HEAT_RECOVERY_AVAILABILITY_SCHEDULE, "Any Number", "1"],
        ),
        IdfObject(
            "EnergyManagementSystem:Sensor",
            [
                HEAT_RECOVERY_FLOW_SENSOR,
                "DOAS Supply Fan Outlet",
                "System Node Mass Flow Rate",
            ],
        ),
        IdfObject(
            "EnergyManagementSystem:Actuator",
            [
                HEAT_RECOVERY_AVAILABILITY_ACTUATOR,
                HEAT_RECOVERY_AVAILABILITY_SCHEDULE,
                "Schedule:Constant",
                "Schedule Value",
            ],
        ),
        IdfObject(
            "EnergyManagementSystem:Program",
            [
                HEAT_RECOVERY_LOCKOUT_PROGRAM,
                f"IF {HEAT_RECOVERY_FLOW_SENSOR} >= {threshold}",
                f"SET {HEAT_RECOVERY_AVAILABILITY_ACTUATOR} = 1",
                "ELSE",
                f"SET {HEAT_RECOVERY_AVAILABILITY_ACTUATOR} = 0",
                "ENDIF",
            ],
        ),
        IdfObject(
            "EnergyManagementSystem:ProgramCallingManager",
            [
                HEAT_RECOVERY_LOCKOUT_MANAGER,
                "InsideHVACSystemIterationLoop",
                HEAT_RECOVERY_LOCKOUT_PROGRAM,
            ],
        ),
    ]


def _template_object(
    donor_objects: list[IdfObject], class_name: str, object_name: str | None = None
) -> IdfObject:
    for obj in donor_objects:
        if obj.class_name != class_name:
            continue
        if object_name is None or obj.name == object_name:
            return _clone_object(obj)
    raise KeyError(f"Could not find donor object {class_name}::{object_name}")


def _build_vrf_terminal_objects(
    zone_name: str,
    zone_air_node: str,
    return_air_node: str,
) -> list[IdfObject]:
    terminal_name = f"{zone_name} VRF TU"
    equipment_name = f"{zone_name} VRF Equipment"
    inlet_node_list = f"{zone_name} VRF Inlet Nodes"
    air_terminal_name = f"{zone_name} DOAS Air Terminal"
    adu_name = f"{zone_name} DOAS ATU"
    terminal_inlet = f"{zone_name} VRF TU Inlet Node"
    terminal_outlet = f"{zone_name} VRF TU Outlet Node"
    primary_inlet = f"{zone_name} DOAS Mixer Primary Inlet"
    secondary_inlet = f"{zone_name} DOAS Mixer Secondary Inlet"
    cooling_outlet = f"{zone_name} VRF DX CCoil Outlet Node"
    heating_outlet = f"{zone_name} VRF DX HCoil Outlet Node"
    fan_name = f"{zone_name} VRF Supply Fan"
    cooling_coil_name = f"{zone_name} VRF DX Cooling Coil"
    heating_coil_name = f"{zone_name} VRF DX Heating Coil"

    return [
        IdfObject("NodeList", [inlet_node_list, terminal_outlet]),
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
                "1",
                "1",
                "",
                "",
                "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow",
                terminal_name,
                "2",
                "2",
                "",
                "",
            ],
        ),
        IdfObject(
            "AirTerminal:SingleDuct:Mixer",
            [
                air_terminal_name,
                "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow",
                terminal_name,
                terminal_inlet,
                primary_inlet,
                secondary_inlet,
                "InletSide",
            ],
        ),
        IdfObject(
            "ZoneHVAC:AirDistributionUnit",
            [adu_name, terminal_inlet, "AirTerminal:SingleDuct:Mixer", air_terminal_name],
        ),
        IdfObject(
            "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow",
            [
                terminal_name,
                "VRFAvailSched",
                terminal_inlet,
                terminal_outlet,
                "autosize",
                "autosize",
                "autosize",
                "autosize",
                "0",
                "0",
                "0",
                "VRFFanSchedule",
                "drawthrough",
                "Fan:ConstantVolume",
                fan_name,
                "",
                "",
                "COIL:Cooling:DX:VariableRefrigerantFlow",
                cooling_coil_name,
                "COIL:Heating:DX:VariableRefrigerantFlow",
                heating_coil_name,
                "30",
                "20",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ),
        IdfObject(
            "Fan:ConstantVolume",
            [
                fan_name,
                "VRFAvailSched",
                "0.7",
                "600.0",
                "autosize",
                "0.9",
                "1.0",
                heating_outlet,
                terminal_outlet,
            ],
        ),
        IdfObject(
            "COIL:Cooling:DX:VariableRefrigerantFlow",
            [
                cooling_coil_name,
                "VRFAvailSched",
                "autosize",
                "autosize",
                "autosize",
                "VRFTUCoolCapFT",
                "VRFACCoolCapFFF",
                terminal_inlet,
                cooling_outlet,
                "",
            ],
        ),
        IdfObject(
            "COIL:Heating:DX:VariableRefrigerantFlow",
            [
                heating_coil_name,
                "VRFAvailSched",
                "autosize",
                "autosize",
                cooling_outlet,
                heating_outlet,
                "VRFTUHeatCapFT",
                "VRFACCoolCapFFF",
            ],
        ),
    ]


def _build_terminal_unit_list(zone_names: list[str]) -> IdfObject:
    fields = ["VRF Heat Pump TU List"] + [f"{zone_name} VRF TU" for zone_name in zone_names]
    return IdfObject("ZoneTerminalUnitList", fields)


def _build_zone_splitter(zone_names: list[str]) -> IdfObject:
    fields = ["DOAS Zone Splitter", "DOAS Supply Path Inlet"] + [
        f"{zone_name} DOAS Mixer Primary Inlet" for zone_name in zone_names
    ]
    return IdfObject("AirLoopHVAC:ZoneSplitter", fields)


def _build_zone_mixer(
    zone_names: list[str], zone_node_map: dict[str, tuple[str, str]]
) -> IdfObject:
    fields = ["DOAS Zone Mixer", "DOAS Return Air Outlet"] + [
        zone_node_map[zone_name][1] for zone_name in zone_names
    ]
    return IdfObject("AirLoopHVAC:ZoneMixer", fields)


def _build_vrf_condenser(
    donor_objects: list[IdfObject],
    city_name: str,
    master_zone: str,
    zone_names: list[str],
) -> IdfObject:
    condenser = _template_object(
        donor_objects, "AirConditioner:VariableRefrigerantFlow", "VRF Heat Pump"
    )
    condenser.fields[0] = f"{city_name} VRF Heat Pump"
    # The Miami donor's -5 C cooling cutoff is too warm for the colder shoulder seasons
    # seen in this shared office prototype, so keep the stabilized lower cutoff.
    condenser.fields[4] = "-15"
    condenser.fields[33] = master_zone
    condenser.fields[36] = "VRF Heat Pump TU List"
    return condenser


def _make_vrf_output_objects() -> list[IdfObject]:
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
            ["DOAS Relief Air Outlet", "System Node Mass Flow Rate", "Hourly"],
        ),
        IdfObject(
            "Output:Variable",
            ["DOAS Air Loop Inlet", "System Node Mass Flow Rate", "Hourly"],
        ),
        IdfObject(
            "Output:Variable",
            ["DOAS Supply Fan Outlet", "System Node Mass Flow Rate", "Hourly"],
        ),
        IdfObject(
            "Output:Variable",
            [HEAT_RECOVERY_AVAILABILITY_SCHEDULE, "Schedule Value", "Hourly"],
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


def build_vrf_case(city_id: str, output_root: Path | None = None) -> Path:
    ensure_directories()
    city = get_city_config(city_id)
    manifest = load_city_manifest(city_id)

    if not NEUTRAL_MODEL_PATH.exists():
        neutralize_reference_model(REFERENCE_MEDIUM_OFFICE_IDF, NEUTRAL_MODEL_PATH)

    neutral_objects = load_idf(NEUTRAL_MODEL_PATH)
    donor_objects = _load_donor_objects()
    zone_node_map, outdoor_air_map = build_zone_maps(neutral_objects)
    zone_names = sorted(zone_node_map)
    master_zone = zone_names[0]

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
            "Sizing:System",
            "AvailabilityManagerAssignmentList",
        },
        remove_prefixes=(
            "Output:Variable",
            "ZoneHVAC:IdealLoadsAirSystem",
            "AirLoopHVAC",
            "AirTerminal:",
        ),
        remove_name_prefixes=("VAV_",),
    )
    filtered = _retune_vrf_outdoor_air_objects(filtered, outdoor_air_map)

    filtered = replace_object(
        filtered,
        "SimulationControl",
        IdfObject(
            "SimulationControl",
            ["YES", "YES", "NO", "YES", "YES", "No", "1"],
        ),
    )
    filtered = replace_object(
        filtered,
        "Building",
        IdfObject(
            "Building",
            [
                f"{city.display_name} Medium Office VRF Pilot",
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
            _build_vrf_terminal_objects(zone_name, zone_air_node, return_air_node)
        )

    vrf_objects = [
        _build_vrf_condenser(donor_objects, city.display_name, master_zone, zone_names),
        _build_terminal_unit_list(zone_names),
        _build_zone_splitter(zone_names),
        _build_zone_mixer(zone_names, zone_node_map),
    ]

    case_id = build_case_id(city_id, "vrf")
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

    generated_objects = _extend_unique_objects(
        city_objects,
        support_objects
        + vrf_objects
        + generated_zone_objects
        + _make_heat_recovery_lockout_objects()
        + _make_vrf_output_objects(),
    )
    write_idf(case_path, generated_objects)
    return case_path
