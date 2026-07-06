from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "air-conditioning-design"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
import numpy as np

from air_conditioning_design.analysis.direction1_plots import (
    CITY_LINE_COLORS,
    _VRF_COP_TEMP,
    _VRF_COP_VAL,
    _peak_load_ratio,
    _primary_energy_per_m2,
    _read_equipment,
    _weather_series,
)
from air_conditioning_design.analysis.report_data import build_ideal_loads_comparison
from air_conditioning_design.analysis.suitability import (
    CITIES,
    PRIMARY_FACTOR_ELEC,
    PRIMARY_FACTOR_GAS,
    SYSTEM_LABEL,
    WINTER_DESIGN_TEMP,
    compute_scores,
)
from air_conditioning_design.config.paths import PAPER_FIGURES_ROOT

DEFAULT_OUTPUT_ROOT = PAPER_FIGURES_ROOT
DEFENSE_CN_STEMS = (
    "defense_cn_load_structure",
    "defense_cn_climate_cdf",
    "defense_cn_capacity_ratio",
    "defense_cn_primary_energy",
    "defense_cn_suitability_heatmap",
    "defense_cn_lcc_breakdown",
    "defense_cn_vrf_cop_degradation",
    "defense_cn_enthalpy_explain",
    "defense_cn_weather_overview",
    "defense_cn_weather_temperature",
    "defense_cn_weather_enthalpy",
)
CASE_CN_STEMS = {
    "shenyang": "defense_cn_case_shenyang",
    "tianjin": "defense_cn_case_tianjin",
    "chengdu": "defense_cn_case_chengdu",
    "chongqing": "defense_cn_case_chongqing",
    "shenzhen": "defense_cn_case_shenzhen",
}

CITY_CN = {
    "shenyang": "沈阳\n严寒",
    "tianjin": "天津\n寒冷",
    "chengdu": "成都\n夏热冬冷",
    "chongqing": "重庆\n夏热冬冷",
    "shenzhen": "深圳\n夏热冬暖",
}
CITY_SHORT_CN = {
    "shenyang": "沈阳",
    "tianjin": "天津",
    "chengdu": "成都",
    "chongqing": "重庆",
    "shenzhen": "深圳",
}
SYSTEM_CN = {"vrf": "多联机+独立新风", "fcu_doas": "风机盘管+独立新风"}

COOLING_COLOR = "#24577a"
HEATING_COLOR = "#b84a4a"
FCU_COLOR = "#24577a"
VRF_COLOR = "#d66a35"
LOAD_COLOR = "#8c8c8c"
ELEC_COLOR = "#4a90d9"
GAS_COLOR = "#e0992e"
NOTE_FACE = "#fff8e8"
NOTE_EDGE = "#d4a252"
CASE_DATA = {
    "shenyang": {
        "title": "沈阳制冷设计结果",
        "season": "6--8月短供冷",
        "peak": 116.07,
        "density": 85.4,
        "fresh": 46.42,
        "vrf": 174.0,
        "combo": 116.8,
        "fcu": 127.7,
        "focus": "短时峰值、新风预冷",
        "notes": ["供冷季短，但设计日峰值不能低估", "多联机适合机房受限情形", "风机盘管冷源不宜明显放大"],
    },
    "tianjin": {
        "title": "天津制冷设计结果",
        "season": "6--9月供冷",
        "peak": 133.90,
        "density": 98.6,
        "fresh": 59.17,
        "vrf": 191.0,
        "combo": 116.2,
        "fcu": 147.3,
        "focus": "高温日射、湿负荷",
        "notes": ["夏季干球温度和日射强度较高", "二层周边区和核心区末端需复核", "屋面、机房和管井条件决定方案选择"],
    },
    "chengdu": {
        "title": "成都制冷设计结果",
        "season": "5--10月供冷",
        "peak": 123.50,
        "density": 90.9,
        "fresh": 48.93,
        "vrf": 185.5,
        "combo": 117.6,
        "fcu": 135.9,
        "focus": "部分负荷、除湿",
        "notes": ["峰值冷量中等，新风冷量较高", "送风露点影响室内相对湿度", "设备选型需兼顾部分负荷稳定性"],
    },
    "chongqing": {
        "title": "重庆制冷设计结果",
        "season": "5--10月高温高湿",
        "peak": 150.48,
        "density": 110.8,
        "fresh": 70.55,
        "vrf": 209.5,
        "combo": 117.9,
        "fcu": 165.5,
        "focus": "峰值冷量、潜热处理",
        "notes": ["五城市中峰值冷负荷密度最高", "新风冷负荷最高，潜热压力大", "散热修正和凝结水排放需提前校核"],
    },
    "shenzhen": {
        "title": "深圳制冷设计结果",
        "season": "4--11月长供冷",
        "peak": 142.54,
        "density": 104.9,
        "fresh": 63.72,
        "vrf": 203.0,
        "combo": 116.3,
        "fcu": 156.8,
        "focus": "长时制冷、持续除湿",
        "notes": ["峰值略低于重庆，但供冷季最长", "新风潜热处理和连续除湿是重点", "低负荷连续运行和冷凝水组织需复核"],
    },
}

