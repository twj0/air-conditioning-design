"""
Generate 2-floor office building floor plan DXF + PDF.

Building: 32m x 14.15m, 3 floors, 452.8 m2 each, 1358.4 m2 total.
Room layout: custom design (differs from Group 7).

Output:
  results/processed/figures/floorplan_floor{1,2}.dxf
  air-conditioning-design-paper/latex/figures/floorplan_floor{1,2}.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties
import numpy as np

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from air_conditioning_design.config.three_story_design import (  # noqa: E402
    FLOOR_DEPTH,
    FLOOR_WIDTH,
    ROOMS,
    rooms_for_floor,
)

# ---------------------------------------------------------------------------
# Font setup: use explicit .ttf/.ttc path to avoid CJK garbling on Windows
# ---------------------------------------------------------------------------
_FONT_PATHS = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\msyhl.ttc"),
]
_FONT_FILE = None
for p in _FONT_PATHS:
    if p.exists():
        _FONT_FILE = p
        break

if _FONT_FILE:
    _FONT_PROP = FontProperties(fname=str(_FONT_FILE))
    fm.fontManager.addfont(str(_FONT_FILE))
    font_name = _FONT_PROP.get_name()
    matplotlib.rcParams["font.family"] = font_name
    matplotlib.rcParams["font.sans-serif"] = [font_name]
    matplotlib.rcParams["axes.unicode_minus"] = False
else:
    _FONT_PROP = None
    matplotlib.rcParams["font.family"] = "sans-serif"

# ---------------------------------------------------------------------------
# Building geometry (meters)
# ---------------------------------------------------------------------------
W = FLOOR_WIDTH
D = FLOOR_DEPTH
WALL_THICK = 0.24
CORRIDOR_Y1 = 5.08
CORRIDOR_Y2 = 6.88


def _room_tuple(room):
    return (room.name, room.x1, room.y1, room.x2, room.y2)


FLOOR1_ROOMS = [_room_tuple(room) for room in rooms_for_floor(1) if room.name not in {"走廊", "楼梯间"}]
FLOOR2_ROOMS = [_room_tuple(room) for room in rooms_for_floor(2) if room.name not in {"走廊", "楼梯间"}]
FLOOR3_ROOMS = [_room_tuple(room) for room in rooms_for_floor(3) if room.name not in {"走廊", "楼梯间"}]
FLOOR_ROOMS = {1: FLOOR1_ROOMS, 2: FLOOR2_ROOMS, 3: FLOOR3_ROOMS}
STAIR = ("楼梯间", 10.80, CORRIDOR_Y1, 13.90, CORRIDOR_Y2)


def _rotated_box(cx, cy, w, h, angle=0):
    theta = np.deg2rad(angle)
    c, s = np.cos(theta), np.sin(theta)
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def _add_item(items, item_type, x, y, w=0.45, h=0.45, angle=0, label=""):
    items.append({"type": item_type, "x": x, "y": y, "w": w, "h": h, "angle": angle, "label": label})


def _add_workstations(items, x1, y1, x2, y2, cols, rows, angle=0):
    xs = np.linspace(x1 + 1.0, x2 - 1.0, cols)
    ys = np.linspace(y1 + 1.0, y2 - 1.0, rows)
    for row, y in enumerate(ys):
        for col, x in enumerate(xs):
            _add_item(items, "desk", x, y, 1.15, 0.62, angle)
            chair_y = y - 0.55 if angle == 0 else y
            chair_x = x if angle == 0 else x - 0.55
            _add_item(items, "chair", chair_x, chair_y, 0.38, 0.38, angle)
            if (row + col) % 2 == 0:
                _add_item(items, "person", chair_x, chair_y, 0.28, 0.28, angle)


def _add_conference(items, x1, y1, x2, y2, seats=10):
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    table_w = min(5.8, (x2 - x1) - 1.8)
    table_h = min(1.6, (y2 - y1) - 1.8)
    _add_item(items, "conference_table", cx, cy, table_w, table_h)
    n_side = max(2, seats // 4)
    for x in np.linspace(cx - table_w / 2 + 0.6, cx + table_w / 2 - 0.6, n_side):
        _add_item(items, "chair", x, cy - table_h / 2 - 0.45, 0.38, 0.38)
        _add_item(items, "chair", x, cy + table_h / 2 + 0.45, 0.38, 0.38)
    for y in np.linspace(cy - table_h / 2 + 0.2, cy + table_h / 2 - 0.2, 2):
        _add_item(items, "chair", cx - table_w / 2 - 0.45, y, 0.38, 0.38, 90)
        _add_item(items, "chair", cx + table_w / 2 + 0.45, y, 0.38, 0.38, 90)
    for index, x in enumerate(np.linspace(cx - table_w / 2 + 0.8, cx + table_w / 2 - 0.8, min(6, seats))):
        if index % 2 == 0:
            _add_item(items, "person", x, cy + table_h / 2 + 0.45, 0.28, 0.28)
    _add_item(items, "whiteboard", cx, y2 - 0.35, min(2.8, table_w), 0.12)


def _add_wc(items, x1, y1, x2, y2):
    count = 3 if x2 - x1 >= 4 else 2
    for index, x in enumerate(np.linspace(x1 + 0.75, x2 - 0.75, count)):
        _add_item(items, "toilet", x, y2 - 0.75, 0.42, 0.52)
        if index < count - 1:
            _add_item(items, "partition", x + 0.38, y2 - 0.75, 0.06, 1.15)
    for x in np.linspace(x1 + 0.85, x2 - 0.85, max(2, count - 1)):
        _add_item(items, "sink", x, y1 + 0.55, 0.55, 0.35)


def _floor_fixtures(rooms: list[tuple]) -> list[dict]:
    items: list[dict] = []
    for name, x1, y1, x2, y2 in rooms:
        if any(key in name for key in ["办公室", "办公", "财务", "董事", "秘书", "值班"]):
            cols = 3 if x2 - x1 >= 7 else 2
            rows = 2 if y2 - y1 >= 5 else 1
            if "总监" in name:
                _add_item(items, "desk", x1 + 1.6, y1 + 1.2, 1.55, 0.75)
                _add_item(items, "chair", x1 + 1.6, y1 + 0.55, 0.45, 0.45)
                _add_item(items, "person", x1 + 1.6, y1 + 0.55, 0.3, 0.3)
                _add_item(items, "sofa", x2 - 1.8, y2 - 0.9, 1.7, 0.55)
            else:
                _add_workstations(items, x1, y1, x2, y2, cols, rows)
        elif any(key in name for key in ["会议", "会客", "休息", "茶歇"]):
            _add_conference(items, x1, y1, x2, y2, seats=12 if x2 - x1 > 8 else 8)
        elif name in {"门厅", "大厅"}:
            _add_item(items, "front_desk", x1 + 1.6, y2 - 0.8, 2.0, 0.55)
            _add_item(items, "sofa", x2 - 2.0, y1 + 1.0, 1.8, 0.55)
            _add_item(items, "person", x1 + 2.0, y2 - 1.35, 0.3, 0.3)
        elif "资料" in name or "档案" in name or "库房" in name or "储藏" in name or "机房" in name:
            for x in np.linspace(x1 + 0.7, x2 - 0.7, max(2, int((x2 - x1) // 2))):
                _add_item(items, "shelf", x, y2 - 0.55, 0.35, 1.0, 90)
        elif "卫" in name:
            _add_wc(items, x1, y1, x2, y2)
        elif "医务" in name or "治疗" in name:
            _add_item(items, "desk", x1 + 1.2, y1 + 1.0, 1.2, 0.6)
            _add_item(items, "chair", x1 + 1.2, y1 + 0.45, 0.38, 0.38)
            _add_item(items, "sofa", x2 - 1.4, y2 - 0.9, 1.6, 0.55)
    _add_item(items, "evac_arrow", 7.0, (CORRIDOR_Y1 + CORRIDOR_Y2) / 2, 1.8, 0.25)
    _add_item(items, "evac_arrow", 25.0, (CORRIDOR_Y1 + CORRIDOR_Y2) / 2, 1.8, 0.25)
    return items


def _text_kwargs() -> dict:
    if _FONT_PROP:
        return {"fontproperties": _FONT_PROP}
    return {}


def _draw_wall_hatch(ax, x1, y1, x2, y2, color="#d0d0d0", alpha=0.5):
    """Draw hatching for wall thickness."""
    # Use a thin filled rectangle to simulate wall cross-section
    ax.fill_between([x1, x2], y1, y2, color=color, alpha=alpha, zorder=4)


def _draw_door(ax, x, y, width, orientation: str = "H", swing_dir: str = "S"):
    """Draw a door symbol: gap in wall + swing arc.
    orientation: 'H' = horizontal wall, 'V' = vertical wall
    swing_dir: 'S'/'N'/'E'/'W' direction of door swing
    """
    gap = width
    half = gap / 2
    if orientation == "H":
        # Door gap horizontal
        if swing_dir == "S":  # swings downward
            ax.plot([x - half, x - half], [y + WALL_THICK, y - gap * 0.6], color="#333", linewidth=1.0, zorder=8)
            arc = mpatches.Arc((x - half, y), gap * 2, gap * 2, angle=0,
                               theta1=0, theta2=90, color="#333", linewidth=0.8, zorder=8)
            ax.add_patch(arc)
        else:  # swings upward
            ax.plot([x + half, x + half], [y - WALL_THICK, y + gap * 0.6], color="#333", linewidth=1.0, zorder=8)
            arc = mpatches.Arc((x + half, y), gap * 2, gap * 2, angle=0,
                               theta1=90, theta2=180, color="#333", linewidth=0.8, zorder=8)
            ax.add_patch(arc)
    else:
        if swing_dir == "E":
            ax.plot([y + WALL_THICK, y + gap * 0.6], [x - half, x - half], color="#333", linewidth=1.0, zorder=8)
        else:
            ax.plot([y - WALL_THICK, y - gap * 0.6], [x + half, x + half], color="#333", linewidth=1.0, zorder=8)


def _mm(value: float) -> str:
    return f"{int(round(value * 1000))}"


def _draw_tick(ax, x: float, y: float, color: str, size: float = 0.16) -> None:
    ax.plot([x - size, x + size], [y - size, y + size], color=color, linewidth=0.8, zorder=9)


def _draw_h_dimension(ax, x1: float, x2: float, y: float, text: str, color: str, *, text_offset: float = -0.16) -> None:
    ax.plot([x1, x2], [y, y], color=color, linewidth=0.65, zorder=8)
    ax.plot([x1, x1], [y - 0.22, y + 0.22], color=color, linewidth=0.45, zorder=8)
    ax.plot([x2, x2], [y - 0.22, y + 0.22], color=color, linewidth=0.45, zorder=8)
    _draw_tick(ax, x1, y, color)
    _draw_tick(ax, x2, y, color)
    ax.text((x1 + x2) / 2, y + text_offset, text, ha="center", va="top" if text_offset < 0 else "bottom",
            fontsize=6.8, color=color, zorder=9, **_text_kwargs())


def _draw_v_dimension(ax, x: float, y1: float, y2: float, text: str, color: str, *, text_offset: float = -0.18) -> None:
    ax.plot([x, x], [y1, y2], color=color, linewidth=0.65, zorder=8)
    ax.plot([x - 0.22, x + 0.22], [y1, y1], color=color, linewidth=0.45, zorder=8)
    ax.plot([x - 0.22, x + 0.22], [y2, y2], color=color, linewidth=0.45, zorder=8)
    _draw_tick(ax, x, y1, color)
    _draw_tick(ax, x, y2, color)
    ax.text(x + text_offset, (y1 + y2) / 2, text, ha="right" if text_offset < 0 else "left", va="center",
            fontsize=6.8, color=color, rotation=90, zorder=9, **_text_kwargs())


def _draw_axis_bubble(ax, x: float, y: float, label: str, color: str) -> None:
    bubble = mpatches.Circle((x, y), 0.24, fill=False, edgecolor=color, linewidth=0.75, zorder=10)
    ax.add_patch(bubble)
    ax.text(x, y, label, ha="center", va="center", fontsize=7.0, color=color, zorder=11, **_text_kwargs())


def _draw_room_dimensions(ax, room: tuple, color: str) -> None:
    _, x1, y1, x2, y2 = room
    width = x2 - x1
    depth = y2 - y1
    if width >= 2.6:
        y = y1 + min(0.42, depth * 0.23)
        _draw_h_dimension(ax, x1 + 0.25, x2 - 0.25, y, _mm(width), color, text_offset=0.10)
    if depth >= 2.0:
        x = x1 + min(0.42, width * 0.20)
        _draw_v_dimension(ax, x, y1 + 0.25, y2 - 0.25, _mm(depth), color, text_offset=0.12)


def _door_specs(rooms: list[tuple]) -> list[tuple[float, float, float, str, str]]:
    doors: list[tuple[float, float, float, str, str]] = []
    for name, x1, y1, x2, y2 in rooms:
        if "楼梯" in name:
            continue
        width = 1.2 if any(key in name for key in ["大厅", "会议", "陈列", "外贸"]) else 0.9
        if abs(y2 - CORRIDOR_Y1) < 0.01:
            doors.append(((x1 + x2) / 2, CORRIDOR_Y1, width, "H", "S"))
        elif abs(y1 - CORRIDOR_Y2) < 0.01:
            doors.append(((x1 + x2) / 2, CORRIDOR_Y2, width, "H", "N"))
    doors.append(((STAIR[1] + STAIR[3]) / 2, CORRIDOR_Y1, 0.9, "H", "S"))
    doors.append(((STAIR[1] + STAIR[3]) / 2, CORRIDOR_Y2, 0.9, "H", "N"))
    return doors


def _draw_pdf_box(ax, item, edge="#111111", face="none", lw=0.7, zorder=4):
    patch = mpatches.Polygon(
        _rotated_box(item["x"], item["y"], item["w"], item["h"], item.get("angle", 0)),
        closed=True,
        facecolor=face,
        edgecolor=edge,
        linewidth=lw,
        zorder=zorder,
    )
    ax.add_patch(patch)


def _draw_pdf_fixtures(ax, fixtures):
    for item in fixtures:
        item_type = item["type"]
        if item_type == "desk":
            _draw_pdf_box(ax, item, edge="#111111", face="white", lw=0.8)
            monitor = {**item, "w": item["w"] * 0.35, "h": 0.06, "y": item["y"] + item["h"] * 0.22}
            _draw_pdf_box(ax, monitor, edge="#111111", face="#111111", lw=0.4, zorder=5)
        elif item_type in {"chair", "sink", "front_desk", "shelf", "sofa", "tea_table", "partition", "whiteboard"}:
            colors_by_type = {
                "chair": ("#111111", "white"),
                "sink": ("#111111", "white"),
                "front_desk": ("#111111", "white"),
                "shelf": ("#111111", "#f4f4f4"),
                "sofa": ("#111111", "white"),
                "tea_table": ("#111111", "white"),
                "partition": ("#111111", "#111111"),
                "whiteboard": ("#111111", "white"),
            }
            edge, face = colors_by_type[item_type]
            _draw_pdf_box(ax, item, edge=edge, face=face, lw=0.65)
        elif item_type == "conference_table":
            ellipse = mpatches.Ellipse(
                (item["x"], item["y"]),
                item["w"],
                item["h"],
                angle=item.get("angle", 0),
                facecolor="white",
                edgecolor="#111111",
                linewidth=0.9,
                zorder=4,
            )
            ax.add_patch(ellipse)
        elif item_type == "person":
            head = mpatches.Circle((item["x"], item["y"]), item["w"] / 2, facecolor="#111827", edgecolor="#111827", linewidth=0.4, zorder=6)
            ax.add_patch(head)
            ax.text(item["x"], item["y"] - 0.32, "人", ha="center", va="center", fontsize=4.5, color="#111827", zorder=6, **_text_kwargs())
        elif item_type == "toilet":
            bowl = mpatches.Ellipse((item["x"], item["y"]), item["w"], item["h"], facecolor="white", edgecolor="#111111", linewidth=0.65, zorder=4)
            tank = mpatches.Rectangle((item["x"] - item["w"] / 2, item["y"] + item["h"] / 2 - 0.08), item["w"], 0.12, facecolor="white", edgecolor="#111111", linewidth=0.5, zorder=4)
            ax.add_patch(bowl)
            ax.add_patch(tank)
        elif item_type == "evac_arrow":
            ax.annotate("", xy=(item["x"] + item["w"] / 2, item["y"]), xytext=(item["x"] - item["w"] / 2, item["y"]), arrowprops=dict(arrowstyle="->", color="#111111", lw=1.0), zorder=5)


def _setup_dxf_layers(doc):
    layer_specs = {
        "A-WALL": colors.WHITE,
        "A-DOOR": colors.YELLOW,
        "A-GLAZ": colors.CYAN,
        "A-FURN": colors.GREEN,
        "A-PEOP": colors.MAGENTA,
        "A-ANNO": colors.RED,
        "A-GRID": colors.BLUE,
    }
    for name, color in layer_specs.items():
        if name not in doc.layers:
            doc.layers.new(name=name, dxfattribs={"color": color})


def _dxf_poly(msp, points, layer, closed=True, lineweight=15):
    msp.add_lwpolyline(
        points,
        close=closed,
        dxfattribs={"layer": layer, "color": colors.BYLAYER, "lineweight": lineweight},
    )


def _draw_dxf_fixture(msp, item):
    item_type = item["type"]
    layer = "A-PEOP" if item_type == "person" else "A-FURN"
    if item_type in {"desk", "chair", "front_desk", "shelf", "sofa", "tea_table", "partition", "whiteboard", "sink"}:
        _dxf_poly(msp, _rotated_box(item["x"], item["y"], item["w"], item["h"], item.get("angle", 0)), layer)
        if item_type == "desk":
            msp.add_line(
                (item["x"] - item["w"] * 0.18, item["y"] + item["h"] * 0.2),
                (item["x"] + item["w"] * 0.18, item["y"] + item["h"] * 0.2),
                dxfattribs={"layer": layer, "color": colors.BYLAYER, "lineweight": 12},
            )
    elif item_type == "conference_table":
        msp.add_ellipse(
            center=(item["x"], item["y"]),
            major_axis=(item["w"] / 2, 0),
            ratio=item["h"] / item["w"],
            dxfattribs={"layer": layer, "color": colors.BYLAYER},
        )
    elif item_type == "person":
        msp.add_circle((item["x"], item["y"]), item["w"] / 2, dxfattribs={"layer": layer, "color": colors.BYLAYER})
        msp.add_text("P", height=0.16, dxfattribs={"layer": layer, "color": colors.BYLAYER}).set_placement((item["x"], item["y"] - 0.32), align=TextEntityAlignment.CENTER)
    elif item_type == "toilet":
        major_axis = (item["w"] / 2, 0)
        ratio = item["h"] / item["w"]
        if ratio > 1:
            major_axis = (0, item["h"] / 2)
            ratio = item["w"] / item["h"]
        msp.add_ellipse(
            center=(item["x"], item["y"]),
            major_axis=major_axis,
            ratio=ratio,
            dxfattribs={"layer": layer, "color": colors.BYLAYER},
        )
        _dxf_poly(msp, _rotated_box(item["x"], item["y"] + item["h"] / 2 - 0.06, item["w"], 0.12), layer)
    elif item_type == "evac_arrow":
        msp.add_line(
            (item["x"] - item["w"] / 2, item["y"]),
            (item["x"] + item["w"] / 2, item["y"]),
            dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER, "lineweight": 15},
        )
        _dxf_poly(
            msp,
            [
                (item["x"] + item["w"] / 2, item["y"]),
                (item["x"] + item["w"] / 2 - 0.25, item["y"] + 0.12),
                (item["x"] + item["w"] / 2 - 0.25, item["y"] - 0.12),
            ],
            "A-ANNO",
        )


def _render_floor_pdf(
    rooms: list[tuple],
    title: str,
    output_path: Path,
) -> None:
    """Render one floor plan as a CAD-style PDF via matplotlib."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    lw_wall = 3.5
    lw_inner = 1.8
    lw_dim = 0.8
    color_wall = "#000000"
    color_inner = "#222222"
    color_text = "#000000"
    color_dim = "#000000"
    color_window = "#000000"
    color_hatch = "#f2f2f2"

    wall_t = WALL_THICK

    # --- Outer wall (double line + hatching) ---
    for (x1, y1, x2, y2) in [(-wall_t, -wall_t, 0, D + wall_t),
                               (W, -wall_t, W + wall_t, D + wall_t),
                               (-wall_t, -wall_t, W + wall_t, 0),
                               (-wall_t, D, W + wall_t, D + wall_t)]:
        _draw_wall_hatch(ax, x1, y1, x2, y2, color_hatch)

    outer = mpatches.Rectangle(
        (-wall_t, -wall_t), W + 2 * wall_t, D + 2 * wall_t,
        linewidth=lw_wall, edgecolor=color_wall, facecolor="none", zorder=5,
    )
    ax.add_patch(outer)
    inner = mpatches.Rectangle(
        (0, 0), W, D,
        linewidth=lw_wall * 0.7, edgecolor=color_wall, facecolor="none", zorder=5,
    )
    ax.add_patch(inner)

    # --- Internal partition walls ---
    for _, x1, y1, x2, y2 in rooms:
        rect = mpatches.Rectangle(
            (x1, y1), x2 - x1, y2 - y1,
            linewidth=lw_inner, edgecolor=color_inner, facecolor="none", zorder=3,
        )
        ax.add_patch(rect)

    # --- Corridor boundary lines ---
    ax.plot([0, W], [CORRIDOR_Y1, CORRIDOR_Y1], color=color_inner, linewidth=lw_inner, zorder=3)
    ax.plot([0, W], [CORRIDOR_Y2, CORRIDOR_Y2], color=color_inner, linewidth=lw_inner, zorder=3)

    # --- Stairwell ---
    sx1, sy1, sx2, sy2 = STAIR[1], STAIR[2], STAIR[3], STAIR[4]
    stair_rect = mpatches.Rectangle(
        (sx1, sy1), sx2 - sx1, sy2 - sy1,
        linewidth=lw_inner, edgecolor=color_inner, facecolor="#f5f5f5", zorder=2,
    )
    ax.add_patch(stair_rect)
    n_steps = 10
    step_h = (sy2 - sy1) / n_steps
    for i in range(1, n_steps):
        ax.plot([sx1, sx2], [sy1 + i * step_h, sy1 + i * step_h],
                color="#999999", linewidth=0.6, zorder=2)
    # Up/down arrows
    mid_x = (sx1 + sx2) / 2
    ax.annotate("", xy=(mid_x, sy2 - 0.3), xytext=(mid_x, sy1 + 1.2),
                arrowprops=dict(arrowstyle="->", color="#555", lw=1.2), zorder=3)
    ax.annotate("", xy=(mid_x, sy1 + 0.3), xytext=(mid_x, sy2 - 1.2),
                arrowprops=dict(arrowstyle="->", color="#555", lw=1.2), zorder=3)

    # --- Doors ---
    doors = _door_specs(rooms)
    for x, y, w, orient, swing in doors:
        _draw_door(ax, x, y, w, orient, swing)

    # --- Windows ---
    # South wall windows
    south_windows = [(3.5, 2.4), (11.5, 3.0), (20.0, 2.4), (28.0, 2.4)]
    for cx, w in south_windows:
        hw = w / 2
        # Outer line
        ax.plot([cx - hw, cx + hw], [-wall_t, -wall_t],
                color=color_window, linewidth=2.2, solid_capstyle="butt", zorder=7)
        # Inner glass line
        ax.plot([cx - hw, cx + hw], [-wall_t - 0.15, -wall_t - 0.15],
                color=color_window, linewidth=1.2, zorder=7)
        # End ticks
        ax.plot([cx - hw, cx - hw], [-wall_t - 0.15, -wall_t], color=color_window, linewidth=1.0, zorder=7)
        ax.plot([cx + hw, cx + hw], [-wall_t - 0.15, -wall_t], color=color_window, linewidth=1.0, zorder=7)
        # Glass arc symbol
        xs = np.linspace(cx - hw, cx + hw, 15)
        ys = -wall_t - 0.08 + 0.05 * np.sin(np.linspace(0, np.pi, 15))
        ax.plot(xs, ys, color=color_window, linewidth=0.6, zorder=7)

    # North wall windows
    north_windows = [(2.25, 1.8), (6.75, 1.8), (12.25, 2.4), (18.75, 2.4), (27.0, 3.6)]
    for cx, w in north_windows:
        hw = w / 2
        ax.plot([cx - hw, cx + hw], [D + wall_t, D + wall_t],
                color=color_window, linewidth=2.2, solid_capstyle="butt", zorder=7)
        ax.plot([cx - hw, cx + hw], [D + wall_t + 0.15, D + wall_t + 0.15],
                color=color_window, linewidth=1.2, zorder=7)
        ax.plot([cx - hw, cx - hw], [D + wall_t, D + wall_t + 0.15], color=color_window, linewidth=1.0, zorder=7)
        ax.plot([cx + hw, cx + hw], [D + wall_t, D + wall_t + 0.15], color=color_window, linewidth=1.0, zorder=7)
        xs = np.linspace(cx - hw, cx + hw, 15)
        ys = D + wall_t + 0.08 + 0.05 * np.sin(np.linspace(0, np.pi, 15))
        ax.plot(xs, ys, color=color_window, linewidth=0.6, zorder=7)

    _draw_pdf_fixtures(ax, _floor_fixtures(rooms))

    # --- Labels ---
    # Corridor
    corr_x = 7.0
    corr_y = (CORRIDOR_Y1 + CORRIDOR_Y2) / 2
    ax.text(corr_x, corr_y, "走廊", ha="center", va="center",
            fontsize=10, color=color_text, zorder=6, **_text_kwargs())

    # Stairwell
    ax.text((sx1 + sx2) / 2, (sy1 + sy2) / 2, "楼梯间",
            ha="center", va="center", fontsize=8, color=color_text, zorder=6,
            **_text_kwargs())

    # Room labels
    for name, x1, y1, x2, y2 in rooms:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        area = (x2 - x1) * (y2 - y1)
        fs_name = 9 if len(name) <= 3 else 8
        ax.text(cx, cy + 0.35, name, ha="center", va="center",
                fontsize=fs_name, color=color_text, weight="bold", zorder=6,
                **_text_kwargs())
        ax.text(cx, cy - 0.55, f"{area:.1f}m²", ha="center", va="center",
                fontsize=7.5, color="#444444", zorder=6, **_text_kwargs())
        _draw_room_dimensions(ax, (name, x1, y1, x2, y2), color_dim)

    # --- Dimension annotations (CAD style with tick marks) ---
    x_axes = [0, 3.60, 7.20, 10.80, 13.90, 17.46, 20.96, 24.56, 28.16, 32.00]
    y_axes = [0, CORRIDOR_Y1, CORRIDOR_Y2, 10.45, D]
    for lower_y in (-1.05, -1.82):
        ax.plot([0, 0], [lower_y, 0], color=color_dim, linewidth=0.45, zorder=7)
        ax.plot([W, W], [lower_y, 0], color=color_dim, linewidth=0.45, zorder=7)
    for i in range(len(x_axes) - 1):
        _draw_h_dimension(ax, x_axes[i], x_axes[i + 1], -1.05, _mm(x_axes[i + 1] - x_axes[i]), color_dim)
    _draw_h_dimension(ax, 0, W, -1.82, _mm(W), color_dim)
    for i in range(len(x_axes) - 1):
        _draw_h_dimension(ax, x_axes[i], x_axes[i + 1], D + 1.00, _mm(x_axes[i + 1] - x_axes[i]), color_dim, text_offset=0.10)
    _draw_h_dimension(ax, 0, W, D + 1.72, _mm(W), color_dim, text_offset=0.10)

    for left_x in (-0.95, -1.72):
        ax.plot([left_x, 0], [0, 0], color=color_dim, linewidth=0.45, zorder=7)
        ax.plot([left_x, 0], [D, D], color=color_dim, linewidth=0.45, zorder=7)
    for i in range(len(y_axes) - 1):
        _draw_v_dimension(ax, -0.95, y_axes[i], y_axes[i + 1], _mm(y_axes[i + 1] - y_axes[i]), color_dim)
    _draw_v_dimension(ax, -1.72, 0, D, _mm(D), color_dim)
    for i in range(len(y_axes) - 1):
        _draw_v_dimension(ax, W + 0.95, y_axes[i], y_axes[i + 1], _mm(y_axes[i + 1] - y_axes[i]), color_dim, text_offset=0.12)
    _draw_v_dimension(ax, W + 1.72, 0, D, _mm(D), color_dim, text_offset=0.12)

    # --- Grid lines (column grid) ---
    grid_color = "#b5b5b5"
    for index, x_grid in enumerate(x_axes, start=1):
        ax.plot([x_grid, x_grid], [-2.1, D + 1.1], color=grid_color, linewidth=0.35, linestyle=":", zorder=1)
        _draw_axis_bubble(ax, x_grid, D + 0.62, str(index), color_dim)
    for index, y_grid in enumerate(y_axes, start=1):
        ax.plot([-2.1, W + 0.5], [y_grid, y_grid], color=grid_color, linewidth=0.35, linestyle=":", zorder=1)
        _draw_axis_bubble(ax, -0.55, y_grid, chr(64 + index), color_dim)
        _draw_axis_bubble(ax, W + 0.55, y_grid, chr(64 + index), color_dim)

    # --- North arrow ---
    nx, ny = W + 2.0, D - 1.5
    circle = mpatches.Circle((nx, ny), 0.7, fill=False, edgecolor="#333", linewidth=1.2, zorder=7)
    ax.add_patch(circle)
    # Arrow triangle
    ax.fill([nx, nx - 0.25, nx + 0.25], [ny + 0.65, ny - 0.1, ny - 0.1],
            color="#333", zorder=8)
    ax.text(nx, ny + 1.1, "N", ha="center", va="bottom", fontsize=12,
            color="#333", weight="bold", zorder=8)

    # --- Scale bar ---
    bar_y = -3.5
    bar_len = 5.0
    ax.plot([0, bar_len], [bar_y, bar_y], color=color_wall, linewidth=3, solid_capstyle="butt")
    # Alternating segments
    seg = bar_len / 5
    for i in range(5):
        if i % 2 == 0:
            ax.fill_between([i * seg, (i + 1) * seg], bar_y - 0.15, bar_y + 0.15, color=color_wall, zorder=5)
    ax.text(bar_len / 2, bar_y - 0.5, "0    1m    2m    3m    4m    5m",
            ha="center", va="top", fontsize=8, color=color_wall, **_text_kwargs())

    # --- Title block ---
    title_y = -5.5
    ax.plot([0, W], [title_y, title_y], color=color_wall, linewidth=1.5)
    ax.text(0, title_y - 0.3, f"{title}    比例 1:100", ha="left", va="top",
            fontsize=11, weight="bold", color=color_text, **_text_kwargs())

    ax.set_xlim(-4.0, W + 4)
    ax.set_ylim(-7.0, D + 3)
    ax.set_aspect("equal")
    ax.axis("off")

    plt.tight_layout(pad=0.2)
    fig.savefig(str(output_path), format="pdf", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  PDF: {output_path}")


def _draw_dxf(msp, rooms: list[tuple], title: str) -> None:
    """Generate DXF geometry."""
    name_map = {
        "门厅": "Lobby", "大厅": "Hall", "行政办公室1": "Admin-1",
        "行政办公室2": "Admin-2", "女卫": "WC-F", "男卫": "WC-M",
        "资料室": "Archive-1", "档案室": "Archive-2", "会议室": "Meeting",
        "设计办公室1": "Design-1", "设计办公室2": "Design-2",
        "大会议室": "Conf-L", "总监办公室": "Director",
        "档案资料室": "Records", "库房": "Storage", "休息室": "Lounge",
        "小会议室": "Conf-S",
    }

    msp.add_lwpolyline(
        [(0, 0), (W, 0), (W, D), (0, D)],
        close=True, dxfattribs={"layer": "A-WALL", "color": colors.BYLAYER, "lineweight": 50},
    )

    for name, x1, y1, x2, y2 in rooms:
        msp.add_lwpolyline(
            [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
            close=True, dxfattribs={"layer": "A-WALL", "color": colors.BYLAYER, "lineweight": 25},
        )
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        en_name = name_map.get(name, name)
        msp.add_text(en_name, height=0.4, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                     ).set_placement((cx, cy + 0.2), align=TextEntityAlignment.CENTER)
        area = (x2 - x1) * (y2 - y1)
        msp.add_text(f"{area:.1f}m2", height=0.3, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                     ).set_placement((cx, cy - 0.4), align=TextEntityAlignment.CENTER)

    msp.add_lwpolyline(
        [(0, CORRIDOR_Y1), (W, CORRIDOR_Y1), (W, CORRIDOR_Y2), (0, CORRIDOR_Y2)],
        close=True, dxfattribs={"layer": "A-WALL", "color": colors.BYLAYER, "lineweight": 20},
    )
    msp.add_text("Corridor", height=0.4, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                 ).set_placement((7, (CORRIDOR_Y1 + CORRIDOR_Y2) / 2),
                                 align=TextEntityAlignment.CENTER)

    sx1, sy1, sx2, sy2 = STAIR[1], STAIR[2], STAIR[3], STAIR[4]
    msp.add_lwpolyline(
        [(sx1, sy1), (sx2, sy1), (sx2, sy2), (sx1, sy2)],
        close=True, dxfattribs={"layer": "A-WALL", "color": colors.BYLAYER, "lineweight": 20},
    )
    for i in range(1, 10):
        y = sy1 + i * (sy2 - sy1) / 10
        msp.add_line((sx1, y), (sx2, y), dxfattribs={"layer": "A-GRID", "color": colors.BYLAYER, "lineweight": 8})
    msp.add_text("Stairs", height=0.35, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                 ).set_placement(((sx1 + sx2) / 2, (sy1 + sy2) / 2),
                                 align=TextEntityAlignment.CENTER)

    doors = [(x, y, w) for x, y, w, _, _ in _door_specs(rooms)]
    for x, y, w in doors:
        msp.add_line((x - w / 2, y), (x - w / 2, y - 0.7), dxfattribs={"layer": "A-DOOR", "color": colors.BYLAYER, "lineweight": 12})
        msp.add_arc((x - w / 2, y), w, 0, 90, dxfattribs={"layer": "A-DOOR", "color": colors.BYLAYER})

    for cx, w in [(3.5, 2.4), (11.5, 3.0), (20.0, 2.4), (28.0, 2.4)]:
        msp.add_line((cx - w / 2, -WALL_THICK), (cx + w / 2, -WALL_THICK), dxfattribs={"layer": "A-GLAZ", "color": colors.BYLAYER, "lineweight": 35})
        msp.add_line((cx - w / 2, -WALL_THICK - 0.15), (cx + w / 2, -WALL_THICK - 0.15), dxfattribs={"layer": "A-GLAZ", "color": colors.BYLAYER, "lineweight": 12})
    for cx, w in [(2.25, 1.8), (6.75, 1.8), (12.25, 2.4), (18.75, 2.4), (27.0, 3.6)]:
        msp.add_line((cx - w / 2, D + WALL_THICK), (cx + w / 2, D + WALL_THICK), dxfattribs={"layer": "A-GLAZ", "color": colors.BYLAYER, "lineweight": 35})
        msp.add_line((cx - w / 2, D + WALL_THICK + 0.15), (cx + w / 2, D + WALL_THICK + 0.15), dxfattribs={"layer": "A-GLAZ", "color": colors.BYLAYER, "lineweight": 12})

    for x_grid in [0, 8, 16, 24, 32]:
        msp.add_line((x_grid, -0.5), (x_grid, D + 0.5), dxfattribs={"layer": "A-GRID", "color": colors.BYLAYER, "lineweight": 5})
    for y_grid in [0, CORRIDOR_Y1, CORRIDOR_Y2, D]:
        msp.add_line((-0.5, y_grid), (W + 0.5, y_grid), dxfattribs={"layer": "A-GRID", "color": colors.BYLAYER, "lineweight": 5})

    for item in _floor_fixtures(rooms):
        _draw_dxf_fixture(msp, item)

    msp.add_text("32.00m", height=0.4, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                 ).set_placement((W / 2, -1.2), align=TextEntityAlignment.CENTER)
    msp.add_text(f"{D:.2f}m", height=0.4, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                 ).set_placement((-1.8, D / 2), align=TextEntityAlignment.CENTER)

    msp.add_circle((W + 2, D - 2), 0.6, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER})
    msp.add_line((W + 2, D - 2.6), (W + 2, D - 1.2), dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER})
    msp.add_text("N", height=0.5, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                 ).set_placement((W + 2, D - 0.8), align=TextEntityAlignment.CENTER)

    msp.add_text(title, height=0.6, dxfattribs={"layer": "A-ANNO", "color": colors.BYLAYER}
                 ).set_placement((W / 2, D + 1.5), align=TextEntityAlignment.CENTER)


