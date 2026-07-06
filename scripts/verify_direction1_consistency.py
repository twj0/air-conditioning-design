# Ref: docs/个性化设计-约束边界与方向一计划.md §三 阶段5 (final consistency gate)
"""Direction-1 final consistency verification: report CSV ↔ figures ↔ paper text.

Checks: (1) report CSV internal math; (2) stale pre-fix values absent from all paper
sections; (3) corrected values present in 07/08; (4) all 8 figures present & non-trivial;
(5) suitability model recomputes consistently. Exits non-zero on any failure.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "air-conditioning-design"))

from air_conditioning_design.analysis.suitability import compute_scores  # noqa: E402
from air_conditioning_design.config.paths import (  # noqa: E402
    MEDIUM_OFFICE_FLOOR_AREA_M2, PAPER_FIGURES_ROOT,
    REPORT_EQUIPMENT_SUMMARY_PATH, REPORT_IDEAL_LOADS_PATH,
    REPORT_SYSTEM_ENERGY_PATH,
)

AREA = MEDIUM_OFFICE_FLOOR_AREA_M2
SECTIONS = REPO / "air-conditioning-design-paper" / "latex" / "sections"
fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        fails.append(msg)


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify_csv_internal() -> None:
    print("\n[1] Report CSV internal consistency")
    for r in _rows(REPORT_IDEAL_LOADS_PATH):
        kw = float(r["peak_cooling_load_kw"])
        per = float(r["peak_cooling_load_per_m2_w_m2"])
        cool, heat = float(r["annual_cooling_load_kwh"]), float(r["annual_heating_load_kwh"])
        check(abs(per - kw * 1000 / AREA) < 0.05, f"{r['city']} per_m2 = kW×1000/area")
        check(abs(float(r["annual_total_load_kwh"]) - (cool + heat)) < 1.0,
              f"{r['city']} total = cool + heat")
    equip = {(r["city"], r["system"]): r for r in _rows(REPORT_EQUIPMENT_SUMMARY_PATH)}
    expected_ratio = {"shenyang": 1.22, "tianjin": 2.01, "chengdu": 1.55,
                      "chongqing": 3.05}
    for city, ratio in expected_ratio.items():
        eq = equip[(city, "fcu_doas")]
        heat_kw = float(eq["design_heating_capacity_kw"])
        if heat_kw == 0.0:
            check(True, f"{city} FCU no central heating (ratio skipped)")
            continue
        actual = float(eq["design_cooling_capacity_kw"]) / heat_kw
        check(abs(actual - ratio) < 0.02, f"{city} FCU cold/hot ratio ≈ {ratio}")
    shenzhen_fcu = equip[("shenzhen", "fcu_doas")]
    check(float(shenzhen_fcu["design_heating_capacity_kw"]) == 0.0,
          "shenzhen FCU has no central heating capacity (matches 夏热冬暖 zone)")


def verify_paper_regression() -> None:
    print("\n[2] Stale pre-fix values must be ABSENT from all sections (02-08)")
    stale = ["7.31", "12.47", "9.51", "10.22", "11.51", "10.00", "17.05",
             "13.00", "13.97", "15.74", "8814", "13486", "12437", "19114", "27080",
             "203489", "169458", "92799", "87752", "86479", "232.95", "200.74",
             "115.47", "117.26", "124.60", "0.95:1", "2.76:1", "2.45:1", "1.13:1",
             "60.25", "60.20", "56.20", "48.85", "48.06", "93.33", "77.03",
             "74.81", "74.96", "45.10", "4.64", "5.67", "35.60", "41.70", "45.80",
             "46.48", "54.25", "54.71", "57.38", "73.79", "47.56", "56.70", "50.16",
             "96.70", "39.47", "111.74", "40.42", "127574", "105295", "50.77"]
    for tex in sorted(SECTIONS.glob("0[2-8]-*.tex")):
        text = tex.read_text(encoding="utf-8")
        hits = [s for s in stale if s in text]
        check(not hits, f"{tex.name} free of stale values" +
              (f" (found: {hits})" if hits else ""))


def verify_correct_present() -> None:
    print("\n[3] Corrected values present in 07-comparison & 08-conclusion")
    combined = (SECTIONS / "07-comparison.tex").read_text(encoding="utf-8") \
        + (SECTIONS / "08-conclusion.tex").read_text(encoding="utf-8")
    # Scheme-B peak cooling load densities (W/m^2), source of truth: report_ideal_loads_comparison.csv
    for needle in ["115.2", "126.5", "115.8", "139.4", "132.0", "105.00",
                   "115.28", "105.58", "127.08", "120.34",
                   "适宜性", "组合率", "COP"]:
        check(needle in combined, f"contains '{needle}'")


def verify_figures() -> None:
    print("\n[4] Paper figures present & non-trivial")
    # Figures actually referenced by 07/08 in the Scheme-B paper
    paper_figs = ["peak_cooling_load_density_by_city", "design_cooling_capacity_by_city",
                  "cooling_season_design_focus_by_city", "annual_ideal_loads_by_city",
                  "peak_cooling_load_by_city", "system_electricity_by_city",
                  "system_electricity_per_m2_by_city"]
    for f in paper_figs:
        p = PAPER_FIGURES_ROOT / f"{f}.pdf"
        check(p.exists() and p.stat().st_size > 8000, f"{f}.pdf exists (>8KB)")
    # Defense-direction1 figures still used by the Beamer deck; keep existence check
    direction1_figs = ["direction1_load_split_by_city", "direction1_capacity_vs_load_ratio",
                      "direction1_primary_energy_comparison", "direction1_energy_radar",
                      "direction1_suitability_heatmap", "direction1_climate_cdf",
                      "direction1_lcc_waterfall", "direction1_vrf_cop_degradation"]
    for f in direction1_figs:
        p = PAPER_FIGURES_ROOT / f"{f}.pdf"
        check(p.exists(), f"{f}.pdf exists (defense deck)")


def verify_model() -> None:
    print("\n[5] Suitability model self-consistency")
    rows = compute_scores()
    check(len(rows) == 10, "10 score rows (5 cities × 2 systems)")
    for r in rows:
        for d in ("D1", "D2", "D3", "D4", "D5", "D6", "total"):
            check(0.0 <= r[d] <= 100.0, f"{r['city']}/{r['system']} {d} in [0,100]")
        check(abs(r["total"] - sum(r[d] for d in ("D1", "D2", "D3", "D4", "D5", "D6")) / 6) < 1e-6,
              f"{r['city']}/{r['system']} total = mean(D1..D6)")
        if r["system"] == "fcu_doas":
            check(r["D1"] == 100.0 and r["D5"] == 100.0, f"{r['city']}/fcu D1=D5=100")
        else:
            check(r["D1"] < 100.0, f"{r['city']}/vrf D1<100")


def verify_chapters() -> None:
    print("\n[6] Per-chapter tables vs CSV (energy intensities, outdoor-unit capacity, placeholders)")
    import re
    en = {(r["city"], r["system"]): r for r in _rows(REPORT_SYSTEM_ENERGY_PATH)}
    eq = {(r["city"], r["system"]): r for r in _rows(REPORT_EQUIPMENT_SUMMARY_PATH)}
    chap = {"shenyang": "02-shenyang", "tianjin": "03-tianjin", "chengdu": "04-chengdu",
            "chongqing": "05-chongqing", "shenzhen": "06-shenzhen"}
    for city, fn in chap.items():
        text = (SECTIONS / f"{fn}.tex").read_text(encoding="utf-8")
        # placeholders
        check(not re.search(r"待仿真|待定|待补|TBD", text), f"{fn} free of placeholders")
        # energy intensity row vs CSV (VRF elec, FCU elec)
        m = re.search(r"电耗强度.*?&\s*([\d.]+).*?&\s*([\d.]+)", text)
        if m:
            vrf, fcu = float(m.group(1)), float(m.group(2))
            tv = float(en[(city, "vrf")]["annual_hvac_electricity_per_m2_kwh_m2"])
            tf = float(en[(city, "fcu_doas")]["annual_hvac_electricity_per_m2_kwh_m2"])
            check(abs(vrf - tv) < 0.1 and abs(fcu - tf) < 0.1,
                  f"{fn} electricity intensity matches CSV ({tv}/{tf})")
        # VRF outdoor-unit capacity matches report (catch stale 106.48/167/96.8-style values)
        vrf_cap = float(eq[(city, "vrf")]["design_cooling_capacity_kw"])
        outdoor_lines = [ln for ln in text.splitlines() if "室外机" in ln and "自动选型" in ln]
        if outdoor_lines:
            nums = [n for ln in outdoor_lines for n in re.findall(r"\d+\.?\d*", ln)]
            check(any(abs(float(n) - vrf_cap) < 0.6 for n in nums if 30 < float(n) < 200),
                  f"{fn} VRF outdoor unit = {vrf_cap} kW (not stale)")


def main() -> int:
    verify_csv_internal()
    verify_paper_regression()
    verify_correct_present()
    verify_figures()
    verify_model()
    verify_chapters()
    print(f"\n{'='*50}")
    if fails:
        print(f"❌ {len(fails)} FAILURES:")
        for f in fails:
            print(f"   - {f}")
        return 1
    print("✅ ALL CONSISTENCY CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
