# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-FCU-CQ-001)
from pathlib import Path

from air_conditioning_design.idf.io import load_idf
from air_conditioning_design.models.systems.fcu_doas import build_fcu_doas_case


def test_build_fcu_doas_case_creates_chongqing_case_file(tmp_path: Path) -> None:
    case_path = build_fcu_doas_case("chongqing", output_root=tmp_path)

    assert case_path.name == "chongqing__fcu_doas.idf"
    assert case_path.exists()
    assert (tmp_path / "medium_office_chongqing.idf").exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert "Chongqing Shapingba_Chongqing_CHN Design_Conditions" in case_text
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
