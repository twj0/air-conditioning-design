# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from pathlib import Path

from air_conditioning_design.weather.catalog import build_weather_manifest


def test_build_weather_manifest_supports_tianjin_and_chengdu() -> None:
    tianjin_manifest = build_weather_manifest("tianjin", Path("data/raw/weather"))
    chengdu_manifest = build_weather_manifest("chengdu", Path("data/raw/weather"))

    assert tianjin_manifest["city"] == "tianjin"
    assert tianjin_manifest["epw_path"].endswith("CHN_TJ_Tianjin.545270_CSWD.epw")
    assert tianjin_manifest["ddy_path"].endswith("CHN_TJ_Tianjin.545270_CSWD.ddy")

    assert chengdu_manifest["city"] == "chengdu"
    assert chengdu_manifest["climate_zone"] == "hot_summer_cold_winter"
    assert chengdu_manifest["epw_path"].endswith("CHN_SC_Chengdu.562940_CSWD.epw")
    assert chengdu_manifest["ddy_path"].endswith("CHN_SC_Chengdu.562940_CSWD.ddy")
    assert Path(chengdu_manifest["epw_path"]).exists()
    assert Path(chengdu_manifest["ddy_path"]).exists()
