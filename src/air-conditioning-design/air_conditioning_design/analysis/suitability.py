# Ref: docs/个性化设计-约束边界与方向一计划.md §三 阶段1
"""Direction-1 climate-differentiated system suitability scoring model (6 dimensions).

Methodology and data sources are documented in
docs/个性化设计-约束边界与方向一计划.md (§三 阶段1, §五 经济性数据).
Scores are reproducible from results/processed/report_*.csv + results/raw + the
constants below; nothing is hand-entered.
"""
from __future__ import annotations

import csv
from pathlib import Path

from air_conditioning_design.config.paths import (
    MEDIUM_OFFICE_FLOOR_AREA_M2,
    REPORT_EQUIPMENT_SUMMARY_PATH,
    REPORT_IDEAL_LOADS_PATH,
    REPORT_SYSTEM_ENERGY_PATH,
    RESULTS_PROCESSED_ROOT,
    RESULTS_RAW_ROOT,
)

FLOOR_AREA_M2 = MEDIUM_OFFICE_FLOOR_AREA_M2
LIFETIME_YEARS = 15

# Primary-energy factors per GB/T 51366-2019 (national-average grid).
PRIMARY_FACTOR_ELEC = 2.46  # kWh primary per kWh electricity
PRIMARY_FACTOR_GAS = 1.04   # kWh primary per kWh fuel gas
GAS_HEAT_VALUE_KWH_PER_M3 = 9.87

# 2024 commercial tariffs (元). Sources cited in plan doc §5.1 / §5.2.
ELECTRICITY_PRICE = {"shenyang": 0.67, "tianjin": 0.68, "chengdu": 0.53,
                     "chongqing": 0.70, "shenzhen": 0.79}        # 元/kWh
GAS_PRICE = {"shenyang": 3.20, "tianjin": 3.45, "chengdu": 2.70,
             "chongqing": 3.06, "shenzhen": 3.80}                # 元/m³ (non-heating)
WINTER_DESIGN_TEMP = {"shenyang": -22.0, "tianjin": -9.6, "chengdu": 1.3,
                      "chongqing": 3.7, "shenzhen": 8.4}         # °C (CSWD design day)

# Equipment unit prices (元). 陆耀庆手册 + 主流厂家样本均值, plan doc §5.4.
UNIT_PRICE = {"vrf_outdoor_per_kw": 1000, "vrf_indoor_per_unit": 500,
              "fcu_per_unit": 1200, "chiller_per_kw": 750,
              "boiler_per_kw": 400, "doas_per_m3h": 5}

# Equipment efficiency (literature). GB 21455-2019 (VRF IPLV/SCOP), GB 19577 (chiller COP),
# gas boiler thermal efficiency ~0.92. SCOP degrades sharply in cold climates (heat-pump
# low-temperature penalty). D2 uses these (not Q/Energy) to avoid mixing ideal_loads demand
# with system consumption, which do not reconcile (DOAS heat recovery, scheduling differences).
VRF_COOL_COP = 3.8
VRF_HEAT_SCOP = {"shenyang": 2.0, "tianjin": 2.8, "chengdu": 3.5,
                 "chongqing": 3.5, "shenzhen": 4.2}   # seasonal COP, climate-dependent
FCU_CHILLER_COP = 5.5
BOILER_EFFICIENCY = 0.92

CITIES = ["shenyang", "tianjin", "chengdu", "chongqing", "shenzhen"]
SYSTEMS = ["vrf", "fcu_doas"]
SYSTEM_LABEL = {"vrf": "多联机+独立新风", "fcu_doas": "风机盘管+独立新风"}
CITY_LABEL = {"shenyang": "沈阳\n严寒", "tianjin": "天津\n寒冷",
              "chengdu": "成都\n夏热冬冷", "chongqing": "重庆\n夏热冬冷",
              "shenzhen": "深圳\n夏热冬暖"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _peak_cooling_components_w(city: str) -> tuple[float, float]:
    """Peak total & sensible cooling rate (W) summed across zones, from raw eplusout.csv."""
    csv_path = RESULTS_RAW_ROOT / f"{city}__ideal_loads" / "eplusout.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        total_idx = [i for i, h in enumerate(headers)
                     if "supply air total cooling rate" in h.lower()]
        sens_idx = [i for i, h in enumerate(headers)
                    if "supply air sensible cooling rate" in h.lower()
                    and "total" not in h.lower()]
        peak_total = peak_sens = 0.0
        for row in reader:
            t = sum(float(row[i]) for i in total_idx if row[i])
            s = sum(float(row[i]) for i in sens_idx if row[i])
            peak_total = max(peak_total, t)
            peak_sens = max(peak_sens, s)
    return peak_total, peak_sens


def _load_inputs() -> dict:
    ideal = {r["city"]: r for r in _read_csv(REPORT_IDEAL_LOADS_PATH)}
    energy = {(r["city"], r["system"]): r for r in _read_csv(REPORT_SYSTEM_ENERGY_PATH)}
    equip = {(r["city"], r["system"]): r for r in _read_csv(REPORT_EQUIPMENT_SUMMARY_PATH)}
    return {"ideal": ideal, "energy": energy, "equip": equip}


