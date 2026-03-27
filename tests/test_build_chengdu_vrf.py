# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-VRF-001)
from pathlib import Path

from air_conditioning_design.idf.io import load_idf
from air_conditioning_design.models.systems.vrf import build_vrf_case


def test_build_vrf_case_creates_chengdu_case_file(tmp_path: Path) -> None:
    case_path = build_vrf_case("chengdu", output_root=tmp_path)

    assert case_path.name == "chengdu__vrf.idf"
    assert case_path.exists()
    assert (tmp_path / "medium_office_chengdu.idf").exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert "Chengdu_Sichuan_CHN Design_Conditions" in case_text
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
