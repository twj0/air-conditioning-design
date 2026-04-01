# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-VRF-CQ-001)
from pathlib import Path

from air_conditioning_design.analysis.vrf_summary import build_vrf_summary


def test_build_vrf_summary_returns_chongqing_case_metadata(tmp_path: Path) -> None:
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

    idf_path = tmp_path / "chongqing__vrf.idf"
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

    summary = build_vrf_summary(
        "chongqing", tmp_path, idf_path=idf_path, floor_area_m2=100.0
    )

    assert summary["case_id"] == "chongqing__vrf"
    assert summary["city"] == "chongqing"
    assert summary["system"] == "vrf"
    assert summary["annual_hvac_electricity"] == 3.0
    assert summary["annual_hvac_electricity_per_m2"] == 0.03
    assert summary["vrf_terminal_count"] == 2
