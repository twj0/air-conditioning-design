from pathlib import Path

from air_conditioning_design.figures.annotations import (
    build_building_structure_annotations,
    build_floor_annotations,
)
from air_conditioning_design.figures.geometry import load_floorplan_geometry

FIXTURE_DXF = Path("tests/fixtures/tianjin_ideal_loads_eplusout.dxf")
FIXTURE_IDF = Path("models/systems/tianjin__ideal_loads.idf")


def test_build_floor_annotations_uses_representative_floor_and_zone_anchors() -> None:
    geometry = load_floorplan_geometry(FIXTURE_DXF)

    annotations = build_floor_annotations(FIXTURE_IDF, geometry=geometry)

    assert annotations.floor_elevation == 3.962
    assert annotations.floor_title == "Typical Floor Plan"
    assert annotations.north_arrow_label == "True North"
    assert annotations.north_arrow_vector == (0.0, 1.0)
    assert annotations.legend_labels == ("Core zone", "Perimeter zone")
    assert tuple(zone.zone_name for zone in annotations.zone_annotations) == (
        "Core_mid",
        "Perimeter_mid_ZN_1",
        "Perimeter_mid_ZN_2",
        "Perimeter_mid_ZN_3",
        "Perimeter_mid_ZN_4",
    )
    assert all(zone.anchor for zone in annotations.zone_annotations)
    assert all(len(zone.boundary) == 4 for zone in annotations.zone_annotations)


def test_build_building_structure_annotations_exposes_all_story_levels() -> None:
    structure = build_building_structure_annotations(FIXTURE_IDF)

    assert tuple(floor.floor_elevation for floor in structure.floors) == (0.0, 3.962, 7.925)
    assert tuple(floor.plenum_elevation for floor in structure.floors) == (2.743, 6.706, 10.668)
    assert tuple(len(floor.occupied_zones) for floor in structure.floors) == (5, 5, 5)
    assert tuple(len(floor.windows) for floor in structure.floors) == (4, 4, 4)
    assert len(structure.roof_outline) == 4
    assert tuple(facade.orientation for facade in structure.facades) == (
        "South",
        "East",
        "North",
        "West",
    )
    assert tuple(len(facade.windows) for facade in structure.facades) == (3, 3, 3, 3)
    assert structure.footprint_width == 49.911
    assert structure.footprint_depth == 33.274
    assert structure.roof_elevation == 11.8872
    assert structure.window_orientation_counts == (
        ("South", 3),
        ("East", 3),
        ("North", 3),
        ("West", 3),
    )
    assert structure.surface_type_counts == (
        ("Wall", 72),
        ("Floor", 30),
        ("Ceiling", 25),
        ("Roof", 1),
    )
