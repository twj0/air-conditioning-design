import importlib.util
from pathlib import Path


SCRIPT_PATH = Path("scripts/plot/build_floorplan_dxf.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("build_floorplan_dxf", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_floorplan_fixtures_include_cad_furniture_and_people() -> None:
    module = _load_module()

    floor1_items = module._floor_fixtures(module.FLOOR1_ROOMS)
    floor2_items = module._floor_fixtures(module.FLOOR2_ROOMS)
    floor3_items = module._floor_fixtures(module.FLOOR3_ROOMS)

    item_types = {item["type"] for item in floor1_items + floor2_items + floor3_items}
    assert {"desk", "chair", "person", "conference_table", "toilet", "sink"} <= item_types
    assert sum(1 for item in floor2_items if item["type"] == "person") >= 12
    assert len(module.FLOOR_ROOMS) == 3
    assert sum(1 for item in floor3_items if item["type"] == "person") >= 12