def _set_chinese_style() -> None:
    names = {font.name for font in font_manager.fontManager.ttflist}
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"]
    font = next((name for name in candidates if name in names), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [font, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.titlesize": 18,
            "axes.titleweight": "bold",
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linestyle": "-",
        }
    )


def _save(fig, output_root: Path, stem: str, formats: Sequence[str]) -> list[Path]:
    paths = []
    for file_format in formats:
        path = output_root / f"{stem}.{file_format}"
        fig.savefig(path, format=file_format)
        paths.append(path)
    plt.close(fig)
    return paths


def _note(ax, text: str, xy: tuple[float, float], *, width: int | None = None) -> None:
    bbox = dict(boxstyle="round,pad=0.45", fc=NOTE_FACE, ec=NOTE_EDGE, lw=1.2)
    ax.text(
        xy[0],
        xy[1],
        text if width is None else "\n".join(text[i : i + width] for i in range(0, len(text), width)),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        color="#3a3a3a",
        bbox=bbox,
    )


def _defense_weather_series(city: str) -> tuple[list[float], list[float]]:
    dry, enth = _weather_series(city)
    return dry, [value for value in enth if -40 <= value <= 160]


def plot_load_structure(output_root: Path, formats: Sequence[str]) -> list[Path]:
    rows = [r for r in build_ideal_loads_comparison() if r["city"] in CITIES]
    rows.sort(key=lambda row: CITIES.index(str(row["city"])))
    cool = np.array([float(r["annual_cooling_load_kwh"]) for r in rows]) / 1e3
    heat = np.array([float(r["annual_heating_load_kwh"]) for r in rows]) / 1e3
    totals = cool + heat

    fig, ax = plt.subplots(figsize=(12, 6.8), constrained_layout=True)
    y = np.arange(len(rows))
    ax.barh(y, cool, color=COOLING_COLOR, label="制冷负荷", edgecolor="white", linewidth=0.8)
    ax.barh(y, heat, left=cool, color=HEATING_COLOR, label="供热负荷", edgecolor="white", linewidth=0.8)
    for i, (c, h, total) in enumerate(zip(cool, heat, totals)):
        display_total = round(c / 10, 1) * 10 + round(h / 10, 1) * 10
        ax.text(c / 2, i, f"{c / total:.0%}", ha="center", va="center", color="white", fontsize=12, fontweight="bold")
        ax.text(c + h / 2, i, f"{h / total:.0%}", ha="center", va="center", color="white", fontsize=12, fontweight="bold")
        ax.text(total, i, f"  总量 {display_total:.0f} MWh", ha="left", va="center", fontsize=11)
    ax.set_yticks(y)
    ax.set_yticklabels([CITY_CN[str(r["city"])] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("全年理想冷热负荷（MWh）")
    ax.set_title("方向一：五类气候区的冷热负荷结构")
    ax.legend(loc="lower right", frameon=True)
    ax.set_axisbelow(True)
    return _save(fig, output_root, DEFENSE_CN_STEMS[0], formats)


def plot_climate_cdf(output_root: Path, formats: Sequence[str]) -> list[Path]:
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.8), constrained_layout=True)
    pct = np.linspace(0, 100, 501)
    weather = {}
    for city in CITIES:
        dry, enth = _defense_weather_series(city)
        dry_sorted = np.percentile(dry, pct)
        enth_sorted = np.percentile(enth, pct)
        weather[city] = (dry_sorted, enth_sorted)
        label = CITY_SHORT_CN[city]
        axes[0].plot(dry_sorted, pct, color=CITY_LINE_COLORS[city], linewidth=2.1, label=label)
        axes[1].plot(enth_sorted, 100 - pct, color=CITY_LINE_COLORS[city], linewidth=2.3, label=label)
    for temp, name in ((20, "供热设定 20°C"), (24, "制冷设定 24°C")):
        axes[0].axvline(temp, color="#444444", linestyle=":", linewidth=1.2)
        axes[0].text(temp, 5, name, rotation=90, va="bottom", ha="right", fontsize=10)
    axes[0].set_xlabel("室外干球温度（°C）")
    axes[0].set_ylabel("累计概率（%）")
    axes[0].set_title("温度分布：冬季尾部决定低温供热风险")
    axes[1].set_xlabel("室外空气焓值（kJ/kg）")
    axes[1].set_ylabel("超过该焓值的小时占比（%）")
    axes[1].set_title("高焓小时占比：新风除湿压力在高焓段拉开")
    axes[1].set_xlim(45, 110)
    axes[1].set_ylim(0, 72)
    indoor_enthalpy = 53
    axes[1].axvspan(indoor_enthalpy, 110, color=COOLING_COLOR, alpha=0.08)
    axes[1].axvline(indoor_enthalpy, color="#444444", linestyle=":", linewidth=1.2)
    axes[1].text(indoor_enthalpy, 3, "室内 24°C/60%\n约 53 kJ/kg", rotation=90, va="bottom", ha="right", fontsize=10)
    for city in ("shenyang", "chongqing", "shenzhen"):
        _, enth_sorted = weather[city]
        exceed_indoor = float(np.interp(indoor_enthalpy, enth_sorted, 100 - pct))
        label_y = min(exceed_indoor - 2.2, 66) if city == "shenzhen" else exceed_indoor
        axes[1].scatter([indoor_enthalpy], [exceed_indoor], color=CITY_LINE_COLORS[city], s=28, zorder=4)
        axes[1].text(indoor_enthalpy + 2, label_y, f"{CITY_SHORT_CN[city]} {exceed_indoor:.0f}%", color=CITY_LINE_COLORS[city], va="center", fontsize=10)
    axes[1].legend(fontsize=10, frameon=True, loc="upper right")
    inset = inset_axes(axes[0], width="38%", height="42%", loc="lower right", borderpad=1.2)
    for city, (dry_sorted, _) in weather.items():
        inset.plot(dry_sorted, pct, color=CITY_LINE_COLORS[city], linewidth=1.6)
    inset.set_xlim(-25, 6)
    inset.set_ylim(0, 32)
    inset.set_title("放大：低温尾部", fontsize=10)
    inset.grid(alpha=0.25)
    mark_inset(axes[0], inset, loc1=2, loc2=4, fc="none", ec="#777777", lw=1)
    _note(axes[1], "53 kJ/kg 以上的小时占比。深圳多数时间高于该线，重庆明显高于北方，因此新风总冷负荷和潜热压力更重。", (0.03, 0.98), width=25)
    return _save(fig, output_root, DEFENSE_CN_STEMS[1], formats)


