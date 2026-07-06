from __future__ import annotations

import importlib.util
from pathlib import Path

from air_conditioning_design.config.paths import PAPER_FIGURES_ROOT


SCRIPT_PATH = Path("scripts/plot/plot_defense_chinese_figures.py")


def _load_script():
    spec = importlib.util.spec_from_file_location("plot_defense_chinese_figures", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_defense_chinese_figure_contract() -> None:
    module = _load_script()

    assert module.DEFAULT_OUTPUT_ROOT == PAPER_FIGURES_ROOT
    assert module.DEFENSE_CN_STEMS == (
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


def test_defense_chinese_build_writes_all_registered_formats(tmp_path, monkeypatch) -> None:
    module = _load_script()

    def fake_plot(output_root, formats):
        return [output_root / f"fake.{fmt}" for fmt in formats]

    monkeypatch.setattr(module, "DEFENSE_CN_PLOTS", (fake_plot,) * len(module.DEFENSE_CN_STEMS))

    paths = module.build_defense_chinese_figures(tmp_path, formats=("pdf", "png"))

    assert len(paths) == len(module.DEFENSE_CN_STEMS) * 2
    assert paths[0] == tmp_path / "fake.pdf"
    assert paths[1] == tmp_path / "fake.png"
