# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-VRF-HS-001)
from pathlib import Path

from air_conditioning_design.idf.io import load_idf
from air_conditioning_design.models.systems.vrf import build_vrf_case


def test_build_vrf_case_creates_shenzhen_case_file(tmp_path: Path) -> None:
    case_path = build_vrf_case("shenzhen", output_root=tmp_path)

    assert case_path.name == "shenzhen__vrf.idf"
    assert case_path.exists()
    assert (tmp_path / "medium_office_shenzhen.idf").exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert "Shenzhen_Guangdong_CHN Design_Conditions" in case_text
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

    terminals = [
        obj
        for obj in objects
        if obj.class_name.upper() == "ZONEHVAC:TERMINALUNIT:VARIABLEREFRIGERANTFLOW"
    ]
    assert len(terminals) == 15