def plot_enthalpy_explain(output_root: Path, formats: Sequence[str]) -> list[Path]:
    fig, ax = plt.subplots(figsize=(5.2, 4.0), constrained_layout=True)
    pct = np.linspace(0, 100, 501)
    weather = {}
    for city in CITIES:
        _, enth = _defense_weather_series(city)
        enth_sorted = np.percentile(enth, pct)
        exceed = 100 - pct
        weather[city] = (enth_sorted, exceed)
        ax.plot(enth_sorted, exceed, color=CITY_LINE_COLORS[city], linewidth=2.4, label=CITY_SHORT_CN[city])
    indoor_enthalpy = 53
    ax.axvspan(indoor_enthalpy, 110, color=COOLING_COLOR, alpha=0.08)
    ax.axvline(indoor_enthalpy, color="#333333", linestyle=":", linewidth=1.3)
    ax.text(indoor_enthalpy + 1.0, 66, "室内约 53 kJ/kg", fontsize=11, color="#333333")
    offsets = {"shenyang": (2.0, -5.0), "chongqing": (2.0, 2.5), "shenzhen": (4.5, -6.0)}
    for city, (dx, dy) in offsets.items():
        enth_sorted, exceed = weather[city]
        value = float(np.interp(indoor_enthalpy, enth_sorted, exceed))
        ax.scatter([indoor_enthalpy], [value], color=CITY_LINE_COLORS[city], s=38, zorder=4)
        ax.annotate(
            f"{CITY_SHORT_CN[city]} {value:.0f}%",
            xy=(indoor_enthalpy, value),
            xytext=(indoor_enthalpy + dx, value + dy),
            arrowprops=dict(arrowstyle="->", color=CITY_LINE_COLORS[city], lw=1.0),
            color=CITY_LINE_COLORS[city],
            fontsize=11,
        )
    ax.set_xlim(45, 110)
    ax.set_ylim(0, 72)
    ax.set_xlabel("室外空气焓值（kJ/kg）")
    ax.set_ylabel("超过该焓值的小时占比（%）")
    ax.set_title("高焓小时占比：新风除湿压力")
    ax.legend(loc="upper right", frameon=True)
    ax.set_axisbelow(True)
    return _save(fig, output_root, DEFENSE_CN_STEMS[7], formats)


