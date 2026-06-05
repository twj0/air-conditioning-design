"""Generate the neutral EnergyPlus mother model from the teacher's actual building geometry.

Derived from analysis of example/building2000.dxf:
  - 2 floors, each 32 m × 14.24 m in plan
  - 3.6 m column grid, 3.5 m floor-to-floor height
  - 5 thermal zones per floor (4 perimeter + 1 core) = 10 conditioned zones
  - Windows on south and north facades
"""

from __future__ import annotations

from pathlib import Path

from air_conditioning_design.config.paths import NEUTRAL_MODEL_PATH, ensure_directories
from air_conditioning_design.idf.io import IdfObject, write_idf

# ---------------------------------------------------------------------------
# Building geometry constants (from DXF analysis)
# ---------------------------------------------------------------------------
FLOOR_COUNT = 2
FLOOR_WIDTH_X = 32.0  # m (building length / X direction)
FLOOR_DEPTH_Y = 14.24  # m (building width / Y direction)
PERIMETER_DEPTH = 3.6  # m (one column bay)

# Z-levels (bottom of each floor slab) — 2-storey building, 3.5 m/floor
FLOOR_Z = [0.0, 3.5]
ROOF_Z = 7.0

# Floor heights: uniform 3.5 m per floor
FLOOR_HEIGHTS = [3.5, 3.5]

# ---------------------------------------------------------------------------
# Zone definitions per floor
#
#   N (y=14.24)
#   ┌─────────────────────────────┐
#   │      Perimeter_N            │
#   ├────────────┬────────────────┤
#   │  W  │      Core      │  E  │
#   │  p  │                  │  p  │
#   │  e  │                  │  e  │
#   │  r  │                  │  r  │
#   ├────────────┴────────────────┤
#   │      Perimeter_S            │
#   └─────────────────────────────┘
#   S (y=0)
#
# Each zone is a rectangular box.
# ZF{n}_{S,N,W,E,C} where n = 1,2 (floor number)
# ---------------------------------------------------------------------------


def _zone_name(floor: int, suffix: str) -> str:
    return f"ZF{floor}_{suffix}"


def _zone_vertices(
    x_min: float, x_max: float,
    y_min: float, y_max: float,
    z_bot: float, z_top: float,
) -> dict[str, list[tuple[float, float, float]]]:
    """Return vertices for all 6 surfaces of a rectangular zone.

    EnergyPlus GlobalGeometryRules: UpperLeftCorner, Counterclockwise, World.
    Each surface is viewed from *outside* the zone.
    Surfaces returned: Floor, Ceiling, Wall_S, Wall_N, Wall_W, Wall_E.
    """
    # Floor (viewed from below → CCW from below)
    floor = [
        (x_min, y_min, z_bot),
        (x_min, y_max, z_bot),
        (x_max, y_max, z_bot),
        (x_max, y_min, z_bot),
    ]
    # Ceiling (viewed from above → CCW from above)
    ceiling = [
        (x_min, y_min, z_top),
        (x_max, y_min, z_top),
        (x_max, y_max, z_top),
        (x_min, y_max, z_top),
    ]
    # South wall (y_min, viewed from outside = looking in +Y direction)
    wall_s = [
        (x_min, y_min, z_bot),
        (x_max, y_min, z_bot),
        (x_max, y_min, z_top),
        (x_min, y_min, z_top),
    ]
    # North wall (y_max, viewed from outside = looking in -Y direction)
    wall_n = [
        (x_max, y_max, z_bot),
        (x_min, y_max, z_bot),
        (x_min, y_max, z_top),
        (x_max, y_max, z_top),
    ]
    # West wall (x_min)
    wall_w = [
        (x_min, y_min, z_bot),
        (x_min, y_max, z_bot),
        (x_min, y_max, z_top),
        (x_min, y_min, z_top),
    ]
    # East wall (x_max)
    wall_e = [
        (x_max, y_max, z_bot),
        (x_max, y_min, z_bot),
        (x_max, y_min, z_top),
        (x_max, y_max, z_top),
    ]
    return {
        "Floor": floor,
        "Ceiling": ceiling,
        "Wall_S": wall_s,
        "Wall_N": wall_n,
        "Wall_W": wall_w,
        "Wall_E": wall_e,
    }


