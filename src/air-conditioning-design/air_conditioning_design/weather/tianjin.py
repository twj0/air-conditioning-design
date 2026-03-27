# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.config.paths import TIANJIN_MANIFEST, WEATHER_ROOT
from air_conditioning_design.weather.catalog import (
    build_weather_manifest,
    write_weather_manifest,
)


def build_tianjin_weather_manifest(weather_root: Path) -> dict[str, str]:
    return build_weather_manifest("tianjin", weather_root)


def write_tianjin_weather_manifest(output_path: Path = TIANJIN_MANIFEST) -> Path:
    return write_weather_manifest("tianjin", output_path)