def plot_weather_overview(output_root: Path, formats: Sequence[str]) -> list[Path]:
    fig, axes = plt.subplots(2, 5, figsize=(13.2, 5.8), constrained_layout=True)
    temp_bins = np.linspace(-30, 42, 37)
    enth_bins = np.linspace(0, 110, 37)
    for i, city in enumerate(CITIES):
        dry, enth = _defense_weather_series(city)
        color = CITY_LINE_COLORS[city]
        temp_ax = axes[0, i]
        enth_ax = axes[1, i]
        temp_ax.hist(dry, bins=temp_bins, color=color, alpha=0.80, edgecolor="white", linewidth=0.4)
        enth_ax.hist(enth, bins=enth_bins, color=color, alpha=0.80, edgecolor="white", linewidth=0.4)
        temp_ax.axvline(24, color="#333333", linestyle=":", linewidth=1.0)
        enth_ax.axvline(53, color="#333333", linestyle=":", linewidth=1.0)
        temp_ax.set_title(CITY_SHORT_CN[city], fontsize=13, color=color, fontweight="bold")
        temp_ax.set_xlim(-30, 42)
        enth_ax.set_xlim(0, 110)
        temp_ax.tick_params(labelsize=8)
        enth_ax.tick_params(labelsize=8)
        temp_ax.grid(axis="y", alpha=0.18)
        enth_ax.grid(axis="y", alpha=0.18)
        temp_ax.set_xlabel("温度（°C）", fontsize=9)
        enth_ax.set_xlabel("焓值（kJ/kg）", fontsize=9)
    axes[0, 0].set_ylabel("温度小时数", fontsize=10)
    axes[1, 0].set_ylabel("焓值小时数", fontsize=10)
    fig.suptitle("五个代表城市EPW逐时气象分布", fontsize=16, fontweight="bold")
    return _save(fig, output_root, DEFENSE_CN_STEMS[8], formats)


def _plot_weather_row(
    output_root: Path,
    formats: Sequence[str],
    *,
    stem: str,
    title: str,
    xlabel: str,
    ylabel: str,
    bins: np.ndarray,
    marker: float,
    data_index: int,
) -> list[Path]:
    fig, axes = plt.subplots(1, 5, figsize=(13.2, 3.5), constrained_layout=True)
    for ax, city in zip(axes, CITIES):
        series = _defense_weather_series(city)[data_index]
        color = CITY_LINE_COLORS[city]
        ax.hist(series, bins=bins, color=color, alpha=0.82, edgecolor="white", linewidth=0.4)
        ax.axvline(marker, color="#333333", linestyle=":", linewidth=1.1)
        ax.set_title(CITY_SHORT_CN[city], fontsize=13, color=color, fontweight="bold")
        ax.set_xlabel(xlabel, fontsize=9)
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", alpha=0.18)
    axes[0].set_ylabel(ylabel, fontsize=10)
    fig.suptitle(title, fontsize=16, fontweight="bold")
    return _save(fig, output_root, stem, formats)


def plot_weather_rows(output_root: Path, formats: Sequence[str]) -> list[Path]:
    paths = []
    paths.extend(
        _plot_weather_row(
            output_root,
            formats,
            stem=DEFENSE_CN_STEMS[9],
            title="五个代表城市EPW逐时室外干球温度分布",
            xlabel="温度（°C）",
            ylabel="小时数",
            bins=np.linspace(-30, 42, 37),
            marker=24,
            data_index=0,
        )
    )
    paths.extend(
        _plot_weather_row(
            output_root,
            formats,
            stem=DEFENSE_CN_STEMS[10],
            title="五个代表城市EPW逐时室外空气焓值分布",
            xlabel="焓值（kJ/kg）",
            ylabel="小时数",
            bins=np.linspace(0, 110, 37),
            marker=53,
            data_index=1,
        )
    )
    return paths