def _raw_metrics(inputs: dict) -> list[dict]:
    """Compute the physical/raw metric for every (city, system) cell, pre-normalization."""
    rows = []
    for city in CITIES:
        il = inputs["ideal"][city]
        q_cool = float(il["annual_cooling_load_kwh"])
        q_heat = float(il["annual_heating_load_kwh"])
        asymmetry = abs(q_cool - q_heat) / (q_cool + q_heat)
        f_cool = q_cool / (q_cool + q_heat)
        f_heat = 1.0 - f_cool
        # D2: climate-weighted primary-energy efficiency from literature equipment values.
        vrf_eff = (f_cool * VRF_COOL_COP / PRIMARY_FACTOR_ELEC
                   + f_heat * VRF_HEAT_SCOP[city] / PRIMARY_FACTOR_ELEC)
        fcu_eff = (f_cool * FCU_CHILLER_COP / PRIMARY_FACTOR_ELEC
                   + f_heat * BOILER_EFFICIENCY / PRIMARY_FACTOR_GAS)
        peak_total, peak_sens = _peak_cooling_components_w(city)
        latent_frac = max(0.0, (peak_total - peak_sens) / peak_total) if peak_total > 0 else 0.0
        t_winter = WINTER_DESIGN_TEMP[city]
        for system in SYSTEMS:
            en = inputs["energy"][(city, system)]
            eq = inputs["equip"][(city, system)]
            elec = float(en["annual_hvac_electricity_kwh"])
            gas = float(en["annual_hvac_natural_gas_kwh"])
            e_primary = elec * PRIMARY_FACTOR_ELEC + gas * PRIMARY_FACTOR_GAS
            eff_primary = vrf_eff if system == "vrf" else fcu_eff
            e_primary_per_m2 = e_primary / FLOOR_AREA_M2
            cool_cap = float(eq["design_cooling_capacity_kw"])
            heat_cap = float(eq["design_heating_capacity_kw"])
            oa_m3h = float(eq["outdoor_air_rate_m3_h"])
            terminals = int(float(eq["terminal_count"]))
            # Initial investment (元)
            if system == "vrf":
                initial = (cool_cap * UNIT_PRICE["vrf_outdoor_per_kw"]
                           + terminals * UNIT_PRICE["vrf_indoor_per_unit"])
            else:
                initial = (cool_cap * UNIT_PRICE["chiller_per_kw"]
                           + heat_cap * UNIT_PRICE["boiler_per_kw"]
                           + terminals * UNIT_PRICE["fcu_per_unit"])
            initial += oa_m3h * UNIT_PRICE["doas_per_m3h"]  # shared DOAS
            # Annual operating cost (元)
            gas_m3 = gas / GAS_HEAT_VALUE_KWH_PER_M3
            operating = elec * ELECTRICITY_PRICE[city] + gas_m3 * GAS_PRICE[city]
            lcc = initial + LIFETIME_YEARS * operating
            rows.append({
                "city": city, "system": system,
                "asymmetry": asymmetry, "eff_primary": eff_primary,
                "e_primary_per_m2": e_primary_per_m2, "latent_frac": latent_frac,
                "t_winter": t_winter, "initial_cost": initial,
                "annual_operating": operating, "lcc": lcc,
            })
    return rows


def _norm(values: list[float], higher_better: bool) -> list[float]:
    lo, hi = min(values), max(values)
    span = hi - lo if hi > lo else 1.0
    return [100.0 * (v - lo) / span if higher_better else 100.0 * (hi - v) / span
            for v in values]


def compute_scores() -> list[dict]:
    """Return list of dicts with raw metrics, D1-D6 normalized scores, and weighted total."""
    inputs = _load_inputs()
    rows = _raw_metrics(inputs)

    eff = _norm([r["eff_primary"] for r in rows], higher_better=True)
    eper = _norm([r["e_primary_per_m2"] for r in rows], higher_better=False)
    lcc = _norm([r["lcc"] for r in rows], higher_better=False)

    for i, r in enumerate(rows):
        asym = r["asymmetry"]
        # D1 capacity-load match: FCU independently sized (100); VRF symmetric unit, penalized by asymmetry.
        d1 = 100.0 if r["system"] == "fcu_doas" else 100.0 - 30.0 * asym
        d2 = eff[i]                      # primary-energy efficiency (literature-weighted), higher better
        d3 = eper[i]                      # primary-energy intensity, lower better
        d4 = 100.0 - 50.0 * r["latent_frac"]   # dehumidification burden, higher latent harder
        # D5 low-temp heating stability: FCU boiler stable (100); VRF heat-pump COP degrades below 10°C.
        if r["system"] == "fcu_doas":
            d5 = 100.0
        else:
            d5 = max(30.0, 100.0 - 2.0 * max(0.0, 10.0 - r["t_winter"]))
        d6 = lcc[i]                       # life-cycle cost, lower better
        r.update({"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6,
                  "total": sum([d1, d2, d3, d4, d5, d6]) / 6.0})
    return rows


SCORE_FIELDS = ["city", "system", "D1", "D2", "D3", "D4", "D5", "D6", "total",
                "asymmetry", "eff_primary", "e_primary_per_m2", "latent_frac",
                "t_winter", "initial_cost", "annual_operating", "lcc"]


def write_scores(output_path: Path | None = None) -> Path:
    rows = compute_scores()
    target = output_path or (RESULTS_PROCESSED_ROOT / "suitability_scores.csv")
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{k: round(v, 3) if isinstance(v, float) else v
                           for k, v in r.items()} for r in rows])
    return target


if __name__ == "__main__":
    path = write_scores()
    print(f"Wrote {path}")
    for r in compute_scores():
        print(f"{r['city']:10s} {SYSTEM_LABEL[r['system']]:9s} "
              f"D1={r['D1']:5.1f} D2={r['D2']:5.1f} D3={r['D3']:5.1f} "
              f"D4={r['D4']:5.1f} D5={r['D5']:5.1f} D6={r['D6']:5.1f} "
              f"total={r['total']:5.1f}")
