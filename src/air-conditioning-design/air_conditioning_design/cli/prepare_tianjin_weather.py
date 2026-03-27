# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

from air_conditioning_design.weather.tianjin import write_tianjin_weather_manifest


def main() -> None:
    manifest_path = write_tianjin_weather_manifest()
    print(manifest_path)