def plot_capacity_ratio(output_root: Path, formats: Sequence[str]) -> list[Path]:
    equip = _read_equipment()
    fcu_ratio = []
    load_ratio = []
    for city in CITIES:
        eq = equip[(city, "fcu_doas")]
        fcu_ratio.append(float(eq["design_cooling_capacity_kw"]) / float(eq["design_heating_capacity_kw"]))
        load_ratio.append(_peak_load_ratio(city))

    x = np.arange(len(CITIES))
    w = 0.36
    fig, ax = plt.subplots(figsize=(12, 6.8), constrained_layout=True)
    ax.axhline(1.0, color=VRF_COLOR, linestyle="--", linewidth=2.0, label="多联机冷热同机：基准比 1.0")
    b1 = ax.bar(x - w / 2, fcu_ratio, w, color=FCU_COLOR, label="风机盘管冷源/热源容量比", edgecolor="white", linewidth=0.8)
    b2 = ax.bar(x + w / 2, load_ratio, w, color=LOAD_COLOR, label="峰值冷/热负荷比", edgecolor="white", linewidth=0.8)
    for bars in (b1, b2):
        for rect in bars:
            ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{rect.get_height():.2f}", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([CITY_CN[c] for c in CITIES])
    ax.set_ylabel("冷热比（制冷 ÷ 供热）")
    ax.set_title("容量比：风机盘管可按冷/热负荷分别配置，多联机通常保持对称")
    ax.legend(loc="upper left", frameon=True)
    ax.set_axisbelow(True)
    inset = inset_axes(ax, width="34%", height="36%", loc="upper right", borderpad=1.2)
    inset.axhline(1.0, color=VRF_COLOR, linestyle="--", linewidth=1.4)
    inset.bar(x - w / 2, fcu_ratio, w, color=FCU_COLOR, edgecolor="white", linewidth=0.5)
    inset.bar(x + w / 2, load_ratio, w, color=LOAD_COLOR, edgecolor="white", linewidth=0.5)
    inset.set_xlim(-0.6, 2.6)
    inset.set_ylim(0.75, 2.25)
    inset.set_xticks(x[:3])
    inset.set_xticklabels([CITY_SHORT_CN[c] for c in CITIES[:3]], fontsize=8)
    inset.set_title("放大：寒冷侧差异", fontsize=10)
    inset.grid(axis="y", alpha=0.25)
    mark_inset(ax, inset, loc1=2, loc2=4, fc="none", ec="#777777", lw=1)
    _note(ax, "设计含义：容量比接近负荷比，说明冷热源分设更容易贴合城市负荷；多联机的 1.0 对称性在严寒/寒冷地区需要重点解释。", (0.48, 0.42), width=25)
    return _save(fig, output_root, DEFENSE_CN_STEMS[2], formats)


