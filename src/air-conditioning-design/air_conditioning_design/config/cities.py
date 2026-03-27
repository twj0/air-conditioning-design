# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CityConfig:
    city_id: str
    display_name: str
    climate_zone: str
    weather_parent_dir: str
    weather_package_dir: str

    @property
    def epw_filename(self) -> str:
        return f"{self.weather_package_dir}.epw"

    @property
    def ddy_filename(self) -> str:
        return f"{self.weather_package_dir}.ddy"


CITY_CONFIGS: dict[str, CityConfig] = {
    "shenyang": CityConfig(
        city_id="shenyang",
        display_name="Shenyang",
        climate_zone="severe_cold",
        weather_parent_dir="CHN_LN_Shenyang",
        weather_package_dir="CHN_LN_Shenyang.543420_CSWD",
    ),
    "tianjin": CityConfig(
        city_id="tianjin",
        display_name="Tianjin",
        climate_zone="cold",
        weather_parent_dir="CHN_TJ_Tianjin",
        weather_package_dir="CHN_TJ_Tianjin.545270_CSWD",
    ),
    "chengdu": CityConfig(
        city_id="chengdu",
        display_name="Chengdu",
        climate_zone="hot_summer_cold_winter",
        weather_parent_dir="CHN_SC_Chengdu",
        weather_package_dir="CHN_SC_Chengdu.562940_CSWD",
    ),
    "shenzhen": CityConfig(
        city_id="shenzhen",
        display_name="Shenzhen",
        climate_zone="hot_summer_warm_winter",
        weather_parent_dir="CHN_GD_Shenzhen",
        weather_package_dir="CHN_GD_Shenzhen.592870_CSWD",
    ),
}


def get_city_config(city_id: str) -> CityConfig:
    try:
        return CITY_CONFIGS[city_id]
    except KeyError as exc:
        supported = ", ".join(sorted(CITY_CONFIGS))
        raise ValueError(f"Unsupported city_id: {city_id}. Supported: {supported}") from exc


def has_city(city_id: str) -> bool:
    return city_id in CITY_CONFIGS


def iter_city_ids() -> tuple[str, ...]:
    return tuple(CITY_CONFIGS)
