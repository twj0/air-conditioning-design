# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
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

CASE_ID_SEPARATOR = "__"


def build_case_id(city_id: str, system_id: str) -> str:
    return f"{city_id}{CASE_ID_SEPARATOR}{system_id}"


def split_case_id(case_id: str) -> tuple[str, str]:
    if CASE_ID_SEPARATOR not in case_id:
        raise ValueError(f"Invalid case id: {case_id}")
    city_id, system_id = case_id.split(CASE_ID_SEPARATOR, 1)
    if not city_id or not system_id:
        raise ValueError(f"Invalid case id: {case_id}")
    return city_id, system_id


def weather_manifest_path(city_id: str) -> Path:
    return INTERIM_ROOT / f"{city_id}_weather_manifest.json"


def city_model_path(city_id: str) -> Path:
    return MODELS_CITY_ROOT / city_id / f"medium_office_{city_id}.idf"


def system_model_path(case_id: str) -> Path:
    return MODELS_SYSTEM_ROOT / f"{case_id}.idf"


def results_dir_for_case(case_id: str) -> Path:
    return RESULTS_RAW_ROOT / case_id


def summary_path_for_case(case_id: str) -> Path:
    return RESULTS_PROCESSED_ROOT / f"{case_id}_summary.csv"


TIANJIN_WEATHER_PACKAGE = (
    WEATHER_ROOT / "CHN_TJ_Tianjin" / "CHN_TJ_Tianjin.545270_CSWD"
)
TIANJIN_EPW = TIANJIN_WEATHER_PACKAGE / "CHN_TJ_Tianjin.545270_CSWD.epw"
TIANJIN_DDY = TIANJIN_WEATHER_PACKAGE / "CHN_TJ_Tianjin.545270_CSWD.ddy"
TIANJIN_MANIFEST = weather_manifest_path("tianjin")
NEUTRAL_MODEL_PATH = MODELS_BASE_ROOT / "medium_office_neutral.idf"
NEUTRAL_METADATA_PATH = MODELS_BASE_ROOT / "medium_office_neutral_metadata.json"
TIANJIN_CITY_MODEL_PATH = city_model_path("tianjin")
TIANJIN_IDEAL_LOADS_PATH = system_model_path("tianjin__ideal_loads")
TIANJIN_VRF_PATH = system_model_path("tianjin__vrf")
TIANJIN_FCU_DOAS_PATH = system_model_path("tianjin__fcu_doas")
TIANJIN_RESULTS_ROOT = results_dir_for_case("tianjin__ideal_loads")
TIANJIN_VRF_RESULTS_ROOT = results_dir_for_case("tianjin__vrf")
TIANJIN_FCU_DOAS_RESULTS_ROOT = results_dir_for_case("tianjin__fcu_doas")
TIANJIN_SUMMARY_PATH = summary_path_for_case("tianjin__ideal_loads")
TIANJIN_VRF_SUMMARY_PATH = summary_path_for_case("tianjin__vrf")
TIANJIN_FCU_DOAS_SUMMARY_PATH = summary_path_for_case("tianjin__fcu_doas")

MEDIUM_OFFICE_FLOOR_AREA_M2 = 4982.0


def ensure_directories() -> None:
    for directory in (
        INTERIM_ROOT,
        MODELS_BASE_ROOT,
        MODELS_CITY_ROOT,
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