def plot_primary_energy(output_root: Path, formats: Sequence[str]) -> list[Path]:
    vrf_elec, fcu_elec, fcu_gas = [], [], []
    for city in CITIES:
        ve, _, _ = _primary_energy_per_m2(city, "vrf")
        fe, fg, _ = _primary_energy_per_m2(city, "fcu_doas")
        vrf_elec.append(ve)
        fcu_elec.append(fe)
        fcu_gas.append(fg)

    x = np.arange(len(CITIES))
    w = 0.36
    fig, ax = plt.subplots(figsize=(12, 6.8), constrained_layout=True)
    ax.bar(x - w / 2, vrf_elec, w, color=ELEC_COLOR, edgecolor="white", linewidth=0.8, label=f"多联机电力一次能源（×{PRIMARY_FACTOR_ELEC:.2f}）")
    ax.bar(x + w / 2, fcu_elec, w, color=ELEC_COLOR, edgecolor="white", linewidth=0.8, label=f"风机盘管电力一次能源（×{PRIMARY_FACTOR_ELEC:.2f}）")
    ax.bar(x + w / 2, fcu_gas, w, bottom=fcu_elec, color=GAS_COLOR, edgecolor="white", linewidth=0.8, label=f"风机盘管燃气一次能源（×{PRIMARY_FACTOR_GAS:.2f}）")
    totals_vrf = np.array(vrf_elec)
    totals_fcu = np.array(fcu_elec) + np.array(fcu_gas)
    for i in range(len(CITIES)):
        ax.text(x[i] - w / 2, totals_vrf[i], f"{totals_vrf[i]:.0f}", ha="center", va="bottom", fontsize=10)
        ax.text(x[i] + w / 2, totals_fcu[i], f"{totals_fcu[i]:.0f}", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([CITY_CN[c] for c in CITIES])
    ax.set_ylabel("全年 HVAC 一次能源强度（kWh/m²）")
    ax.set_title("一次能源比较：全电多联机与电+燃气风机盘管的口径统一")
    ax.legend(loc="upper right", frameon=True)
    ax.set_axisbelow(True)
    gap_idx = int(np.argmax(np.abs(totals_vrf - totals_fcu)))
    ax.annotate(
        f"差值约 {abs(totals_vrf[gap_idx] - totals_fcu[gap_idx]):.0f} kWh/m²",
        xy=(x[gap_idx], max(totals_vrf[gap_idx], totals_fcu[gap_idx])),
        xytext=(x[gap_idx] - 0.7, max(totals_vrf.max(), totals_fcu.max()) * 1.10),
        arrowprops=dict(arrowstyle="->", color="#264653", lw=1.4),
        color="#264653",
        fontsize=12,
    )
    _note(ax, "旁白：图中不是终端电/气账单，而是按一次能源系数折算后的可比指标。", (0.03, 0.98), width=22)
    return _save(fig, output_root, DEFENSE_CN_STEMS[3], formats)


def plot_suitability_heatmap(output_root: Path, formats: Sequence[str]) -> list[Path]:
    rows = compute_scores()
    dims = ["D1", "D2", "D3", "D4", "D5", "D6", "total"]
    dim_labels = ["D1\n容量匹配", "D2\n一次能效", "D3\n能耗强度", "D4\n除湿压力", "D5\n低温供热", "D6\n经济性", "总分"]
    data = np.array([[r[d] for d in dims] for r in rows], dtype=float)
    labels = [f"{CITY_SHORT_CN[r['city']]}  {SYSTEM_CN[r['system']]}" for r in rows]

    fig, ax = plt.subplots(figsize=(12, 7.2), constrained_layout=True)
    im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(dims)))
    ax.set_xticklabels(dim_labels)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels(labels)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            value = data[i, j]
            text = f"{value:.1f}" if j == len(dims) - 1 else f"{value:.0f}"
            ax.text(j, i, text, ha="center", va="center", fontsize=10, color="black" if 30 < value < 75 else "white", fontweight="bold")
    ax.add_patch(Rectangle((len(dims) - 1.5, -0.5), 1, len(rows), fill=False, edgecolor="#264653", linewidth=2.5))
    ax.set_title("适宜性热力图：把容量、能效、除湿、低温与经济性放到同一张表")
    cbar = fig.colorbar(im, ax=ax, shrink=0.82)
    cbar.set_label("适宜性得分（越高越适合）")
    _note(ax, "答辩读法：先看最右侧总分，再回到 D1–D6 解释“为什么这个城市更适合该系统”。", (0.52, -0.08), width=24)
    return _save(fig, output_root, DEFENSE_CN_STEMS[4], formats)


def plot_lcc_breakdown(output_root: Path, formats: Sequence[str]) -> list[Path]:
    rows = {(r["city"], r["system"]): r for r in compute_scores()}
    x = np.arange(len(CITIES))
    w = 0.36
    vrf_init = np.array([rows[(c, "vrf")]["initial_cost"] / 1e4 for c in CITIES])
    vrf_oper = np.array([rows[(c, "vrf")]["annual_operating"] * 15 / 1e4 for c in CITIES])
    fcu_init = np.array([rows[(c, "fcu_doas")]["initial_cost"] / 1e4 for c in CITIES])
    fcu_oper = np.array([rows[(c, "fcu_doas")]["annual_operating"] * 15 / 1e4 for c in CITIES])

    fig, ax = plt.subplots(figsize=(12, 6.8), constrained_layout=True)
    ax.bar(x - w / 2, vrf_init, w, color=VRF_COLOR, edgecolor="white", linewidth=0.8, label="多联机初投资")
    ax.bar(x - w / 2, vrf_oper, w, bottom=vrf_init, color="#f0b88c", edgecolor="white", linewidth=0.8, label="多联机15年运行费")
    ax.bar(x + w / 2, fcu_init, w, color=FCU_COLOR, edgecolor="white", linewidth=0.8, label="风机盘管初投资")
    ax.bar(x + w / 2, fcu_oper, w, bottom=fcu_init, color="#9cc0db", edgecolor="white", linewidth=0.8, label="风机盘管15年运行费")
    vrf_total = vrf_init + vrf_oper
    fcu_total = fcu_init + fcu_oper
    for i in range(len(CITIES)):
        ax.text(x[i] - w / 2, vrf_total[i], f"{vrf_total[i]:.0f}", ha="center", va="bottom", fontsize=10, color=VRF_COLOR)
        ax.text(x[i] + w / 2, fcu_total[i], f"{fcu_total[i]:.0f}", ha="center", va="bottom", fontsize=10, color=FCU_COLOR)
    ax.set_xticks(x)
    ax.set_xticklabels([CITY_CN[c] for c in CITIES])
    ax.set_ylabel("15年生命周期成本（万元）")
    ax.set_title("LCC 分解：初投资与运行费用共同决定方案经济性")
    ax.legend(loc="upper left", frameon=True, ncol=2)
    ax.set_axisbelow(True)
    share_idx = int(np.argmax(vrf_oper / vrf_total))
    ax.annotate(
        "运行费占比高，能效差异会被放大",
        xy=(x[share_idx] - w / 2, vrf_init[share_idx] + vrf_oper[share_idx] * 0.72),
        xytext=(x[share_idx] + 0.65, vrf_total.max() * 0.82),
        arrowprops=dict(arrowstyle="->", color=VRF_COLOR, lw=1.4),
        color=VRF_COLOR,
        fontsize=12,
    )
    _note(ax, "计算口径：LCC = 初投资 + 年运行费用 × 15。单位为万元，便于直接比较方案差异。", (0.56, 0.98), width=24)
    return _save(fig, output_root, DEFENSE_CN_STEMS[5], formats)


