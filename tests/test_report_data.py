# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
import csv
from pathlib import Path

from air_conditioning_design.analysis import report_data, report_plots


def _write_csv(path: Path, fieldnames: list[str], row: dict[str, str | float | int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def _write_summary_fixture(tmp_path: Path, case_id: str, row: dict[str, str | float | int]) -> None:
    _write_csv(tmp_path / "processed" / f"{case_id}_summary.csv", list(row.keys()), row)


def _write_eio_fixture(tmp_path: Path, case_id: str, lines: list[str]) -> None:
    case_root = tmp_path / "raw" / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    (case_root / "eplusout.eio").write_text("\n".join(lines), encoding="utf-8")


def _patch_report_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        report_data,
        "summary_path_for_case",
        lambda case_id: tmp_path / "processed" / f"{case_id}_summary.csv",
    )
    monkeypatch.setattr(
        report_data,
        "results_dir_for_case",
        lambda case_id: tmp_path / "raw" / case_id,
    )


def _seed_report_fixtures(tmp_path: Path) -> None:
    _write_summary_fixture(
        tmp_path,
        "tianjin__ideal_loads",
        {
            "case_id": "tianjin__ideal_loads",
            "city": "tianjin",
            "system": "ideal_loads",
            "peak_cooling_load": 275.184,
            "peak_cooling_load_per_m2": 55.236,
            "annual_cooling_load": 539982.673,
            "annual_heating_load": 268931.951,
        },
    )
    _write_summary_fixture(
        tmp_path,
        "shenzhen__ideal_loads",
        {
            "case_id": "shenzhen__ideal_loads",
            "city": "shenzhen",
            "system": "ideal_loads",
            "peak_cooling_load": 310.0,
            "peak_cooling_load_per_m2": 62.224,
            "annual_cooling_load": 680000.0,
            "annual_heating_load": 15000.0,
        },
    )
    _write_summary_fixture(
        tmp_path,
        "tianjin__vrf",
        {
            "case_id": "tianjin__vrf",
            "city": "tianjin",
            "system": "vrf",
            "annual_hvac_electricity": 676474.187,
            "annual_hvac_electricity_per_m2": 135.784,
            "vrf_terminal_count": 15,
        },
    )
    _write_summary_fixture(
        tmp_path,
        "shenzhen__vrf",
        {
            "case_id": "shenzhen__vrf",
            "city": "shenzhen",
            "system": "vrf",
            "annual_hvac_electricity": 520000.0,
            "annual_hvac_electricity_per_m2": 104.376,
            "vrf_terminal_count": 15,
        },
    )
    _write_summary_fixture(
        tmp_path,
        "tianjin__fcu_doas",
        {
            "case_id": "tianjin__fcu_doas",
            "city": "tianjin",
            "system": "fcu_doas",
            "annual_hvac_electricity": 57218.599,
            "annual_hvac_electricity_per_m2": 11.485,
            "fcu_terminal_count": 15,
            "plant_loop_count": 2,
        },
    )
    _write_summary_fixture(
        tmp_path,
        "shenzhen__fcu_doas",
        {
            "case_id": "shenzhen__fcu_doas",
            "city": "shenzhen",
            "system": "fcu_doas",
            "annual_hvac_electricity": 61613.131,
            "annual_hvac_electricity_per_m2": 12.367,
            "fcu_terminal_count": 15,
            "plant_loop_count": 2,
        },
    )

    _write_eio_fixture(
        tmp_path,
        "tianjin__vrf",
        [
            "Component Sizing Information, AirConditioner:VariableRefrigerantFlow, TIANJIN VRF HEAT PUMP, Design Size Rated Total Cooling Capacity (gross) [W], 589117.60788",
            "Component Sizing Information, AirConditioner:VariableRefrigerantFlow, TIANJIN VRF HEAT PUMP, Design Size Rated Total Heating Capacity [W], 589117.60788",
            "Component Sizing Information, Controller:OutdoorAir, DOAS OA CONTROLLER, Maximum Outdoor Air Flow Rate [m3/s], 3.35185",
        ],
    )
    _write_eio_fixture(
        tmp_path,
        "shenzhen__vrf",
        [
            "Component Sizing Information, AirConditioner:VariableRefrigerantFlow, SHENZHEN VRF HEAT PUMP, Design Size Rated Total Cooling Capacity (gross) [W], 480000.0",
            "Component Sizing Information, AirConditioner:VariableRefrigerantFlow, SHENZHEN VRF HEAT PUMP, Design Size Rated Total Heating Capacity [W], 410000.0",
            "Component Sizing Information, Controller:OutdoorAir, DOAS OA CONTROLLER, Maximum Outdoor Air Flow Rate [m3/s], 3.35185",
        ],
    )
    _write_eio_fixture(
        tmp_path,
        "tianjin__fcu_doas",
        [
            "Component Sizing Information, Chiller:Electric:EIR, MAIN CHILLER, Design Size Reference Capacity [W], 604257.71308",
            "Component Sizing Information, Boiler:HotWater, MAIN BOILER, Design Size Nominal Capacity [W], 322944.49155",
            "Component Sizing Information, Controller:OutdoorAir, DOAS OA CONTROLLER, Maximum Outdoor Air Flow Rate [m3/s], 3.35185",
        ],
    )
    _write_eio_fixture(
        tmp_path,
        "shenzhen__fcu_doas",
        [
            "Component Sizing Information, Chiller:Electric:EIR, MAIN CHILLER, Design Size Reference Capacity [W], 420000.0",
            "Component Sizing Information, Boiler:HotWater, MAIN BOILER, Design Size Nominal Capacity [W], 95000.0",
            "Component Sizing Information, Controller:OutdoorAir, DOAS OA CONTROLLER, Maximum Outdoor Air Flow Rate [m3/s], 3.35185",
        ],
    )


def test_write_report_data_outputs_expected_csvs(monkeypatch, tmp_path: Path) -> None:
    _patch_report_paths(monkeypatch, tmp_path)
    _seed_report_fixtures(tmp_path)

    output_root = tmp_path / "report"
    outputs = report_data.write_report_data(
        output_root=output_root,
        city_ids=("tianjin", "shenzhen"),
    )

    assert [path.name for path in outputs] == [
        "report_ideal_loads_comparison.csv",
        "report_system_energy_comparison.csv",
        "report_equipment_summary.csv",
        "report_case_matrix.csv",
    ]

    with (output_root / "report_ideal_loads_comparison.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["case_id"] == "tianjin__ideal_loads"
    assert rows[0]["annual_total_load_kwh"] == "808914.624"

    with (output_root / "report_equipment_summary.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        equipment_rows = list(csv.DictReader(handle))
    assert len(equipment_rows) == 4
    assert equipment_rows[0]["design_cooling_capacity_kw"] == "589.118"
    assert equipment_rows[1]["system"] == "fcu_doas"


def test_build_report_figures_writes_svg_files(monkeypatch, tmp_path: Path) -> None:
    _patch_report_paths(monkeypatch, tmp_path)
    _seed_report_fixtures(tmp_path)

    output_root = tmp_path / "plots"
    outputs = report_plots.build_report_figures(
        output_root=output_root,
        city_ids=("tianjin", "shenzhen"),
    )

    assert len(outputs) == 6
    for path in outputs:
        assert path.exists()
        assert path.suffix == ".svg"
        assert "<svg" in path.read_text(encoding="utf-8")


def test_build_report_figures_supports_png_output(monkeypatch, tmp_path: Path) -> None:
    _patch_report_paths(monkeypatch, tmp_path)
    _seed_report_fixtures(tmp_path)

    output_root = tmp_path / "plots_png"
    outputs = report_plots.build_report_figures(
        output_root=output_root,
        city_ids=("tianjin", "shenzhen"),
        file_format="png",
    )

    assert len(outputs) == 6
    for path in outputs:
        assert path.exists()
        assert path.suffix == ".png"
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