def _surface_idf(
    surf_type: str,
    construction: str,
    zone_name: str,
    vertices: list[tuple[float, float, float]],
    *,
    surf_name: str = "",
    outside_boundary: str = "Outdoors",
    sun_exposure: str = "SunExposed",
    wind_exposure: str = "WindExposed",
) -> IdfObject:
    """Build a BuildingSurface:Detailed IdfObject."""
    name = surf_name if surf_name else f"{zone_name} {surf_type}"
    fields: list[str] = [
        name,
        surf_type,
        construction,
        zone_name,
        "",  # Space Name
        outside_boundary,
        "",  # Outside Boundary Condition Object
        sun_exposure,
        wind_exposure,
        "0.0",  # View Factor to Ground
        str(len(vertices)),
    ]
    for v in vertices:
        fields.extend([f"{v[0]:.4f}", f"{v[1]:.4f}", f"{v[2]:.4f}"])
    return IdfObject("BuildingSurface:Detailed", fields)


def _make_window_idf(
    zone_name: str,
    wall_surface_name: str,
    vertices: list[tuple[float, float, float]],
    index: int = 1,
    construction: str = "Double Clear 3mm",
) -> IdfObject:
    """Build a FenestrationSurface:Detailed with world-coordinate vertices.

    Vertices must be CCW when viewed from outside, in world coordinates.
    """
    fields = [
        f"{zone_name} Window {wall_surface_name} {index}",
        "Window",
        construction,
        wall_surface_name,
        "",
        "0.0",
        "",
        "1",
        str(len(vertices)),
    ]
    for v in vertices:
        fields.append(f"{v[0]:.4f},{v[1]:.4f},{v[2]:.4f}")
    return IdfObject("FenestrationSurface:Detailed", fields)


# ---------------------------------------------------------------------------
# Zone definitions
# ---------------------------------------------------------------------------
def _floor_zones(floor: int) -> list[dict]:
    """Return zone geometry dicts for one floor, 0-indexed."""
    z_bot = FLOOR_Z[floor]
    z_top = FLOOR_Z[floor] + FLOOR_HEIGHTS[floor]
    core_y_min = PERIMETER_DEPTH
    core_y_max = FLOOR_DEPTH_Y - PERIMETER_DEPTH
    core_x_min = PERIMETER_DEPTH
    core_x_max = FLOOR_WIDTH_X - PERIMETER_DEPTH

    zones = [
        # South perimeter (full width)
        {
            "name": _zone_name(floor + 1, "S"),
            "x_min": 0.0, "x_max": FLOOR_WIDTH_X,
            "y_min": 0.0, "y_max": PERIMETER_DEPTH,
        },
        # North perimeter
        {
            "name": _zone_name(floor + 1, "N"),
            "x_min": 0.0, "x_max": FLOOR_WIDTH_X,
            "y_min": core_y_max, "y_max": FLOOR_DEPTH_Y,
        },
        # West perimeter
        {
            "name": _zone_name(floor + 1, "W"),
            "x_min": 0.0, "x_max": PERIMETER_DEPTH,
            "y_min": core_y_min, "y_max": core_y_max,
        },
        # East perimeter
        {
            "name": _zone_name(floor + 1, "E"),
            "x_min": FLOOR_WIDTH_X - PERIMETER_DEPTH, "x_max": FLOOR_WIDTH_X,
            "y_min": core_y_min, "y_max": core_y_max,
        },
        # Core
        {
            "name": _zone_name(floor + 1, "C"),
            "x_min": core_x_min, "x_max": core_x_max,
            "y_min": core_y_min, "y_max": core_y_max,
        },
    ]
    for z in zones:
        z["z_bot"] = z_bot
        z["z_top"] = z_top
    return zones


