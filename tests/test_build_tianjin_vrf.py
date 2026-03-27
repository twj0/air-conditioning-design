# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from pathlib import Path

from air_conditioning_design.idf.io import load_idf
from air_conditioning_design.models.tianjin_vrf import build_tianjin_vrf_case


def test_build_tianjin_vrf_case_creates_case_file(tmp_path: Path) -> None:
    case_path = build_tianjin_vrf_case(output_root=tmp_path)

    assert case_path.name == "tianjin__vrf.idf"
    assert case_path.exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert "Tianjin_Tianjin_CHN Design_Conditions" in case_text
    assert "AirConditioner:VariableRefrigerantFlow" in case_text
    assert "HeatExchanger:AirToAir:SensibleAndLatent" in case_text
    assert "AirTerminal:SingleDuct:Mixer" in case_text
    assert "Electricity:HVAC" in case_text

    objects = load_idf(case_path)
    vrf_condensers = [
        obj
        for obj in objects
        if obj.class_name.upper() == "AIRCONDITIONER:VARIABLEREFRIGERANTFLOW"
    ]
    assert len(vrf_condensers) == 1
    assert vrf_condensers[0].fields[4] == "-15"

    heat_recovery_objects = [
        obj
        for obj in objects
        if obj.class_name.upper() == "HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT"
        and obj.name == "DOAS Heat Recovery"
    ]
    assert len(heat_recovery_objects) == 1
    assert heat_recovery_objects[0].fields[1] == "DOAS Heat Recovery Availability"

    doas_supply_fans = [obj for obj in objects if obj.name == "DOAS Supply Fan"]
    assert len(doas_supply_fans) == 1
    assert doas_supply_fans[0].class_name == "Fan:ConstantVolume"

    hx_availability_schedules = [
        obj
        for obj in objects
        if obj.class_name == "Schedule:Constant"
        and obj.name == "DOAS Heat Recovery Availability"
    ]
    assert len(hx_availability_schedules) == 1
    assert hx_availability_schedules[0].fields[2] == "1"

    ems_sensors = [
        obj
        for obj in objects
        if obj.class_name == "EnergyManagementSystem:Sensor"
        and obj.name == "DOAS_HX_SupplyMassFlow"
    ]
    assert len(ems_sensors) == 1
    assert ems_sensors[0].fields[1] == "DOAS Supply Fan Outlet"

    ems_program_managers = [
        obj
        for obj in objects
        if obj.class_name == "EnergyManagementSystem:ProgramCallingManager"
        and obj.name == "DOAS_HX_LowFlowLockout_Manager"
    ]
    assert len(ems_program_managers) == 1
    assert ems_program_managers[0].fields[1] == "InsideHVACSystemIterationLoop"

    outdoor_air_specs = [
        obj
        for obj in objects
        if obj.class_name == "DesignSpecification:OutdoorAir"
        and obj.name == "SZ DSOA Core_bottom"
    ]
    assert len(outdoor_air_specs) == 1
    assert outdoor_air_specs[0].fields[1] == "Flow/Zone"
    assert float(outdoor_air_specs[0].fields[4]) > 0.0
