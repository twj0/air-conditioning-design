# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from pathlib import Path

from air_conditioning_design.analysis.tianjin_summary import build_tianjin_summary


def test_build_tianjin_summary_returns_required_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "eplusout.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Date/Time,Core_bottom:Zone Ideal Loads Supply Air Sensible Cooling Rate [W](Hourly),Core_bottom:Zone Ideal Loads Supply Air Sensible Heating Rate [W](Hourly)",
                "01/01  01:00:00,1000,0",
                "01/01  02:00:00,2000,500",
            ]
        ),
        encoding="utf-8",
    )

    summary = build_tianjin_summary(tmp_path, floor_area_m2=100.0)

    assert {
        "case_id",
        "city",
        "system",
        "peak_cooling_load",
        "peak_cooling_load_per_m2",
        "annual_cooling_load",
        "annual_heating_load",
    } <= set(summary.keys())
    assert summary["peak_cooling_load"] == 2.0
    assert summary["annual_cooling_load"] == 3.0
    assert summary["annual_heating_load"] == 0.5