def get_all_zone_names() -> list[str]:
    names: list[str] = []
    for f in range(FLOOR_COUNT):
        zf = _floor_zones(f)
        names.extend(z["name"] for z in zf)
    return names


# ---------------------------------------------------------------------------
# Construction and material definitions
# ---------------------------------------------------------------------------
# GB 50189-2015 envelope U-value limits per climate zone:
#   severe_cold:           wall ≤0.45  roof ≤0.35  window ≤2.5
#   cold:                  wall ≤0.50  roof ≤0.45  window ≤2.7
#   hot_summer_cold_winter: wall ≤0.80  roof ≤0.50  window ≤3.0
#   hot_summer_warm_winter: wall ≤1.5   roof ≤0.80  window ≤4.0
#
# Achieved U-values (wall / roof) by XPS thickness:
#   severe_cold  (70mm/90mm): ≈0.36 / ≈0.30
#   cold         (50mm/70mm): ≈0.48 / ≈0.38
#   hscw         (30mm/40mm): ≈0.70 / ≈0.60
#   hsww         (20mm/30mm): ≈0.91 / ≈0.75
_ENVELOPE_SPECS: dict[str, dict[str, float]] = {
    "severe_cold": {"wall_xps": 0.070, "roof_xps": 0.090},
    "cold": {"wall_xps": 0.050, "roof_xps": 0.070},
    "hot_summer_cold_winter": {"wall_xps": 0.030, "roof_xps": 0.040},
    "hot_summer_warm_winter": {"wall_xps": 0.020, "roof_xps": 0.030},
}