def plot_vrf_cop_degradation(output_root: Path, formats: Sequence[str]) -> list[Path]:
    t_dense = np.linspace(-25, 15, 240)
    cop_dense = np.interp(t_dense, _VRF_COP_TEMP, _VRF_COP_VAL)
    vrf_primary_eff = cop_dense / PRIMARY_FACTOR_ELEC
    boiler_eff = 0.92 / PRIMARY_FACTOR_GAS

    fig, ax = plt.subplots(figsize=(12, 6.8), constrained_layout=True)
    ax.plot(t_dense, vrf_primary_eff, color=VRF_COLOR, linewidth=2.5, label=f"多联机制热：性能系数 ÷ {PRIMARY_FACTOR_ELEC:.2f}")
    ax.scatter(_VRF_COP_TEMP, [v / PRIMARY_FACTOR_ELEC for v in _VRF_COP_VAL], color=VRF_COLOR, zorder=3, s=38)
    ax.axhline(boiler_eff, color=FCU_COLOR, linestyle="--", linewidth=2.0, label=f"燃气锅炉：0.92 ÷ {PRIMARY_FACTOR_GAS:.2f} ≈ {boiler_eff:.2f}")
    ax.fill_between(t_dense, vrf_primary_eff, boiler_eff, where=vrf_primary_eff < boiler_eff, color=VRF_COLOR, alpha=0.14, label="锅炉一次能源效率更高区间")
    for city in ("shenyang", "tianjin", "chengdu", "shenzhen"):
        temp = WINTER_DESIGN_TEMP[city]
        eff = float(np.interp(temp, _VRF_COP_TEMP, _VRF_COP_VAL)) / PRIMARY_FACTOR_ELEC
        ax.axvline(temp, color=CITY_LINE_COLORS[city], linestyle=":", linewidth=1.4)
        ax.annotate(f"{CITY_SHORT_CN[city]}\n{temp:g}°C", xy=(temp, eff), xytext=(temp + 1.2, eff + 0.16), arrowprops=dict(arrowstyle="->", color=CITY_LINE_COLORS[city], lw=1), color=CITY_LINE_COLORS[city], fontsize=11)
    ax.set_xlabel("室外干球温度（°C）")
    ax.set_ylabel("一次能源效率（供热量 ÷ 一次能源）")
    ax.set_title("多联机低温制热衰减：严寒/寒冷地区需解释冬季效率风险")
    ax.set_xlim(-26, 15)
    ax.set_ylim(0, 1.85)
    ax.legend(loc="upper left", frameon=True)
    ax.set_axisbelow(True)
    inset = inset_axes(ax, width="36%", height="38%", loc="lower right", borderpad=1.2)
    inset.plot(t_dense, vrf_primary_eff, color=VRF_COLOR, linewidth=1.8)
    inset.axhline(boiler_eff, color=FCU_COLOR, linestyle="--", linewidth=1.4)
    inset.fill_between(t_dense, vrf_primary_eff, boiler_eff, where=vrf_primary_eff < boiler_eff, color=VRF_COLOR, alpha=0.14)
    inset.set_xlim(-16, -6)
    inset.set_ylim(0.72, 1.05)
    inset.set_title("放大：效率交叉区", fontsize=10)
    inset.grid(alpha=0.25)
    mark_inset(ax, inset, loc1=2, loc2=4, fc="none", ec="#777777", lw=1)
    _note(ax, "旁白：性能系数不是固定值。温度越低，热泵制热越吃力；折算一次能源后，低温段可能输给燃气锅炉。", (0.47, 0.56), width=23)
    return _save(fig, output_root, DEFENSE_CN_STEMS[6], formats)


