# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-FCU-001)
from pathlib import Path

from air_conditioning_design.analysis.tianjin_fcu_doas_summary import (
    build_tianjin_fcu_doas_summary,
)


def test_build_tianjin_fcu_doas_summary_returns_required_columns(tmp_path: Path) -> None:
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

    idf_path = tmp_path / "tianjin__fcu_doas.idf"
    idf_path.write_text(
        "\n".join(
            [
                "ZoneHVAC:FourPipeFanCoil,",
                "  FCU1;",
                "",
                "ZoneHVAC:FourPipeFanCoil,",
                "  FCU2;",
                "",
                "PlantLoop,",
                "  Loop1;",
                "",
                "PlantLoop,",
                "  Loop2;",
            ]
        ),
        encoding="utf-8",
    )

    summary = build_tianjin_fcu_doas_summary(
        tmp_path, idf_path=idf_path, floor_area_m2=100.0
    )

    assert {
        "case_id",
        "city",
        "system",
        "annual_hvac_electricity",
        "annual_hvac_electricity_per_m2",
        "fcu_terminal_count",
        "plant_loop_count",
    } <= set(summary.keys())
    assert summary["annual_hvac_electricity"] == 3.0
    assert summary["annual_hvac_electricity_per_m2"] == 0.03
    assert summary["fcu_terminal_count"] == 2
    assert summary["plant_loop_count"] == 2