def _make_constructions(climate_zone: str = "cold") -> list[IdfObject]:
    """Material and construction definitions, differentiated by climate zone per GB 50189-2015."""
    spec = _ENVELOPE_SPECS.get(climate_zone, _ENVELOPE_SPECS["cold"])
    wall_xps_thickness = spec["wall_xps"]  # metres
    roof_xps_thickness = spec["roof_xps"]  # metres

    return [
        # --- Materials ---
        IdfObject("Material", [
            "M01 200mm Brick",
            "MediumRough",
            "0.200",
            "0.890",
            "1920",
            "790",
            "0.900",
            "0.840",
            "0.950",
        ]),
        IdfObject("Material", [
            "M02 100mm Brick",
            "MediumRough",
            "0.100",
            "0.890",
            "1920",
            "790",
            "0.900",
        ]),
        IdfObject("Material", [
            "M03 Wall XPS",
            "MediumRough",
            f"{wall_xps_thickness:.3f}",
            "0.030",
            "35",
            "1400",
            "0.900",
        ]),
        IdfObject("Material", [
            "M04 200mm Concrete Roof",
            "MediumRough",
            "0.200",
            "1.310",
            "2240",
            "840",
            "0.900",
        ]),
        IdfObject("Material", [
            "M05 150mm Heavyweight Concrete Floor",
            "MediumRough",
            "0.150",
            "1.950",
            "2240",
            "900",
            "0.900",
        ]),
        IdfObject("Material", [
            "M06 20mm Plaster",
            "Smooth",
            "0.020",
            "0.720",
            "1850",
            "840",
            "0.900",
        ]),
        IdfObject("Material", [
            "M07 20mm Cement Mortar",
            "Smooth",
            "0.020",
            "0.930",
            "1800",
            "1050",
            "0.900",
        ]),
        IdfObject("Material", [
            "M08 10mm Ceramic Tile",
            "Smooth",
            "0.010",
            "1.500",
            "2000",
            "920",
            "0.900",
        ]),
        IdfObject("Material", [
            "M09 Roof XPS",
            "MediumRough",
            f"{roof_xps_thickness:.3f}",
            "0.030",
            "35",
            "1400",
            "0.900",
        ]),
        # Window construction — double glazing with 12mm air gap
        IdfObject("WindowMaterial:Glazing", [
            "Clear 3mm",
            "SpectralAverage",
            "",
            "0.0030",
            "0.837",
            "0.075",
            "0.075",
            "0.898",
            "0.081",
            "0.081",
            "0.0",
            "0.84",
            "0.84",
        ]),
        IdfObject("WindowMaterial:Gas", [
            "Air 12mm",
            "Air",
            "0.0127",
        ]),
        # --- Constructions ---
        IdfObject("Construction", [
            "Ext Wall",
            "M06 20mm Plaster",
            "M01 200mm Brick",
            "M03 Wall XPS",
            "M07 20mm Cement Mortar",
        ]),
        IdfObject("Construction", [
            "Int Wall",
            "M06 20mm Plaster",
            "M02 100mm Brick",
            "M06 20mm Plaster",
        ]),
        IdfObject("Construction", [
            "Roof",
            "M09 Roof XPS",
            "M04 200mm Concrete Roof",
            "M07 20mm Cement Mortar",
        ]),
        IdfObject("Construction", [
            "Floor Slab",
            "M05 150mm Heavyweight Concrete Floor",
            "M08 10mm Ceramic Tile",
        ]),
        IdfObject("Construction", [
            "Double Clear 3mm",
            "Clear 3mm",
            "Air 12mm",
            "Clear 3mm",
        ]),
    ]


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------
def _make_schedules() -> list[IdfObject]:
    """Minimal schedule set for internal loads."""
    return [
        IdfObject("ScheduleTypeLimits", ["Any Number"]),
        IdfObject("ScheduleTypeLimits", ["Fraction", "0.0", "1.0", "CONTINUOUS"]),
        IdfObject("ScheduleTypeLimits", ["On/Off", "0", "1", "DISCRETE"]),
        IdfObject("ScheduleTypeLimits", ["Temperature", "-60", "200", "CONTINUOUS"]),
        # Always on
        IdfObject("Schedule:Compact", [
            "ALWAYS_ON", "On/Off",
            "Through: 12/31",
            "For: AllDays",
            "Until: 24:00", "1",
        ]),
        # Office occupancy schedule (8:00-18:00, weekday)
        IdfObject("Schedule:Compact", [
            "Office Occupancy", "Fraction",
            "Through: 12/31",
            "For: Weekdays SummerDesignDay",
            "Until: 8:00", "0.0",
            "Until: 12:00", "0.9",
            "Until: 13:00", "0.5",
            "Until: 18:00", "0.9",
            "Until: 24:00", "0.0",
            "For: Saturday WinterDesignDay",
            "Until: 8:00", "0.0",
            "Until: 12:00", "0.5",
            "Until: 24:00", "0.0",
            "For: AllOtherDays",
            "Until: 24:00", "0.0",
        ]),
        # Lighting schedule
        IdfObject("Schedule:Compact", [
            "Office Lighting", "Fraction",
            "Through: 12/31",
            "For: Weekdays SummerDesignDay",
            "Until: 8:00", "0.05",
            "Until: 12:00", "0.9",
            "Until: 13:00", "0.5",
            "Until: 18:00", "0.9",
            "Until: 24:00", "0.05",
            "For: Saturday WinterDesignDay",
            "Until: 8:00", "0.05",
            "Until: 12:00", "0.5",
            "Until: 24:00", "0.05",
            "For: AllOtherDays",
            "Until: 24:00", "0.0",
        ]),
        # Equipment schedule
        IdfObject("Schedule:Compact", [
            "Office Equipment", "Fraction",
            "Through: 12/31",
            "For: Weekdays SummerDesignDay",
            "Until: 8:00", "0.1",
            "Until: 12:00", "0.8",
            "Until: 13:00", "0.5",
            "Until: 18:00", "0.8",
            "Until: 24:00", "0.1",
            "For: Saturday WinterDesignDay",
            "Until: 8:00", "0.1",
            "Until: 12:00", "0.5",
            "Until: 24:00", "0.1",
            "For: AllOtherDays",
            "Until: 24:00", "0.0",
        ]),
        # HVAC operation schedule
        IdfObject("Schedule:Compact", [
            "HVAC Operation", "On/Off",
            "Through: 12/31",
            "For: Weekdays SummerDesignDay",
            "Until: 7:00", "0",
            "Until: 19:00", "1",
            "Until: 24:00", "0",
            "For: Saturday",
            "Until: 7:00", "0",
            "Until: 13:00", "1",
            "Until: 24:00", "0",
            "For: AllOtherDays",
            "Until: 24:00", "0",
        ]),
    ]


