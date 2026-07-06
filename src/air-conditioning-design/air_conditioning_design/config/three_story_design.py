from __future__ import annotations

from dataclasses import dataclass


FLOOR_WIDTH = 32.0
FLOOR_DEPTH = 14.15
FLOOR_HEIGHT = 3.0
TOTAL_FLOOR_AREA = FLOOR_WIDTH * FLOOR_DEPTH
TOTAL_BUILDING_AREA = TOTAL_FLOOR_AREA * 3


@dataclass(frozen=True)
class RoomSpec:
    floor: int
    room_id: str
    name: str
    x1: float
    y1: float
    x2: float
    y2: float
    room_type: str
    conditioned: bool = True
    people_density_m2_per_person: float = 6.0
    fresh_air_m3h_person: float = 40.0
    lighting_w_m2: float = 10.0
    equipment_w_m2: float = 15.0

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


ROOM_TYPE_PROFILES = {
    "office": (7.0, 40.0, 10.0, 15.0),
    "open_office": (5.5, 45.0, 10.0, 18.0),
    "meeting": (3.5, 40.0, 11.0, 8.0),
    "lobby": (9.0, 35.0, 12.0, 6.0),
    "exhibition": (10.0, 35.0, 12.0, 8.0),
    "medical": (7.0, 45.0, 11.0, 12.0),
    "archive": (25.0, 25.0, 6.0, 4.0),
    "toilet": (20.0, 25.0, 6.0, 1.0),
    "corridor": (25.0, 20.0, 6.0, 1.0),
    "stair": (30.0, 20.0, 5.0, 0.0),
}


def _room(
    floor: int,
    room_id: str,
    name: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    room_type: str,
    *,
    conditioned: bool = True,
) -> RoomSpec:
    people, fresh_air, lighting, equipment = ROOM_TYPE_PROFILES[room_type]
    conditioned = conditioned and room_type != "stair"
    return RoomSpec(
        floor=floor,
        room_id=room_id,
        name=name,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        room_type=room_type,
        conditioned=conditioned,
        people_density_m2_per_person=people,
        fresh_air_m3h_person=fresh_air,
        lighting_w_m2=lighting,
        equipment_w_m2=equipment,
    )


ROOMS: tuple[RoomSpec, ...] = (
    _room(1, "1001", "外贸办公室", 0.00, 6.88, 10.80, 14.15, "open_office"),
    _room(1, "1002", "卫生间", 10.80, 6.88, 13.90, 14.15, "toilet"),
    _room(1, "1003", "医务室", 13.90, 6.88, 17.46, 10.45, "medical"),
    _room(1, "1004", "治疗室", 13.90, 10.45, 17.46, 14.15, "medical"),
    _room(1, "1005", "设备科办公1", 17.46, 6.88, 24.56, 10.45, "office"),
    _room(1, "1006", "设备科办公2", 17.46, 10.45, 24.56, 14.15, "office"),
    _room(1, "1007", "门厅", 12.00, 0.00, 17.46, 5.08, "lobby"),
    _room(1, "1008", "陈列室", 17.46, 0.00, 32.00, 5.08, "exhibition"),
    _room(1, "1009", "楼梯间", 10.80, 5.08, 13.90, 6.88, "stair"),
    _room(1, "1010", "走廊", 0.00, 5.08, 32.00, 6.88, "corridor"),
    _room(1, "1011", "接待大厅", 0.00, 0.00, 12.00, 5.08, "lobby"),
    _room(1, "1012", "值班室", 24.56, 6.88, 32.00, 14.15, "office"),
    _room(2, "2001", "办公室1", 0.00, 6.88, 5.40, 14.15, "office"),
    _room(2, "2002", "办公室2", 5.40, 6.88, 10.80, 14.15, "office"),
    _room(2, "2003", "卫生间", 10.80, 6.88, 13.90, 14.15, "toilet"),
    _room(2, "2004", "办公室3", 13.90, 6.88, 17.46, 10.45, "office"),
    _room(2, "2005", "档案室", 13.90, 10.45, 17.46, 14.15, "archive"),
    _room(2, "2006", "办公室4", 17.46, 6.88, 20.96, 14.15, "office"),
    _room(2, "2007", "储藏室", 20.96, 6.88, 24.56, 14.15, "archive"),
    _room(2, "2008", "办公大厅", 0.00, 0.00, 10.80, 5.08, "open_office"),
    _room(2, "2009", "副董办公室", 17.46, 0.00, 24.56, 5.08, "office"),
    _room(2, "2010", "办公室5", 24.56, 0.00, 28.16, 5.08, "office"),
    _room(2, "2011", "办公室6", 28.16, 0.00, 32.00, 5.08, "office"),
    _room(2, "2012", "办公室7", 24.56, 6.88, 28.16, 14.15, "office"),
    _room(2, "2013", "办公室8", 28.16, 6.88, 32.00, 14.15, "office"),
    _room(2, "2014", "楼梯间", 10.80, 5.08, 13.90, 6.88, "stair"),
    _room(2, "2015", "走廊", 0.00, 5.08, 32.00, 6.88, "corridor"),
    _room(2, "2016", "会议接待室", 13.90, 0.00, 17.46, 5.08, "meeting"),
    _room(2, "2017", "二层前室", 10.80, 0.00, 13.90, 5.08, "corridor"),
    _room(3, "3001", "财务室1", 17.46, 10.45, 20.96, 14.15, "office"),
    _room(3, "3002", "财务室2", 20.96, 10.45, 24.56, 14.15, "office"),
    _room(3, "3003", "机房", 24.56, 10.45, 28.16, 14.15, "archive"),
    _room(3, "3004", "卫生间", 10.80, 6.88, 13.90, 14.15, "toilet"),
    _room(3, "3005", "休息室1", 28.16, 10.45, 32.00, 14.15, "meeting"),
    _room(3, "3006", "楼梯间", 10.80, 5.08, 13.90, 6.88, "stair"),
    _room(3, "3007", "会客室", 24.56, 0.00, 32.00, 5.08, "meeting"),
    _room(3, "3008", "休息室2", 28.16, 6.88, 32.00, 10.45, "meeting"),
    _room(3, "3009", "阳台", 0.00, 0.00, 3.60, 5.08, "corridor"),
    _room(3, "3010", "董事办公室", 0.00, 10.45, 5.40, 14.15, "office"),
    _room(3, "3011", "秘书办公", 5.40, 10.45, 10.80, 14.15, "office"),
    _room(3, "3012", "走廊", 0.00, 5.08, 32.00, 6.88, "corridor"),
    _room(3, "3013", "小型会议室", 0.00, 6.88, 10.80, 10.45, "meeting"),
    _room(3, "3014", "办公室1", 3.60, 0.00, 7.20, 5.08, "office"),
    _room(3, "3015", "办公室2", 7.20, 0.00, 10.80, 5.08, "office"),
    _room(3, "3016", "办公室3", 13.90, 0.00, 17.46, 5.08, "office"),
    _room(3, "3017", "办公室4", 17.46, 0.00, 24.56, 5.08, "office"),
    _room(3, "3018", "办公茶歇区", 13.90, 6.88, 17.46, 14.15, "meeting"),
    _room(3, "3019", "休息室3", 17.46, 6.88, 24.56, 10.45, "meeting"),
    _room(3, "3020", "三层前室", 10.80, 0.00, 13.90, 5.08, "corridor"),
    _room(3, "3021", "设备资料间", 24.56, 6.88, 28.16, 10.45, "archive"),
)


