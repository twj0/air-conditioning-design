# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
from air_conditioning_design.analysis.ideal_loads_summary import build_ideal_loads_summary


def test_build_ideal_loads_summary_returns_shenzhen_case_metadata(tmp_path) -> None:
    csv_path = tmp_path / "eplusout.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Date/Time,Core_bottom:Zone Ideal Loads Supply Air Sensible Cooling Rate [W](Hourly),Core_bottom:Zone Ideal Loads Supply Air Sensible Heating Rate [W](Hourly)",
                "01/01  01:00:00,1000,0",
                "01/01  02:00:00,2500,500",
            ]
        ),
        encoding="utf-8",
    )

    summary = build_ideal_loads_summary("shenzhen", tmp_path, floor_area_m2=100.0)

    assert summary["case_id"] == "shenzhen__ideal_loads"
    assert summary["city"] == "shenzhen"
    assert summary["system"] == "ideal_loads"
    assert summary["peak_cooling_load"] == 2.5
    assert summary["annual_cooling_load"] == 3.5
    assert summary["annual_heating_load"] == 0.5