def _plot_case_card(city: str, output_root: Path, formats: Sequence[str]) -> list[Path]:
    data = CASE_DATA[city]
    fig = plt.figure(figsize=(10.8, 3.25), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.40, 1.20])
    ax_cards = fig.add_subplot(gs[0, 0])
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_note = fig.add_subplot(gs[0, 2])

    ax_cards.axis("off")
    cards = [
        ("峰值冷负荷", f"{data['peak']:.2f} kW", "#8c8c8c"),
        ("冷负荷指标", f"{data['density']:.1f} W/m²", "#24577a"),
        ("新风冷负荷", f"{data['fresh']:.1f} kW", "#2a9d8f"),
        ("全楼新风量", "7250 m³/h", "#d4a252"),
    ]
    for i, (label, value, color) in enumerate(cards):
        y0 = 0.76 - i * 0.24
        rect = Rectangle((0.04, y0), 0.88, 0.17, transform=ax_cards.transAxes, fc=color, ec="none", alpha=0.96)
        ax_cards.add_patch(rect)
        ax_cards.text(0.47, y0 + 0.105, value, transform=ax_cards.transAxes, ha="center", va="center", fontsize=15, color="white", fontweight="bold")
        ax_cards.text(0.47, y0 + 0.035, label, transform=ax_cards.transAxes, ha="center", va="center", fontsize=10.5, color="white")

    labels = ["峰值冷负荷", "多联机室外机", "风机盘管冷水机组", "新风冷负荷"]
    values = [float(data["peak"]), float(data["vrf"]), float(data["fcu"]), float(data["fresh"])]
    colors = ["#8c8c8c", "#d66a35", "#24577a", "#2a9d8f"]
    y = np.arange(len(labels))
    bars = ax_bar.barh(y, values, color=colors, height=0.55, edgecolor="white", linewidth=0.8)
    for bar, value in zip(bars, values):
        ax_bar.text(value + max(values) * 0.025, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center", fontsize=11, color="#333333")
    ax_bar.set_yticks(y)
    ax_bar.set_yticklabels(labels, fontsize=11)
    ax_bar.invert_yaxis()
    ax_bar.set_xlabel("冷量口径（kW）", fontsize=11)
    ax_bar.set_xlim(0, max(values) * 1.32)
    ax_bar.grid(axis="x", alpha=0.18)
    ax_bar.set_axisbelow(True)
    ax_bar.set_title(f"多联机组合率 {data['combo']:.0f}%", fontsize=13, color="#d66a35", pad=6)

    ax_note.axis("off")
    note_text = "\n".join(f"• {item}" for item in data["notes"])
    ax_note.text(
        0.02,
        0.90,
        f"设计重点\n{data['focus']}\n\n结果判断\n{note_text}",
        transform=ax_note.transAxes,
        ha="left",
        va="top",
        fontsize=11.3,
        linespacing=1.45,
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.50", fc="#fff8e8", ec="#d4a252", lw=1.2),
    )
    return _save(fig, output_root, CASE_CN_STEMS[city], formats)

def plot_case_cards(output_root: Path, formats: Sequence[str]) -> list[Path]:
    paths: list[Path] = []
    for city in CITIES:
        paths.extend(_plot_case_card(city, output_root, formats))
    return paths


DEFENSE_CN_PLOTS = (
    plot_load_structure,
    plot_climate_cdf,
    plot_enthalpy_explain,
    plot_weather_overview,
    plot_weather_rows,
    plot_capacity_ratio,
    plot_primary_energy,
    plot_suitability_heatmap,
    plot_lcc_breakdown,
    plot_vrf_cop_degradation,
    plot_case_cards,
)


def build_defense_chinese_figures(
    output_root: Path | None = None,
    formats: Sequence[str] = ("pdf", "png"),
) -> list[Path]:
    _set_chinese_style()
    target = output_root or DEFAULT_OUTPUT_ROOT
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for plotter in DEFENSE_CN_PLOTS:
        paths.extend(plotter(target, formats))
    return paths


if __name__ == "__main__":
    for path in build_defense_chinese_figures():
        print(f"Figure: {path}")
