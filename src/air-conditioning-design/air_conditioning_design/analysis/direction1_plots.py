# Ref: docs/个性化设计-约束边界与方向一计划.md §三 阶段3 (F1, F2, F5)
"""Direction-1 figures: cooling/heating load split (F1), capacity-vs-load ratio (F2),
and 6-dimension suitability heatmap (F5). Style matches analysis/report_plots.py.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

from air_conditioning_design.analysis.report_data import (
    DESIGN_PEAK_COOLING_LOAD_KW,
    build_ideal_loads_comparison,
)
from air_conditioning_design.analysis.suitability import (
    CITIES, CITY_LABEL, SYSTEM_LABEL, compute_scores,
)
from air_conditioning_design.config.paths import PAPER_FIGURES_ROOT, REPORT_EQUIPMENT_SUMMARY_PATH

import csv

COOLING_COLOR = "#d66a35"
HEATING_COLOR = "#4e8c63"
FCU_COLOR = "#24577a"
VRF_COLOR = "#d66a35"
LOAD_COLOR = "#888888"
ELEC_PRIMARY_COLOR = "#4a90d9"   # electricity (primary-adjusted) component
GAS_PRIMARY_COLOR = "#e0992e"    # gas (primary-adjusted) component
PRIMARY_FACTOR_ELEC = 2.46
PRIMARY_FACTOR_GAS = 1.04

# Distinct colors for the 5 climate lines (cool→warm gradient).
CITY_LINE_COLORS = {
    "shenyang": "#3b6fb5", "tianjin": "#5fa8d3", "chengdu": "#7fb069",
    "chongqing": "#e8a33d", "shenzhen": "#c0392b",
}
CITY_SHORT_CN = {"shenyang": "沈阳", "tianjin": "天津", "chengdu": "成都", "chongqing": "重庆", "shenzhen": "深圳"}


def _set_chinese_style() -> None:
    names = {font.name for font in font_manager.fontManager.ttflist}
    font = next(
        (name for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC") if name in names),
        "DejaVu Sans",
    )
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [font, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
        }
    )


def _weather_series(city: str) -> tuple[list[float], list[float]]:
    """Outdoor dry-bulb (°C) and enthalpy (kJ/kg) hourly series from the city EPW."""
    import math
    from air_conditioning_design.weather.catalog import load_weather_manifest
    epw_path = Path(load_weather_manifest(city)["epw_path"])
    dry, enth = [], []
    with epw_path.open(encoding="utf-8", errors="ignore") as handle:
        for line_number, line in enumerate(handle):
            if line_number < 8:
                continue
            parts = line.split(",")
            if len(parts) < 10 or not parts[6].strip().lstrip("-").replace(".", "").isdigit():
                continue
            t_db = float(parts[6])
            rh = min(100.0, max(0.0, float(parts[8]) if parts[8] else 50.0))
            p_pa = float(parts[9]) if parts[9] else 101325.0
            if p_pa < 50000.0 or p_pa > 120000.0:
                p_pa = 101325.0
            p_kpa = p_pa / 1000.0
            psat = 0.61078 * math.exp(17.27 * t_db / (t_db + 237.3))  # kPa
            pv = max(0.0, min(psat, rh / 100.0 * psat))
            w = 0.62198 * pv / max(0.1, p_kpa - pv)
            h = 1.006 * t_db + w * (2501 + 1.86 * t_db)
            dry.append(t_db)
            enth.append(h)
    return dry, enth


def _read_system_energy() -> dict:
    from air_conditioning_design.config.paths import REPORT_SYSTEM_ENERGY_PATH
    with REPORT_SYSTEM_ENERGY_PATH.open(encoding="utf-8") as handle:
        return {(r["city"], r["system"]): r for r in csv.DictReader(handle)}


def _primary_energy_per_m2(city: str, system: str) -> tuple[float, float, float]:
    """Return (electricity_primary, gas_primary, total_primary) in kWh/m²."""
    from air_conditioning_design.config.paths import MEDIUM_OFFICE_FLOOR_AREA_M2
    en = _read_system_energy()[(city, system)]
    elec = float(en["annual_hvac_electricity_kwh"]) * PRIMARY_FACTOR_ELEC / MEDIUM_OFFICE_FLOOR_AREA_M2
    gas = float(en["annual_hvac_natural_gas_kwh"]) * PRIMARY_FACTOR_GAS / MEDIUM_OFFICE_FLOOR_AREA_M2
    return elec, gas, elec + gas


def _peak_load_ratio(city: str) -> float:
    """Peak cooling / peak heating (kW), same peak basis as equipment sizing."""
    import csv as _csv
    from air_conditioning_design.config.paths import RESULTS_RAW_ROOT
    csv_path = RESULTS_RAW_ROOT / f"{city}__ideal_loads" / "eplusout.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = _csv.reader(handle)
        headers = next(reader)
        cool_idx = [i for i, c in enumerate(headers)
                    if "supply air total cooling rate" in c.lower()]
        heat_idx = [i for i, c in enumerate(headers)
                    if "supply air sensible heating rate" in c.lower()]
        peak_cool = peak_heat = 0.0
        for row in reader:
            peak_cool = max(peak_cool, sum(float(row[i]) for i in cool_idx if row[i]))
            peak_heat = max(peak_heat, sum(float(row[i]) for i in heat_idx if row[i]))
    design_peak_cool = DESIGN_PEAK_COOLING_LOAD_KW.get(city, peak_cool / 1000.0) * 1000.0
    return design_peak_cool / peak_heat if peak_heat > 0 else 0.0


def _read_equipment() -> dict:
    with REPORT_EQUIPMENT_SUMMARY_PATH.open(encoding="utf-8") as handle:
        return {(r["city"], r["system"]): r for r in csv.DictReader(handle)}


def plot_load_split(output_root: Path, file_format: str = "pdf") -> Path:
    """F1: annual cooling vs heating load split per city (stacked bar)."""
    rows = build_ideal_loads_comparison()
    rows = [r for r in rows if r["city"] in CITIES]
    labels = [CITY_LABEL[r["city"]] for r in rows]
    cool = np.array([float(r["annual_cooling_load_kwh"]) for r in rows]) / 1e3
    heat = np.array([float(r["annual_heating_load_kwh"]) for r in rows]) / 1e3

    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    y = np.arange(len(rows))
    ax.barh(y, cool, color=COOLING_COLOR, label="年冷负荷", edgecolor="white", linewidth=0.5)
    ax.barh(y, heat, left=cool, color=HEATING_COLOR, label="年热负荷", edgecolor="white", linewidth=0.5)
    for i, (c, h) in enumerate(zip(cool, heat)):
        tot = c + h
        ax.text(c / 2, i, f"{c/tot*100:.0f}%", ha="center", va="center",
                color="white", fontsize=9, fontweight="bold")
        ax.text(c + h / 2, i, f"{h/tot*100:.0f}%", ha="center", va="center",
                color="white", fontsize=9, fontweight="bold")
        ax.text(tot, i, f" {tot:.0f} MWh", ha="left", va="center", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("全年理想冷热负荷（MWh）")
    ax.set_title("五城市全年冷热负荷结构")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    path = output_root / f"direction1_load_split_by_city.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


def plot_capacity_ratio(output_root: Path, file_format: str = "pdf") -> Path:
    """F2: FCU cold/hot capacity ratio vs peak load ratio per city (VRF = 1.0 reference)."""
    equip = _read_equipment()

    fcu_ratio, load_ratio, city_keys = [], [], []
    for city in CITIES:
        eq = equip[(city, "fcu_doas")]
        heating_capacity = float(eq["design_heating_capacity_kw"])
        fcu_ratio.append(
            float(eq["design_cooling_capacity_kw"]) / heating_capacity
            if heating_capacity > 0
            else np.nan
        )
        load_ratio.append(_peak_load_ratio(city))
        city_keys.append(city)

    x = np.arange(len(CITIES))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.axhline(1.0, color=VRF_COLOR, linestyle="--", linewidth=1.5,
               label="多联机热泵冷热对称 = 1.0")
    b1 = ax.bar(x - w / 2, fcu_ratio, w, color=FCU_COLOR,
                label="风机盘管冷水机组/锅炉容量比", edgecolor="white", linewidth=0.5)
    b2 = ax.bar(x + w / 2, load_ratio, w, color=LOAD_COLOR,
                label="峰值冷/热负荷比", edgecolor="white", linewidth=0.5)
    for bars in (b1, b2):
        for rect in bars:
            if not np.isfinite(rect.get_height()):
                ax.text(rect.get_x() + rect.get_width() / 2, 0.15,
                        "不设\n热源", ha="center", va="bottom", fontsize=8)
                continue
            ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(),
                    f"{rect.get_height():.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([CITY_LABEL[c] for c in CITIES], fontsize=8)
    ax.set_ylabel("冷/热比（制冷 ÷ 供热）")
    ax.set_title("冷热容量比与峰值负荷比的气候梯度")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    path = output_root / f"direction1_capacity_vs_load_ratio.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


_DIM_LABEL = ["D1\n容量\n匹配", "D2\n一次能源\n效率", "D3\n能耗\n强度",
              "D4\n除湿\n压力", "D5\n低温\n供热", "D6\n寿命周期\n经济性", "总分"]


def plot_suitability_heatmap(output_root: Path, file_format: str = "pdf") -> Path:
    """F5: 6-dimension suitability score heatmap (rows = city×system, cols = D1-D6+Total)."""
    rows = compute_scores()
    dims = ["D1", "D2", "D3", "D4", "D5", "D6", "total"]
    data = np.array([[r[d] for d in dims] for r in rows], dtype=float)
    row_labels = [f"{CITY_LABEL[r['city']].split(chr(10))[0]}  {SYSTEM_LABEL[r['system']]}"
                  for r in rows]

    fig, ax = plt.subplots(figsize=(9, 6.5), constrained_layout=True)
    im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(dims)))
    ax.set_xticklabels(_DIM_LABEL, fontsize=8)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels(row_labels, fontsize=8)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            txt = f"{val:.0f}"
            if j == len(dims) - 1:
                txt = f"{val:.1f}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                    color="black" if 30 < val < 75 else "white", fontweight="bold")
    ax.set_title("不同气候分区系统适宜性评分（0–100）", pad=10)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("分值（越高越适宜）")
    path = output_root / f"direction1_suitability_heatmap.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


def plot_primary_energy_comparison(output_root: Path, file_format: str = "pdf") -> Path:
    """F3: VRF vs FCU annual primary-energy intensity, stacked by electricity/gas component."""
    vrf_elec, vrf_gas, fcu_elec, fcu_gas = [], [], [], []
    for city in CITIES:
        ve, vg, _ = _primary_energy_per_m2(city, "vrf")
        fe, fg, _ = _primary_energy_per_m2(city, "fcu_doas")
        vrf_elec.append(ve); vrf_gas.append(vg)
        fcu_elec.append(fe); fcu_gas.append(fg)

    x = np.arange(len(CITIES))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    # VRF (all-electric)
    ax.bar(x - w / 2, vrf_elec, w, color=ELEC_PRIMARY_COLOR, edgecolor="white",
           linewidth=0.5, label="多联机电耗（×2.46）")
    # FCU stacked: electricity + gas
    ax.bar(x + w / 2, fcu_elec, w, color=ELEC_PRIMARY_COLOR, edgecolor="white",
           linewidth=0.5, label="风机盘管电耗（×2.46）")
    ax.bar(x + w / 2, fcu_gas, w, bottom=fcu_elec, color=GAS_PRIMARY_COLOR,
           edgecolor="white", linewidth=0.5, label="风机盘管天然气（×1.04）")
    for i in range(len(CITIES)):
        ax.text(x[i] - w / 2, vrf_elec[i], f"{vrf_elec[i]:.0f}", ha="center",
                va="bottom", fontsize=8)
        ax.text(x[i] + w / 2, fcu_elec[i] + fcu_gas[i], f"{fcu_elec[i] + fcu_gas[i]:.0f}",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([CITY_LABEL[c] for c in CITIES], fontsize=8)
    ax.set_ylabel("全年一次能源强度（kWh/m²）")
    ax.set_title("两类系统全年一次能源强度对比")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    path = output_root / f"direction1_primary_energy_comparison.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


def plot_energy_radar(output_root: Path, file_format: str = "pdf") -> Path:
    """F4: primary-energy intensity radar, 5 climate axes, VRF vs FCU polygons."""
    vrf_tot = [_primary_energy_per_m2(c, "vrf")[2] for c in CITIES]
    fcu_tot = [_primary_energy_per_m2(c, "fcu_doas")[2] for c in CITIES]

    angles = np.linspace(0, 2 * np.pi, len(CITIES), endpoint=False).tolist()
    angles += angles[:1]
    vrf_plot = vrf_tot + vrf_tot[:1]
    fcu_plot = fcu_tot + fcu_tot[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True),
                           constrained_layout=True)
    ax.plot(angles, vrf_plot, color=VRF_COLOR, linewidth=2, label="VRF+DOAS")
    ax.fill(angles, vrf_plot, color=VRF_COLOR, alpha=0.15)
    ax.plot(angles, fcu_plot, color=FCU_COLOR, linewidth=2, label="FCU+DOAS")
    ax.fill(angles, fcu_plot, color=FCU_COLOR, alpha=0.15)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([CITY_LABEL[c].replace("\n", " ") for c in CITIES], fontsize=8)
    ax.set_ylabel("")
    ax.set_title("不同气候下的一次能源强度分布（kWh/m²）", pad=20)
    for ang, val in zip(angles[:-1], vrf_tot):
        ax.annotate(f"{val:.0f}", xy=(ang, val), fontsize=7, color=VRF_COLOR,
                    ha="center", va="bottom")
    for ang, val in zip(angles[:-1], fcu_tot):
        ax.annotate(f"{val:.0f}", xy=(ang, val), fontsize=7, color=FCU_COLOR,
                    ha="center", va="top")
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1.1), frameon=False, fontsize=9)
    path = output_root / f"direction1_energy_radar.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


def plot_climate_cdf(output_root: Path, file_format: str = "pdf") -> Path:
    """F6: outdoor dry-bulb and enthalpy CDFs per city (climate background)."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), constrained_layout=True)
    pct = np.linspace(0, 100, 501)
    for city in CITIES:
        dry, enth = _weather_series(city)
        dry_sorted = np.percentile(dry, pct)
        enth_sorted = np.percentile(enth, pct)
        label = CITY_SHORT_CN[city]
        axes[0].plot(dry_sorted, pct, color=CITY_LINE_COLORS[city], linewidth=1.8, label=label)
        axes[1].plot(enth_sorted, pct, color=CITY_LINE_COLORS[city], linewidth=1.8, label=label)
    for temp, name in ((20, "供热设定 20°C"), (26, "制冷设定 26°C")):
        axes[0].axvline(temp, color="#444444", linestyle=":", linewidth=1)
        axes[0].text(temp, 4, name, rotation=90, va="bottom", ha="right", fontsize=7)
    axes[0].set_xlabel("室外干球温度（°C）")
    axes[0].set_ylabel("累积概率（%）")
    axes[0].set_title("室外干球温度分布")
    axes[0].grid(alpha=0.25)
    axes[0].set_axisbelow(True)
    axes[1].set_xlabel("室外空气焓值（kJ/kg）")
    axes[1].set_ylabel("累积概率（%）")
    axes[1].set_title("湿空气焓值分布")
    axes[1].grid(alpha=0.25)
    axes[1].set_axisbelow(True)
    axes[1].axvline(58, color="#444444", linestyle=":", linewidth=1)
    axes[1].text(58, 4, "室内 26°C/60%\n约 58 kJ/kg", rotation=90, va="bottom", ha="right", fontsize=7)
    axes[1].legend(fontsize=7, frameon=False, loc="lower right")
    path = output_root / f"direction1_climate_cdf.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