CITY_ENVELOPE_PARAMS = {
    "shenyang": {
        "display": "沈阳",
        "climate_zone": "severe_cold",
        "t_out_dry": 31.5,
        "t_out_wet": 25.3,
        "t_out_daily_mean": 27.3,
        "h_out": 78.4,
        "t_loc_correction": -0.5,
        "K_wall": 0.35,
        "K_roof": 0.30,
        "K_win": 2.30,
        "SC": 0.40,
        "lat": 41.8,
    },
    "tianjin": {
        "display": "天津",
        "climate_zone": "cold",
        "t_out_dry": 33.9,
        "t_out_wet": 26.9,
        "t_out_daily_mean": 29.4,
        "h_out": 84.0,
        "t_loc_correction": 0.5,
        "K_wall": 0.45,
        "K_roof": 0.38,
        "K_win": 2.50,
        "SC": 0.40,
        "lat": 39.1,
    },
    "chengdu": {
        "display": "成都",
        "climate_zone": "hot_summer_cold_winter",
        "t_out_dry": 31.9,
        "t_out_wet": 26.4,
        "t_out_daily_mean": 27.8,
        "h_out": 79.5,
        "t_loc_correction": -0.3,
        "K_wall": 0.70,
        "K_roof": 0.50,
        "K_win": 2.60,
        "SC": 0.36,
        "lat": 30.7,
    },
    "chongqing": {
        "display": "重庆",
        "climate_zone": "hot_summer_cold_winter",
        "t_out_dry": 35.5,
        "t_out_wet": 27.6,
        "t_out_daily_mean": 30.7,
        "h_out": 89.0,
        "t_loc_correction": 1.0,
        "K_wall": 0.72,
        "K_roof": 0.52,
        "K_win": 2.50,
        "SC": 0.34,
        "lat": 29.6,
    },
    "shenzhen": {
        "display": "深圳",
        "climate_zone": "hot_summer_warm_winter",
        "t_out_dry": 33.7,
        "t_out_wet": 27.5,
        "t_out_daily_mean": 29.8,
        "h_out": 86.0,
        "t_loc_correction": 0.8,
        "K_wall": 0.78,
        "K_roof": 0.58,
        "K_win": 2.20,
        "SC": 0.33,
        "lat": 22.5,
    },
}


def rooms_for_floor(floor: int) -> list[RoomSpec]:
    return [room for room in ROOMS if room.floor == floor]


def conditioned_rooms() -> list[RoomSpec]:
    return [room for room in ROOMS if room.conditioned]


def total_conditioned_area() -> float:
    return TOTAL_BUILDING_AREA
