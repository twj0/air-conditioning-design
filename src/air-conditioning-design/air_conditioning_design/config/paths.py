# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-FCU-001)
from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
WEATHER_ROOT = REPO_ROOT / "data" / "raw" / "weather"
INTERIM_ROOT = REPO_ROOT / "data" / "interim"
MODELS_BASE_ROOT = REPO_ROOT / "models" / "base"
MODELS_CITY_ROOT = REPO_ROOT / "models" / "cities"
MODELS_SYSTEM_ROOT = REPO_ROOT / "models" / "systems"
RESULTS_RAW_ROOT = REPO_ROOT / "results" / "raw"
RESULTS_PROCESSED_ROOT = REPO_ROOT / "results" / "processed"
TESTS_ROOT = REPO_ROOT / "tests"

REFERENCE_MEDIUM_OFFICE_IDF = Path(
    r"D:/energyplus/2320/ExampleFiles/RefBldgMediumOfficeNew2004_Chicago.idf"
)
DEFAULT_ENERGYPLUS_EXE = Path(r"D:/energyplus/2320/energyplus.exe")
VRF_DOAS_DONOR_IDF = Path(r"D:/energyplus/2320/ExampleFiles/DOAToVRF.idf")
FCU_DOAS_DONOR_IDF = Path(r"D:/energyplus/2320/ExampleFiles/DOAToFanCoilInlet.idf")

TIANJIN_WEATHER_PACKAGE = (
    WEATHER_ROOT / "CHN_TJ_Tianjin" / "CHN_TJ_Tianjin.545270_CSWD"
)
TIANJIN_EPW = TIANJIN_WEATHER_PACKAGE / "CHN_TJ_Tianjin.545270_CSWD.epw"
TIANJIN_DDY = TIANJIN_WEATHER_PACKAGE / "CHN_TJ_Tianjin.545270_CSWD.ddy"
TIANJIN_MANIFEST = INTERIM_ROOT / "tianjin_weather_manifest.json"
NEUTRAL_MODEL_PATH = MODELS_BASE_ROOT / "medium_office_neutral.idf"
NEUTRAL_METADATA_PATH = MODELS_BASE_ROOT / "medium_office_neutral_metadata.json"
TIANJIN_CITY_MODEL_PATH = MODELS_CITY_ROOT / "tianjin" / "medium_office_tianjin.idf"
TIANJIN_IDEAL_LOADS_PATH = MODELS_SYSTEM_ROOT / "tianjin__ideal_loads.idf"
TIANJIN_VRF_PATH = MODELS_SYSTEM_ROOT / "tianjin__vrf.idf"
TIANJIN_FCU_DOAS_PATH = MODELS_SYSTEM_ROOT / "tianjin__fcu_doas.idf"
TIANJIN_RESULTS_ROOT = RESULTS_RAW_ROOT / "tianjin__ideal_loads"
TIANJIN_VRF_RESULTS_ROOT = RESULTS_RAW_ROOT / "tianjin__vrf"
TIANJIN_FCU_DOAS_RESULTS_ROOT = RESULTS_RAW_ROOT / "tianjin__fcu_doas"
TIANJIN_SUMMARY_PATH = RESULTS_PROCESSED_ROOT / "tianjin__ideal_loads_summary.csv"
TIANJIN_VRF_SUMMARY_PATH = RESULTS_PROCESSED_ROOT / "tianjin__vrf_summary.csv"
TIANJIN_FCU_DOAS_SUMMARY_PATH = RESULTS_PROCESSED_ROOT / "tianjin__fcu_doas_summary.csv"

MEDIUM_OFFICE_FLOOR_AREA_M2 = 4982.0


def ensure_directories() -> None:
    for directory in (
        INTERIM_ROOT,
        MODELS_BASE_ROOT,
        MODELS_CITY_ROOT / "tianjin",
        MODELS_SYSTEM_ROOT,
        RESULTS_RAW_ROOT,
        RESULTS_PROCESSED_ROOT,
        TESTS_ROOT,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def resolve_energyplus_executable() -> Path:
    if DEFAULT_ENERGYPLUS_EXE.exists():
        return DEFAULT_ENERGYPLUS_EXE

    discovered = shutil.which("energyplus")
    if discovered:
        return Path(discovered)

    raise FileNotFoundError(
        "EnergyPlus executable was not found at the default path or on PATH."
    )