# ---------------------------------------------------------------------------
# Internal loads
# ---------------------------------------------------------------------------
def _make_internal_loads(zone_name: str, floor_area: float) -> list[IdfObject]:
    """People, Lights, ElectricEquipment, Infiltration for one zone.

    Values from reference paper:
      - Personnel density: 10 m²/person
      - Lighting power density: 10 W/m²
      - Equipment power density: 15 W/m²
      - Fresh air: 30 m³/(h·person)
    """
    obj: list[IdfObject] = []
    n_people = max(1, round(floor_area / 10.0))

    # People
    obj.append(IdfObject("People", [
        f"{zone_name} People",
        zone_name,
        "Office Occupancy",
        "People",
        str(n_people),
        "",
        "",
        "0.3",
        "",
        "ALWAYS_ON",
    ]))

    # Lights
    obj.append(IdfObject("Lights", [
        f"{zone_name} Lights",
        zone_name,
        "Office Lighting",
        "Watts/Area",
        f"{10.0:.1f}",
    ]))

    # ElectricEquipment
    obj.append(IdfObject("ElectricEquipment", [
        f"{zone_name} Equipment",
        zone_name,
        "Office Equipment",
        "Watts/Area",
        f"{15.0:.1f}",
    ]))

    # Infiltration
    obj.append(IdfObject("ZoneInfiltration:DesignFlowRate", [
        f"{zone_name} Infiltration",
        zone_name,
        "ALWAYS_ON",
        "AirChanges/Hour",
        "",
        "0.5",
    ]))

    return obj


# ---------------------------------------------------------------------------
# Sizing objects
# ---------------------------------------------------------------------------
def _make_sizing_zone(zone_name: str, floor_area: float) -> list[IdfObject]:
    """Sizing:Zone and DesignSpecification:OutdoorAir for a perimeter zone."""
    dsoa_name = f"{zone_name} Outdoor Air"
    n_people = max(1, round(floor_area / 10.0))
    fresh_air_m3h = n_people * 30.0
    # Convert m³/h to m³/s
    fresh_air_m3s = fresh_air_m3h / 3600.0

    return [
        IdfObject("DesignSpecification:OutdoorAir", [
            dsoa_name,
            "Flow/Person",
            "0.00833",  # 30 m³/h = 0.00833 m³/s per person
            "",
            "",
            "",
        ]),
        IdfObject("Sizing:Zone", [
            zone_name,
            "SupplyAirTemperature",
            "12.8",
            "",
            "SupplyAirTemperature",
            "50.0",
            "",
            "0.008",
            "0.008",
            dsoa_name,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]),
    ]


# ---------------------------------------------------------------------------
# Zone equipment connections
# ---------------------------------------------------------------------------
def _make_zone_equip(zone_name: str) -> list[IdfObject]:
    """ZoneHVAC:EquipmentConnections with NodeList for HVAC system binding."""
    inlet_list = f"{zone_name} Inlet Nodes"

    return [
        IdfObject("NodeList", [inlet_list, f"{zone_name} Supply Inlet"]),
        IdfObject("ZoneHVAC:EquipmentConnections", [
            zone_name,
            f"{zone_name} Equipment",
            inlet_list,
            "",  # Secondary inlet — set by system builder
            f"{zone_name} Air Node",
            f"{zone_name} Return Air Node",
        ]),
    ]


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------
def make_zone_idf(zone_name: str, floor_area: float) -> IdfObject:
    return IdfObject("Zone", [
        zone_name,
        "0.0",  # X origin
        "0.0",  # Y origin
        "0.0",  # Z origin
        "1",    # Type
        "1",    # Multiplier
        "",     # Ceiling height
        str(round(floor_area, 2)),  # Floor area
    ])


