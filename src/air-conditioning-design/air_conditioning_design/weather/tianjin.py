# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

import json
from pathlib import Path

from air_conditioning_design.config.paths import (
    TIANJIN_DDY,
    TIANJIN_EPW,
    TIANJIN_MANIFEST,
    WEATHER_ROOT,
    ensure_directories,
)


def build_tianjin_weather_manifest(weather_root: Path) -> dict[str, str]:
    package_root = weather_root / "CHN_TJ_Tianjin" / "CHN_TJ_Tianjin.545270_CSWD"
    manifest = {
        "city": "tianjin",
        "climate_zone": "cold",
        "weather_root": str(package_root.resolve()),
        "epw_path": str((package_root / TIANJIN_EPW.name).resolve()),
        "ddy_path": str((package_root / TIANJIN_DDY.name).resolve()),
    }

    missing = [
        key for key in ("epw_path", "ddy_path") if not Path(manifest[key]).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Tianjin weather manifest is incomplete. Missing: {', '.join(missing)}"
        )

    return manifest


def write_tianjin_weather_manifest(output_path: Path = TIANJIN_MANIFEST) -> Path:
    ensure_directories()
    manifest = build_tianjin_weather_manifest(WEATHER_ROOT)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return output_path
