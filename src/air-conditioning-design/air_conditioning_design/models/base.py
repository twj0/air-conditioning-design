# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

import json
from pathlib import Path

from air_conditioning_design.config.cities import get_city_config
from air_conditioning_design.config.paths import (
    NEUTRAL_MODEL_PATH,
    city_model_path,
    ensure_directories,
)
from air_conditioning_design.models.building_from_dxf import build_actual_building_model


def neutralize_reference_model(source: Path, target: Path) -> Path:
    return build_actual_building_model(target)


def build_neutral_mother_model() -> Path:
    return build_actual_building_model(NEUTRAL_MODEL_PATH, climate_zone="cold")


def build_city_building_model(city_id: str, target: Path | None = None) -> Path:
    """Build a city-specific building model with climate-appropriate envelope.

    The neutral model is the cold-climate default. City models vary XPS
    insulation thickness per GB 50189-2015 to match each city's climate zone.
    """
    city = get_city_config(city_id)
    target = target or city_model_path(city_id)
    ensure_directories()
    target.parent.mkdir(parents=True, exist_ok=True)

    result = build_actual_building_model(target, climate_zone=city.climate_zone)

    metadata = {"city_id": city_id, "climate_zone": city.climate_zone}
    metadata_path = target.parent / f"{target.stem}_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, ensure_ascii=False)

    return result
