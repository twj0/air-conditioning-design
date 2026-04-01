from pathlib import Path

from air_conditioning_design.figures.geometry import load_floorplan_geometry

FIXTURE_DXF = Path("tests/fixtures/tianjin_ideal_loads_eplusout.dxf")


def test_load_floorplan_geometry_extracts_horizontal_faces_and_text() -> None:
    geometry = load_floorplan_geometry(FIXTURE_DXF)

    assert len(geometry.polygons) > 0
    assert len(geometry.texts) == 2
    assert geometry.texts[0].text
    assert geometry.horizontal_elevations[0] == 0.0
    assert len(geometry.horizontal_elevations) == 7


def test_representative_floor_level_selects_middle_occupied_story() -> None:
    geometry = load_floorplan_geometry(FIXTURE_DXF)

    levels = geometry.occupied_floor_levels()

    assert tuple(level.elevation for level in levels) == (0.0, 3.962, 7.925)
    representative = geometry.representative_floor_level()
    assert representative.elevation == 3.962
    assert representative.layers == (
        "CORE_MID",
        "PERIMETER_MID_ZN_1",
        "PERIMETER_MID_ZN_2",
        "PERIMETER_MID_ZN_3",
        "PERIMETER_MID_ZN_4",
    )
