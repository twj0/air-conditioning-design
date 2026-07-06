# Ref: docs/个性化设计-约束边界与方向一计划.md §三 阶段1
from __future__ import annotations

import csv
from pathlib import Path

from air_conditioning_design.analysis import suitability


def _write(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _seed(tmp_path: Path) -> None:
    proc = tmp_path / "processed"
    proc.mkdir(parents=True, exist_ok=True)
    cities = [("shenyang", "Severe Cold"), ("shenzhen", "Hot Summer Warm Winter")]
    _write(proc / "report_ideal_loads_comparison.csv",
           ["case_id", "city", "city_name", "climate_zone", "climate_zone_label", "system",
            "system_label", "peak_cooling_load_kw", "peak_cooling_load_per_m2_w_m2",
            "annual_cooling_load_kwh", "annual_heating_load_kwh", "annual_total_load_kwh",
            "annual_total_load_per_m2_kwh_m2"],
           [{"case_id": f"{c}__ideal_loads", "city": c, "city_name": c, "climate_zone": cz,
             "climate_zone_label": cz, "system": "ideal_loads", "system_label": "Ideal Loads",
             "peak_cooling_load_kw": "100", "peak_cooling_load_per_m2_w_m2": "110",
             "annual_cooling_load_kwh": cool, "annual_heating_load_kwh": heat,
             "annual_total_load_kwh": str(cool + heat), "annual_total_load_per_m2_kwh_m2": "100"}
            for c, cz, cool, heat in
            [("shenyang", "Severe Cold", 70000, 260000), ("shenzhen", "Hot Summer Warm Winter", 280000, 40000)]])

    energy_rows, equip_rows = [], []
    for c in ("shenyang", "shenzhen"):
        for sys, elec, gas, cool, heat in [("vrf", 60000, 0, 53, 53),
                                            ("fcu_doas", 6000, 80000, 76, 62)]:
            energy_rows.append({"case_id": f"{c}__{sys}", "city": c, "city_name": c,
                                "climate_zone": "x", "climate_zone_label": "x",
                                "system": sys, "system_label": sys,
                                "annual_hvac_electricity_kwh": str(elec),
                                "annual_hvac_electricity_per_m2_kwh_m2": "10",
                                "annual_hvac_natural_gas_kwh": str(gas),
                                "annual_hvac_natural_gas_per_m2_kwh_m2": "10",
                                "terminal_count": "15", "plant_loop_count": "2",
                                "design_cooling_equipment_name": "x",
                                "design_cooling_capacity_kw": str(cool),
                                "design_heating_equipment_name": "x",
                                "design_heating_capacity_kw": str(heat),
                                "outdoor_air_rate_m3_s": "2.014",
                                "outdoor_air_rate_m3_h": "7250"})
            equip_rows.append({**energy_rows[-1]})
    _write(proc / "report_system_energy_comparison.csv", list(energy_rows[0].keys()), energy_rows)
    _write(proc / "report_equipment_summary.csv", list(equip_rows[0].keys()), equip_rows)

    # Synthetic raw eplusout for peak cooling/heating/latent components.
    for c in ("shenyang", "shenzhen"):
        raw = tmp_path / "raw" / f"{c}__ideal_loads"
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "eplusout.csv").write_text(
            "Date/Time,Zone Ideal Loads Supply Air Total Cooling Rate [W](Hourly),"
            "Zone Ideal Loads Supply Air Sensible Cooling Rate [W](Hourly),"
            "Zone Ideal Loads Supply Air Sensible Heating Rate [W](Hourly)\n"
            "1,80000,50000,0\n2,60000,40000,95000\n", encoding="utf-8")


def _patch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(suitability, "REPORT_IDEAL_LOADS_PATH", tmp_path / "processed" / "report_ideal_loads_comparison.csv")
    monkeypatch.setattr(suitability, "REPORT_SYSTEM_ENERGY_PATH", tmp_path / "processed" / "report_system_energy_comparison.csv")
    monkeypatch.setattr(suitability, "REPORT_EQUIPMENT_SUMMARY_PATH", tmp_path / "processed" / "report_equipment_summary.csv")
    monkeypatch.setattr(suitability, "RESULTS_RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(suitability, "RESULTS_PROCESSED_ROOT", tmp_path / "processed")
    monkeypatch.setattr(suitability, "CITIES", ["shenyang", "shenzhen"])


def test_compute_scores_shape_and_ranges(monkeypatch, tmp_path: Path) -> None:
    _seed(tmp_path)
    _patch(monkeypatch, tmp_path)
    rows = suitability.compute_scores()
    assert len(rows) == 4  # 2 cities x 2 systems
    for r in rows:
        for d in ("D1", "D2", "D3", "D4", "D5", "D6", "total"):
            assert 0.0 <= r[d] <= 100.0
        assert abs(r["total"] - sum(r[d] for d in ("D1", "D2", "D3", "D4", "D5", "D6")) / 6.0) < 1e-6


def test_dimension_properties(monkeypatch, tmp_path: Path) -> None:
    _seed(tmp_path)
    _patch(monkeypatch, tmp_path)
    rows = {(r["city"], r["system"]): r for r in suitability.compute_scores()}
    for (city, system), r in rows.items():
        if system == "fcu_doas":
            assert r["D1"] == 100.0   # FCU independently sized
            assert r["D5"] == 100.0   # boiler stable
        else:
            assert r["D1"] < 100.0    # VRF penalized by load asymmetry
            assert r["D5"] < 100.0    # VRF heat-pump cold penalty


def test_write_scores(monkeypatch, tmp_path: Path) -> None:
    _seed(tmp_path)
    _patch(monkeypatch, tmp_path)
    path = suitability.write_scores()
    assert path.exists()
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {"D1", "D2", "D3", "D4", "D5", "D6", "total"} <= set(rows[0].keys())
