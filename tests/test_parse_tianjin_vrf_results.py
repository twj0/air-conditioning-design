# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-VRF-001)
from pathlib import Path

from air_conditioning_design.analysis.tianjin_vrf_summary import build_tianjin_vrf_summary


def test_build_tianjin_vrf_summary_returns_required_columns(tmp_path: Path) -> None:
    meter_csv_path = tmp_path / "eplusmtr.csv"
    meter_csv_path.write_text(
        "\n".join(
            [
                "Date/Time,Electricity:HVAC [J](Monthly),Fans:Electricity [J](Monthly)",
                "01/31  24:00:00,3600000,100000",
                "02/28  24:00:00,7200000,100000",
            ]
        ),
        encoding="utf-8",
    )

    idf_path = tmp_path / "tianjin__vrf.idf"
    idf_path.write_text(
        "\n".join(
            [
                "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow,",
                "  TU1;",
                "",
                "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow,",
                "  TU2;",
            ]
        ),
        encoding="utf-8",
    )

    summary = build_tianjin_vrf_summary(tmp_path, idf_path=idf_path, floor_area_m2=100.0)

    assert {
        "case_id",
        "city",
        "system",
        "annual_hvac_electricity",
        "annual_hvac_electricity_per_m2",
        "vrf_terminal_count",
    } <= set(summary.keys())
    assert summary["annual_hvac_electricity"] == 3.0
    assert summary["annual_hvac_electricity_per_m2"] == 0.03
    assert summary["vrf_terminal_count"] == 2
