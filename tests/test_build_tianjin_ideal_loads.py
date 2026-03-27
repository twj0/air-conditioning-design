# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from pathlib import Path

from air_conditioning_design.models.tianjin_ideal_loads import build_tianjin_ideal_loads_case


def test_build_tianjin_ideal_loads_case_creates_case_file(tmp_path: Path) -> None:
    case_path = build_tianjin_ideal_loads_case(output_root=tmp_path)

    assert case_path.name == "tianjin__ideal_loads.idf"
    assert case_path.exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert "Tianjin_Tianjin_CHN Design_Conditions" in case_text
    assert "ZoneHVAC:IdealLoadsAirSystem" in case_text
    assert "Zone Ideal Loads Supply Air Sensible Cooling Rate" in case_text
    assert "  AirLoopHVAC," not in case_text
    assert "  SetpointManager:MixedAir," not in case_text
    assert "  CoilSystem:Cooling:DX," not in case_text
    assert "  Coil:Heating:Fuel," not in case_text
    assert "  Output:Meter," not in case_text
