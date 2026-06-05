from pathlib import Path

from air_conditioning_design.figures.annotations import (
    build_building_structure_annotations,
    build_floor_annotations,
)
from air_conditioning_design.figures.geometry import load_floorplan_geometry

FIXTURE_DXF = Path("tests/fixtures/tianjin_ideal_loads_eplusout.dxf")
FIXTURE_IDF = Path("models/systems/tianjin__ideal_loads.idf")


def test_build_floor_annotations_uses_representative_floor_and_zone_anchors() -> None:
    # Use floor_elevation=4.2 to match our actual 2nd floor height
    annotations = build_floor_annotations(FIXTURE_IDF, floor_elevation=4.2)

    assert annotations.floor_elevation == 4.2
    assert annotations.floor_title == "Floor 2 Plan"
    assert annotations.north_arrow_label == "True North"
    assert annotations.north_arrow_vector == (0.0, 1.0)
    assert annotations.legend_labels == ("Core zone", "Perimeter zone")
    assert tuple(zone.zone_name for zone in annotations.zone_annotations) == (
        "ZF2_C",
        "ZF2_E",
        "ZF2_N",
        "ZF2_S",
        "ZF2_W",
    )
    assert all(zone.anchor for zone in annotations.zone_annotations)
    assert all(len(zone.boundary) == 4 for zone in annotations.zone_annotations)


def test_build_building_structure_annotations_exposes_all_story_levels() -> None:
    structure = build_building_structure_annotations(FIXTURE_IDF)

    assert tuple(floor.floor_elevation for floor in structure.floors) == (0.0, 4.2, 7.8)
    assert tuple(floor.plenum_elevation for floor in structure.floors) == (None, None, None)
    assert tuple(len(floor.occupied_zones) for floor in structure.floors) == (5, 5, 5)
    assert tuple(len(floor.windows) for floor in structure.floors) == (6, 6, 6)
    assert len(structure.roof_outline) == 4
    assert tuple(facade.orientation for facade in structure.facades) == ("South", "East", "North", "West")
    assert tuple(len(facade.windows) for facade in structure.facades) == (9, 0, 9, 0)
    assert structure.footprint_width == 32.0
    assert structure.footprint_depth == 14.24
    assert structure.roof_elevation == 11.4
    assert structure.window_orientation_counts == (
        ("South", 9),
        ("North", 9),
    )
    assert structure.surface_type_counts == (
        ("Wall", 60),
        ("Floor", 15),
        ("Ceiling", 10),
        ("Roof", 5),
    )
