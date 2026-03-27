# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from pathlib import Path

from air_conditioning_design.weather.tianjin import build_tianjin_weather_manifest


def test_build_tianjin_weather_manifest_finds_epw_and_ddy() -> None:
    manifest = build_tianjin_weather_manifest(Path("data/raw/weather"))
    assert manifest["city"] == "tianjin"
    assert manifest["epw_path"].endswith("CHN_TJ_Tianjin.545270_CSWD.epw")
    assert manifest["ddy_path"].endswith("CHN_TJ_Tianjin.545270_CSWD.ddy")
    assert Path(manifest["epw_path"]).exists()
    assert Path(manifest["ddy_path"]).exists()