def build_floorplans():
    """Generate floor plans (DXF + PDF)."""
    dxf_dir = Path("results/processed/figures")
    pdf_dir = Path("air-conditioning-design-paper/latex/figures")
    dxf_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    floor_titles = {1: "一层平面图", 2: "二层平面图", 3: "三层平面图"}
    for floor, rooms in FLOOR_ROOMS.items():
        print(f"Floor {floor}:")
        doc = ezdxf.new("R2010")
        _setup_dxf_layers(doc)
        _draw_dxf(doc.modelspace(), rooms, f"Floor {floor} Plan  1:100")
        dxf_path = dxf_dir / f"floorplan_floor{floor}.dxf"
        doc.saveas(str(dxf_path))
        print(f"  DXF: {dxf_path}")
        _render_floor_pdf(rooms, floor_titles[floor], pdf_dir / f"floorplan_floor{floor}.pdf")

    print("\nArea summary:")
    for floor, rooms in FLOOR_ROOMS.items():
        room_total = sum((x2 - x1) * (y2 - y1) for _, x1, y1, x2, y2 in rooms)
        corr_area = W * (CORRIDOR_Y2 - CORRIDOR_Y1)
        stair_area = (STAIR[3] - STAIR[1]) * (STAIR[4] - STAIR[2])
        net_corr = corr_area - stair_area
        total = room_total + net_corr
        print(f"  Floor {floor}: rooms={room_total:.1f} corridor={net_corr:.1f} "
              f"stairs={stair_area:.1f} total={total:.1f} m2")


if __name__ == "__main__":
    build_floorplans()
