# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-CQ-001)
from pathlib import Path

from air_conditioning_design.models.systems.ideal_loads import build_ideal_loads_case


def test_build_ideal_loads_case_creates_chongqing_case_file(tmp_path: Path) -> None:
    case_path = build_ideal_loads_case("chongqing", output_root=tmp_path)

    assert case_path.name == "chongqing__ideal_loads.idf"
    assert case_path.exists()
    assert (tmp_path / "medium_office_chongqing.idf").exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert "Chongqing Shapingba_Chongqing_CHN Design_Conditions" in case_text
    assert "ZoneHVAC:IdealLoadsAirSystem" in case_text
    assert "Zone Ideal Loads Supply Air Sensible Cooling Rate" in case_text
    assert "  AirLoopHVAC," not in case_text
    assert "  SetpointManager:MixedAir," not in case_text
    assert "  CoilSystem:Cooling:DX," not in case_text
    assert "  Coil:Heating:Fuel," not in case_text
    assert "  Output:Meter," not in case_text