# ---------------------------------------------------------------------------
# Main surface generator
# ---------------------------------------------------------------------------
def _make_surfaces_for_zone(
    zd: dict,
    all_zone_names: set[str],
    is_top_floor: bool,
) -> list[IdfObject]:
    """Generate all surfaces for one zone dict."""
    objs: list[IdfObject] = []
    z_name = zd["name"]
    x_mi, x_ma = zd["x_min"], zd["x_max"]
    y_mi, y_ma = zd["y_min"], zd["y_max"]
    z_b, z_t = zd["z_bot"], zd["z_top"]
    verts = _zone_vertices(x_mi, x_ma, y_mi, y_ma, z_b, z_t)

    # Determine adjacency
    def is_interior_wall(side: str) -> bool:
        """Check if this wall touches another zone."""
        other_name: str | None = None
        for oz_name in all_zone_names:
            if oz_name == z_name:
                continue
            # Check if another zone shares this face
            other = next((z for z in sum((_floor_zones(i) for i in range(FLOOR_COUNT)), [])
                         if z["name"] == oz_name), None)
            if other is None:
                continue
            eps = 0.001
            if side == "S":
                if (abs(y_mi - other["y_max"]) < eps
                        and x_mi < other["x_max"] - eps and x_ma > other["x_min"] + eps
                        and z_b < other["z_top"] - eps and z_t > other["z_bot"] + eps):
                    return True
            elif side == "N":
                if (abs(y_ma - other["y_min"]) < eps
                        and x_mi < other["x_max"] - eps and x_ma > other["x_min"] + eps
                        and z_b < other["z_top"] - eps and z_t > other["z_bot"] + eps):
                    return True
            elif side == "W":
                if (abs(x_mi - other["x_max"]) < eps
                        and y_mi < other["y_max"] - eps and y_ma > other["y_min"] + eps
                        and z_b < other["z_top"] - eps and z_t > other["z_bot"] + eps):
                    return True
            elif side == "E":
                if (abs(x_ma - other["x_min"]) < eps
                        and y_mi < other["y_max"] - eps and y_ma > other["y_min"] + eps
                        and z_b < other["z_top"] - eps and z_t > other["z_bot"] + eps):
                    return True
        return False

    # Floor — always adjacent (except ground floor touches ground)
    if abs(z_b) < 0.001:
        objs.append(_surface_idf(
            "Floor", "Floor Slab", z_name, verts["Floor"],
            outside_boundary="Ground", sun_exposure="NoSun", wind_exposure="NoWind",
        ))
    else:
        objs.append(_surface_idf(
            "Floor", "Floor Slab", z_name, verts["Floor"],
            outside_boundary="Adiabatic", sun_exposure="", wind_exposure="",
        ))

    # Ceiling
    if is_top_floor:
        objs.append(_surface_idf(
            "Roof", "Roof", z_name, verts["Ceiling"],
        ))
    else:
        objs.append(_surface_idf(
            "Ceiling", "Floor Slab", z_name, verts["Ceiling"],
            outside_boundary="Adiabatic", sun_exposure="", wind_exposure="",
        ))

    # Walls
    for side in ("S", "N", "W", "E"):
        surf_name = f"{z_name} Wall_{side}"
        vert_key = f"Wall_{side}"
        if is_interior_wall(side):
            objs.append(_surface_idf(
                "Wall", "Int Wall", z_name, verts[vert_key],
                surf_name=surf_name,
                outside_boundary="Adiabatic", sun_exposure="", wind_exposure="",
            ))
        else:
            objs.append(_surface_idf(
                "Wall", "Ext Wall", z_name, verts[vert_key],
                surf_name=surf_name,
            ))

    return objs


