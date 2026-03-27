# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

import json
from pathlib import Path

from air_conditioning_design.config.cities import get_city_config
from air_conditioning_design.config.paths import (
    WEATHER_ROOT,
    ensure_directories,
    weather_manifest_path,
)


def build_weather_manifest(city_id: str, weather_root: Path = WEATHER_ROOT) -> dict[str, str]:
    city = get_city_config(city_id)
    package_root = weather_root / city.weather_parent_dir / city.weather_package_dir
    manifest = {
        "city": city.city_id,
        "city_name": city.display_name,
        "climate_zone": city.climate_zone,
        "weather_package": city.weather_package_dir,
        "weather_root": str(package_root.resolve()),
        "epw_path": str((package_root / city.epw_filename).resolve()),
        "ddy_path": str((package_root / city.ddy_filename).resolve()),
    }

    missing = [
        key for key in ("epw_path", "ddy_path") if not Path(manifest[key]).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Weather manifest for {city_id} is incomplete. Missing: {', '.join(missing)}"
        )

    return manifest


def write_weather_manifest(city_id: str, output_path: Path | None = None) -> Path:
    ensure_directories()
    manifest = build_weather_manifest(city_id)
    target = output_path or weather_manifest_path(city_id)
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def load_weather_manifest(city_id: str) -> dict[str, str]:
    manifest_path = weather_manifest_path(city_id)
    if not manifest_path.exists():
        write_weather_manifest(city_id, manifest_path)
    return json.loads(manifest_path.read_text(encoding="utf-8"))