def plot_lcc_waterfall(output_root: Path, file_format: str = "pdf") -> Path:
    """F7: life-cycle cost breakdown — initial investment + 15-yr operating, per city×system."""
    rows = {(r["city"], r["system"]): r for r in compute_scores()}
    x = np.arange(len(CITIES))
    w = 0.36
    vrf_init = [rows[(c, "vrf")]["initial_cost"] / 1e4 for c in CITIES]
    vrf_oper = [rows[(c, "vrf")]["annual_operating"] * 15 / 1e4 for c in CITIES]
    fcu_init = [rows[(c, "fcu_doas")]["initial_cost"] / 1e4 for c in CITIES]
    fcu_oper = [rows[(c, "fcu_doas")]["annual_operating"] * 15 / 1e4 for c in CITIES]

    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.bar(x - w / 2, vrf_init, w, color=VRF_COLOR, edgecolor="white", linewidth=0.5,
           label="多联机初投资")
    ax.bar(x - w / 2, vrf_oper, w, bottom=vrf_init, color="#f0b88c",
           edgecolor="white", linewidth=0.5, label="多联机15年运行费")
    ax.bar(x + w / 2, fcu_init, w, color=FCU_COLOR, edgecolor="white", linewidth=0.5,
           label="风机盘管初投资")
    ax.bar(x + w / 2, fcu_oper, w, bottom=fcu_init, color="#9cc0db",
           edgecolor="white", linewidth=0.5, label="风机盘管15年运行费")
    for i in range(len(CITIES)):
        ax.text(x[i] - w / 2, vrf_init[i] + vrf_oper[i], f"{vrf_init[i]+vrf_oper[i]:.0f}",
                ha="center", va="bottom", fontsize=8, color=VRF_COLOR)
        ax.text(x[i] + w / 2, fcu_init[i] + fcu_oper[i], f"{fcu_init[i]+fcu_oper[i]:.0f}",
                ha="center", va="bottom", fontsize=8, color=FCU_COLOR)
    ax.set_xticks(x)
    ax.set_xticklabels([CITY_LABEL[c] for c in CITIES], fontsize=8)
    ax.set_ylabel("寿命周期费用（万元，15年）")
    ax.set_title("寿命周期费用构成：初投资 + 15年运行费")
    ax.legend(loc="upper left", frameon=False, fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    path = output_root / f"direction1_lcc_waterfall.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


# Representative VRF low-ambient heating COP vs outdoor temperature (literature:
# GB 21455-2019 / low-temp VRF manufacturer samples). Below ~ -12 °C COP drops
# under a gas boiler's 0.92 thermal efficiency (primary-energy basis ~0.885).
_VRF_COP_TEMP = [-25, -20, -15, -10, -7, 0, 7, 12]
_VRF_COP_VAL = [1.3, 1.6, 1.9, 2.3, 2.6, 3.1, 3.8, 4.3]


def plot_vrf_cop_degradation(output_root: Path, file_format: str = "pdf") -> Path:
    """F8: VRF heating primary-energy efficiency vs outdoor temp (cold-climate penalty).

    Plots VRF COP/2.46 against the gas-boiler primary-energy efficiency (0.885) so both
    systems are compared on the same primary-energy basis. Below the crossover (~-11°C)
    the VRF heat pump is less primary-efficient than a gas boiler.
    """
    from air_conditioning_design.analysis.suitability import (
        PRIMARY_FACTOR_ELEC, WINTER_DESIGN_TEMP,
    )

    t_dense = np.linspace(-25, 15, 200)
    cop_dense = np.interp(t_dense, _VRF_COP_TEMP, _VRF_COP_VAL)
    vrf_primary_eff = cop_dense / PRIMARY_FACTOR_ELEC
    boiler_eff = 0.92 / PRIMARY_FACTOR_GAS  # = 0.885

    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.plot(t_dense, vrf_primary_eff, color=VRF_COLOR, linewidth=2.2,
            label="多联机热泵（COP ÷ 2.46）")
    ax.scatter(_VRF_COP_TEMP, [v / PRIMARY_FACTOR_ELEC for v in _VRF_COP_VAL],
               color=VRF_COLOR, zorder=3, s=25)
    ax.axhline(boiler_eff, color=FCU_COLOR, linestyle="--", linewidth=1.8,
               label=f"燃气锅炉（η÷1.04≈{boiler_eff:.3f}）")
    # Crossover annotation.
    ax.fill_between(t_dense, vrf_primary_eff, boiler_eff,
                    where=(vrf_primary_eff < boiler_eff), color="#d66a35", alpha=0.12,
                    label="锅炉一次能源效率更高区域")
    for city in ("shenyang", "tianjin"):
        tw = WINTER_DESIGN_TEMP[city]
        eff_at = float(np.interp(tw, _VRF_COP_TEMP, _VRF_COP_VAL)) / PRIMARY_FACTOR_ELEC
        ax.axvline(tw, color=CITY_LINE_COLORS[city], linestyle=":", linewidth=1.3)
        ax.annotate(f"{CITY_SHORT_CN[city]}\n{tw}°C → {eff_at:.2f}", xy=(tw, eff_at),
                    xytext=(tw + 1.5, eff_at - 0.22), fontsize=8,
                    color=CITY_LINE_COLORS[city],
                    arrowprops=dict(arrowstyle="->", color=CITY_LINE_COLORS[city], lw=1))
    ax.set_xlabel("室外干球温度（°C）")
    ax.set_ylabel("一次能源供热效率（供热量 ÷ 一次能源）")
    ax.set_title("低温工况下多联机供热效率与燃气锅炉对比")
    ax.set_xlim(-26, 15)
    ax.set_ylim(0, 1.85)
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    path = output_root / f"direction1_vrf_cop_degradation.{file_format}"
    fig.savefig(path, dpi=200, format=file_format)
    plt.close(fig)
    return path


def build_direction1_figures(output_root: Path | None = None,
                             file_format: str = "pdf") -> list[Path]:
    target = output_root or PAPER_FIGURES_ROOT
    target.mkdir(parents=True, exist_ok=True)
    _set_chinese_style()
    return [plot_load_split(target, file_format),
            plot_capacity_ratio(target, file_format),
            plot_primary_energy_comparison(target, file_format),
            plot_energy_radar(target, file_format),
            plot_suitability_heatmap(target, file_format),
            plot_climate_cdf(target, file_format),
            plot_lcc_waterfall(target, file_format),
            plot_vrf_cop_degradation(target, file_format)]