def _make_windows_for_zone(
    zd: dict,
    surfaces: list[IdfObject],
) -> list[IdfObject]:
    """Add windows on south and north perimeter zone walls.

    Windows are evenly distributed across the wall width. WWR ~0.35.
    Vertices in world coordinates, CCW when viewed from outside.
    """
    objs: list[IdfObject] = []
    z_name = zd["name"]
    if not z_name.endswith("_S") and not z_name.endswith("_N"):
        return objs

    wall_width = zd["x_max"] - zd["x_min"]
    wall_height = zd["z_top"] - zd["z_bot"]
    wwr = 0.35
    n_windows = 3
    win_area = (wall_width * wall_height * wwr) / n_windows
    win_height = wall_height * 0.8
    win_width = win_area / win_height
    sill_height = 0.3
    spacing = (wall_width - n_windows * win_width) / (n_windows + 1)
    side = "S" if z_name.endswith("_S") else "N"
    y = zd["y_min"] if side == "S" else zd["y_max"]
    z_bot = zd["z_bot"] + sill_height
    z_top = z_bot + win_height

    for i in range(n_windows):
        x_left = zd["x_min"] + spacing + i * (win_width + spacing)
        x_right = x_left + win_width
        wall_surf_name = f"{z_name} Wall_{side}"

        if side == "S":
            # South wall: normal = South (-Y). CCW: bottom-left→bottom-right→top-right→top-left
            # Edge1 = East, Edge2 = Up, East×Up = South ✓
            world_verts = [
                (x_left, y, z_bot),
                (x_right, y, z_bot),
                (x_right, y, z_top),
                (x_left, y, z_top),
            ]
        else:
            # North wall: normal = North (+Y). CCW: top-left→top-right→bottom-right→bottom-left
            # Edge1 = East, Edge2 = Down, East×Down = North ✓
            world_verts = [
                (x_left, y, z_top),
                (x_right, y, z_top),
                (x_right, y, z_bot),
                (x_left, y, z_bot),
            ]

        objs.append(_make_window_idf(
            z_name, wall_surf_name, world_verts,
            index=i + 1,
        ))

    return objs


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------
def _zone_floor_area(zd: dict) -> float:
    return (zd["x_max"] - zd["x_min"]) * (zd["y_max"] - zd["y_min"])


def _calculate_area(zd: dict) -> float:
    return _zone_floor_area(zd)


