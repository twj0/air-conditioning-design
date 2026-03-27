# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-FCU-001)
from pathlib import Path

from air_conditioning_design.idf.io import load_idf
from air_conditioning_design.models.tianjin_fcu_doas import build_tianjin_fcu_doas_case


def test_build_tianjin_fcu_doas_case_creates_case_file(tmp_path: Path) -> None:
    case_path = build_tianjin_fcu_doas_case(output_root=tmp_path)

    assert case_path.name == "tianjin__fcu_doas.idf"
    assert case_path.exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert "Tianjin_Tianjin_CHN Design_Conditions" in case_text
    assert "ZoneHVAC:FourPipeFanCoil" in case_text
    assert "HeatExchanger:AirToAir:SensibleAndLatent" in case_text
    assert "AirTerminal:SingleDuct:Mixer" in case_text
    assert "PlantLoop" in case_text
    assert "Electricity:HVAC" in case_text

    objects = load_idf(case_path)
    fan_coils = [
        obj for obj in objects if obj.class_name.upper() == "ZONEHVAC:FOURPIPEFANCOIL"
    ]
    assert len(fan_coils) == 15

    doas_supply_fans = [obj for obj in objects if obj.name == "DOAS Supply Fan"]
    assert len(doas_supply_fans) == 1
    assert doas_supply_fans[0].class_name == "Fan:ConstantVolume"

    plant_loops = [obj for obj in objects if obj.class_name.upper() == "PLANTLOOP"]
    assert len(plant_loops) == 2

    sizing_parameters = [obj for obj in objects if obj.class_name == "Sizing:Parameters"]
    assert len(sizing_parameters) == 1

    water_objects = [
        obj
        for obj in objects
        if obj.class_name in {"WaterHeater:Mixed", "WaterUse:Connections", "WaterUse:Equipment"}
    ]
    assert water_objects == []

    shw_plant_lists = [
        obj
        for obj in objects
        if obj.class_name.startswith("PlantEquipment") and obj.name and "SWHSys1" in obj.name
    ]
    assert shw_plant_lists == []

    chw_reset_managers = [
        obj
        for obj in objects
        if obj.class_name == "SetpointManager:OutdoorAirReset"
        and obj.name == "Chilled Water Loop ChW Temp Manager"
    ]
    assert len(chw_reset_managers) == 1
    assert chw_reset_managers[0].fields[2] == "7.2"

    outdoor_air_specs = [
        obj
        for obj in objects
        if obj.class_name == "DesignSpecification:OutdoorAir"
        and obj.name == "SZ DSOA Core_bottom"
    ]
    assert len(outdoor_air_specs) == 1
    assert outdoor_air_specs[0].fields[1] == "Flow/Zone"
    assert float(outdoor_air_specs[0].fields[4]) > 0.0
