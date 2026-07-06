from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib import font_manager

OUTPUT = Path("air-conditioning-design-paper/latex/figures")
SENSITIVITY_CSV = Path("results/processed/cltd_sensitivity.csv")
CITY_ORDER = ["沈阳", "天津", "成都", "重庆", "深圳"]
COLORS = ["#5E81AC", "#4A90D9", "#2A9D8F", "#E76F51", "#D4A252"]


def set_style() -> None:
    names = {font.name for font in font_manager.fontManager.ttflist}
    font = next((name for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC") if name in names), "DejaVu Sans")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [font, "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.20,
    })


def read_rows() -> list[dict]:
    if not SENSITIVITY_CSV.exists():
        raise FileNotFoundError("Run scripts/run_cltd_load_calculation.py first")
    with SENSITIVITY_CSV.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    set_style()
    rows = read_rows()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    fresh_labels = [("fresh_air_30", 30), ("fresh_air_50", 50)]
    fig, ax = plt.subplots(figsize=(9.2, 5.4), constrained_layout=True)
    for city, color in zip(CITY_ORDER, COLORS):
        city_rows = [row for row in rows if row["city"] == city]
        baseline = float(city_rows[0]["baseline_peak_kw"])
        points = [(40, baseline)]
        for scenario, rate in fresh_labels:
            match = next(row for row in city_rows if row["scenario"] == scenario)
            points.append((rate, float(match["scenario_peak_kw"])))
        points.sort()
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        ax.plot(xs, ys, marker="o", linewidth=2.2, markersize=5.5, color=color, label=city)
        ax.text(xs[-1] + 0.4, ys[-1], f"{ys[-1]:.1f}", va="center", fontsize=9, color=color)
    ax.axvline(40, color="#333333", linestyle=":", linewidth=1.3)
    ax.text(40.5, ax.get_ylim()[1] * 0.96, "本文基准值", fontsize=10, color="#333333")
    ax.set_xlim(28, 53)
    ax.set_xticks([30, 40, 50])
    ax.set_xlabel("人均新风量（m³/(h·人)）")
    ax.set_ylabel("夏季峰值冷负荷（kW）")
    ax.set_title("新风量取值对五城市峰值冷负荷的影响")
    ax.legend(ncol=5, loc="upper left", frameon=False)
    for ext in ("pdf", "png"):
        fig.savefig(OUTPUT / f"fresh_air_sensitivity_by_city.{ext}")
    plt.close(fig)

    scenario_order = [
        ("fresh_air_30", "新风 40→30"),
        ("fresh_air_50", "新风 40→50"),
        ("indoor_25", "室温 26→25℃"),
        ("indoor_27", "室温 26→27℃"),
        ("wwr_025", "窗墙比 0.35→0.25"),
        ("wwr_045", "窗墙比 0.35→0.45"),
        ("equipment_10", "设备 15→10W/m²"),
        ("equipment_20", "设备 15→20W/m²"),
        ("enhanced_envelope", "围护增强"),
        ("enhanced_shading", "遮阳增强"),
    ]
    matrix = []
    for scenario, _ in scenario_order:
        matrix.append([
            float(next(row for row in rows if row["city"] == city and row["scenario"] == scenario)["delta_percent"])
            for city in CITY_ORDER
        ])
    sensitivity = np.array(matrix)

    fig = plt.figure(figsize=(9.8, 5.4))
    ax = fig.add_axes([0.22, 0.28, 0.70, 0.56])
    cax = fig.add_axes([0.34, 0.16, 0.42, 0.035])
    limit = max(6, float(np.max(np.abs(sensitivity))))
    im = ax.imshow(sensitivity, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit), aspect="auto")
    ax.set_xticks(np.arange(len(CITY_ORDER)), labels=CITY_ORDER)
    ax.set_yticks(np.arange(len(scenario_order)), labels=[label for _, label in scenario_order])
    fig.text(0.5, 0.92, "设计参数单因素扰动对峰值冷负荷的影响", ha="center", va="center", fontsize=14)
    for i in range(sensitivity.shape[0]):
        for j in range(sensitivity.shape[1]):
            ax.text(j, i, f"{sensitivity[i, j]:+.1f}", ha="center", va="center", color="#222222", fontsize=8.2)
    cbar = fig.colorbar(im, cax=cax, orientation="horizontal")
    cbar.set_label("相对基准峰值冷负荷的变化（%）", labelpad=6)
    for ext in ("pdf", "png"):
        fig.savefig(OUTPUT / f"design_sensitivity_high_side.{ext}")
    plt.close(fig)


if __name__ == "__main__":
    main()
