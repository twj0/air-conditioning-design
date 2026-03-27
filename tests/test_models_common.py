# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from pathlib import Path

from air_conditioning_design.models.common import extract_design_objects


def test_extract_design_objects_keeps_location_and_sizing_periods() -> None:
    ddy_path = Path(
        "data/raw/weather/CHN_SC_Chengdu/CHN_SC_Chengdu.562940_CSWD/CHN_SC_Chengdu.562940_CSWD.ddy"
    )

    objects = extract_design_objects(ddy_path)

    assert any(obj.class_name == "Site:Location" for obj in objects)
    assert any(obj.class_name.startswith("SizingPeriod:") for obj in objects)