def build_actual_building_model(
    target: Path | None = None,
    climate_zone: str = "cold",
) -> Path:
    """Generate a complete EnergyPlus IDF from the actual building geometry.

    This replaces the DOE reference medium office model with our teacher's
    actual building layout (derived from building2000.dxf).

    climate_zone: one of "severe_cold", "cold", "hot_summer_cold_winter",
                  "hot_summer_warm_winter". Controls insulation thickness per GB 50189-2015.
    """
    target = target or NEUTRAL_MODEL_PATH
    ensure_directories()

    all_objects: list[IdfObject] = []

    # Version
    all_objects.append(IdfObject("Version", ["23.2"]))

    # Simulation control
    all_objects.append(IdfObject("SimulationControl", [
        "YES", "YES", "YES", "YES", "NO", "No", "1",
    ]))

    # Building
    all_objects.append(IdfObject("Building", [
        "Medium Office Neutral Base",
        "0.0000", "City", "0.0400", "0.4000",
        "FullInteriorAndExterior", "100", "6",
    ]))

    # RunPeriod
    all_objects.append(IdfObject("RunPeriod", [
        "annual",
        "1", "1", "", "12", "31", "",
        "Sunday", "No", "No", "No", "Yes", "Yes",
    ]))

    # Timestep
    all_objects.append(IdfObject("Timestep", ["6"]))

    # Surface convection
    all_objects.append(IdfObject("SurfaceConvectionAlgorithm:Inside", ["TARP"]))
    all_objects.append(IdfObject("SurfaceConvectionAlgorithm:Outside", ["DOE-2"]))

    # Heat balance
    all_objects.append(IdfObject("HeatBalanceAlgorithm", [
        "ConductionTransferFunction", "200.0000",
    ]))
    all_objects.append(IdfObject("ZoneAirHeatBalanceAlgorithm", ["AnalyticalSolution"]))

    # Sizing parameters
    all_objects.append(IdfObject("Sizing:Parameters", [
        "1.33", "1.33", "6",
    ]))

    # Convergence
    all_objects.append(IdfObject("ConvergenceLimits", ["2", "25"]))

    # Shadow calculation
    all_objects.append(IdfObject("ShadowCalculation", [
        "PolygonClipping", "Periodic", "7", "15000",
    ]))

    # Ground temperatures
    all_objects.append(IdfObject("Site:WaterMainsTemperature", [
        "CORRELATION", "", "9.69", "28.10",
    ]))
    all_objects.append(IdfObject("Site:GroundTemperature:BuildingSurface", [
        "19.527",  # Jan
        "19.502",  # Feb  ... using constant approximation
        "19.527",
        "19.527",
        "19.527",
        "19.527",
        "19.527",
        "19.527",
        "19.527",
        "19.527",
        "19.527",
        "19.527",
    ]))

    # --- Schedules ---
    all_objects.extend(_make_schedules())

    # --- Constructions ---
    all_objects.extend(_make_constructions(climate_zone))

    # --- GlobalGeometryRules ---
    all_objects.append(IdfObject("GlobalGeometryRules", [
        "UpperLeftCorner", "Counterclockwise", "World",
    ]))

    # --- Zones ---
    # Collect all zone names for adjacency detection
    all_zone_names = set(get_all_zone_names())
    total_floor_area = 0.0

    for f in range(FLOOR_COUNT):
        zones = _floor_zones(f)
        for zd in zones:
            area = _calculate_area(zd)
            total_floor_area += area
            all_objects.append(make_zone_idf(zd["name"], area))

    # --- Surfaces ---
    all_zone_surfaces: dict[str, list[IdfObject]] = {}
    for f in range(FLOOR_COUNT):
        zones = _floor_zones(f)
        for zd in zones:
            surf_objs = _make_surfaces_for_zone(zd, all_zone_names, f == FLOOR_COUNT - 1)
            all_zone_surfaces[zd["name"]] = surf_objs
            all_objects.extend(surf_objs)

    # --- Windows ---
    for f in range(FLOOR_COUNT):
        zones = _floor_zones(f)
        for zd in zones:
            win_objs = _make_windows_for_zone(zd, all_zone_surfaces.get(zd["name"], []))
            all_objects.extend(win_objs)

    # --- Internal loads and sizing ---
    for f in range(FLOOR_COUNT):
        zones = _floor_zones(f)
        for zd in zones:
            area = _calculate_area(zd)
            all_objects.extend(_make_internal_loads(zd["name"], area))
            all_objects.extend(_make_sizing_zone(zd["name"], area))

    # --- Zone equipment connections ---
    for f in range(FLOOR_COUNT):
        zones = _floor_zones(f)
        for zd in zones:
            all_objects.extend(_make_zone_equip(zd["name"]))

    # --- Output variables ---
    all_objects.append(IdfObject("OutputControl:Table:Style", ["CommaAndHTML", "JtoKWH"]))
    all_objects.append(IdfObject("Output:Table:SummaryReports", ["AllSummary"]))
    all_objects.append(IdfObject("Output:Variable", ["*", "Zone Mean Air Temperature", "Hourly"]))
    all_objects.append(IdfObject("Output:Variable", ["*", "Zone Total Internal Latent Gain", "Hourly"]))
    all_objects.append(IdfObject("Output:Variable", ["*", "Zone Total Internal Total Gain", "Hourly"]))

    # Write the IDF file
    write_idf(target, all_objects)

    print(f"  Generated {target}")
    print(f"  Zones: {len(all_zone_names)}")
    print(f"  Total floor area: {total_floor_area:.1f} m²")
    print(f"  Zone names: {', '.join(sorted(all_zone_names))}")

    return target


if __name__ == "__main__":
    build_actual_building_model()
