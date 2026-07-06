# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run a single EnergyPlus case:** `python scripts/run_energyplus_case.py --case-id <city>__<system>`
- **Parse one case's `eplusout.csv` into `results/processed/<case_id>_summary.csv`:** `python scripts/parse_tianjin_results.py --case-id <case_id>` (per-system: `parse_tianjin_<system>_results.py`)
- **Build neutral mother model:** `python scripts/build_neutral_mother_model.py`
- **Print latest load tables from raw CSVs:** `python scripts/generate_load_calc_tables.py`
- **Regenerate 负荷计算报告.docx:** `python scripts/generate_load_calc_docx.py`
- **Plot report figures into LaTeX dir:** `python scripts/plot/plot_report_figures.py`
- **Build floorplan figures from DXF:** `python scripts/plot/build_model_figures.py`
- **Generate direction1 (suitability) figures:** `python scripts/plot/plot_direction1_figures.py`
- **Verify direction1 data consistency:** `python scripts/verify_direction1_consistency.py`
- **Generate defense speech:** `python scripts/generate_defense_speech.py`
- **Run all tests:** `pytest`
- **Run single test:** `pytest tests/test_<name>.py -v`
- **Run tests matching pattern:** `pytest -k "<pattern>" -v`
- **Install package (editable):** `pip install -e ".[dev]"`
- **Sync with uv:** `uv sync` (if using uv — `uv.lock` present)

## Environment & Setup

- **Python**: `>=3.11` (`.python-version` pins 3.11). Runtime deps (declared in `pyproject.toml`): `ezdxf>=1.3` (DXF floorplan parsing), `matplotlib>=3.8` (figures). Dev extra: `pytest>=8.2`.
- **EnergyPlus**: 23.2 expected. Executable defaults to `D:/energyplus/2320/energyplus.exe`; falls back to PATH lookup if absent. Configure in `src/air-conditioning-design/air_conditioning_design/config/paths.py`. Example-file donors used for system IDFs: `DOAToVRF.idf`, `DOAToFanCoilInlet.idf`, `RefBldgMediumOfficeNew2004_Chicago.idf`. EnergyPlus is **never invoked in tests/CI** — only on a real simulation run.
- **Floor area constant**: `MEDIUM_OFFICE_FLOOR_AREA_M2 = 911.36` (used in all load density calculations).
- **Gitignored, locally generated**: `results/` (simulation outputs — `results/raw/<case_id>/`, `results/processed/`) and `context_portal/` (jCodeMunch's `context.db` code index + alembic). Neither is committed; both are produced by running the pipeline or the code indexer.

## Project Architecture

### Package: `src/air-conditioning-design/air_conditioning_design/`

| Layer | Path | Responsibility |
|-------|------|----------------|
| **Config** | `config/` | Path constants, city definitions (`CityConfig` dataclass), case ID encoding/decoding (`build_case_id`/`split_case_id`) |
| **IDF IO** | `idf/io.py` | Parse, filter, find, replace, write IDF objects (`IdfObject` dataclass with `IdfField` list) |
| **Models** | `models/` | IDF generation: neutral base model (`building_from_dxf.py` — 2-story, 10 zones, 911 m²), city envelope variants, system cases (`ideal_loads`, `vrf`, `fcu_doas` builders) |
| **Weather** | `weather/` | EPW/DDY manifest generation (`write_weather_manifest`/`load_weather_manifest`) and loading per city |
| **Simulation** | `simulation/runner.py` | `run_case(case_id)` — builds IDF, resolves weather, calls `energyplus --readvars`, safe output-dir reset |
| **Analysis** | `analysis/` | Parse `eplusout.csv` → summary CSVs: `ideal_loads_summary.py`, `vrf_summary.py`, `fcu_doas_summary.py`, `suitability.py` (technical suitability scoring), `direction1_plots.py` (suitability heatmaps and direction1 figures), `report_data.py`/`report_plots.py` (paper report pipeline) |
| **Figures** | `figures/` | IDF floorplan visualization: `geometry.py` (DXF geometry reconstruction), `annotations.py` (zone labels), `overlays.py` (dimension lines), `render.py` (matplotlib output) |
| **CLI** | `cli/` | Lightweight argument-parsing entry points — `run_energyplus_case.py`, `build_<city>_<system>.py`, `prepare_tianjin_weather.py` |

### Key data flow

`case_id` format: `{city_id}__{system_id}` (e.g., `tianjin__vrf`, `shenzhen__fcu_doas`)

1. `run_case(case_id)` in `runner.py` splits the case ID, builds the city's IDF variant from the neutral mother model
2. Generates system-specific IDF objects (ideal_loads/vrf/fcu_doas builders in `models/systems/`)
3. Loads weather manifest for EPW path
4. Executes `energyplus --readvars -w <epw> -d <output_dir> <idf>`
5. Analysis scripts parse `eplusout.csv` → summary metrics (peak load, annual energy)

### City × System matrix

5 cities (shenyang, tianjin, chengdu, shenzhen, chongqing) × 3 systems (ideal_loads, vrf, fcu_doas) = 15 cases. City configs defined in `config/cities.py` with 4 climate zone types (`severe_cold`, `cold`, `hot_summer_cold_winter`, `hot_summer_warm_winter`) — chengdu and chongqing both map to `hot_summer_cold_winter`. Builder functions in `models/systems/` accept a city parameter and support all 5 cities; convenience scripts under `scripts/` exist for Tianjin, while `scripts/run_energyplus_case.py --case-id <city>__<system>` handles any case.

### Test pattern

Tests mirror the build/parse matrix: `test_build_<city>_<system>.py` and `test_parse_<city>_<system>_results.py`. These validate IDF generation and CSV parsing, not EnergyPlus execution (no EnergyPlus in CI). Additional tests: `test_models_common.py`, `test_prepare_weather_catalog.py`, `test_report_data.py`, `test_run_energyplus_case.py`, `test_suitability.py`, `test_figure_*.py`. Test fixtures under `tests/fixtures/`. No conftest hooks beyond sys.path setup. Tests use the `src/air-conditioning-design` source root for import resolution (see `tests/conftest.py`).

### Load metrics — read these carefully

When extracting peak cooling load from `eplusout.csv`, **the correct metric is `Zone * Supply Air Total Cooling Rate`** (the load the equipment must actually supply), summed across all zones. `Zone Total Cooling Rate` is a zone heat balance term, **not** the equipment load — using it yields values ~10× too low (≈10–12 W/m² instead of the physical ≈90–130 W/m²). Per-zone peak cooling density lands in the 70–160 W/m² range across the five cities; whole-building peak density is 87.8–132.8 W/m², consistent with the 100–150 W/m² target. This applies to the `ideal_loads` system; `vrf`/`fcu_doas` cases are sized from these ideal loads. `scripts/generate_load_calc_tables.py` is the source of truth for current numbers — `generate_load_calc_docx.py` hardcodes a snapshot of that data, so regenerate the docx after any re-run.

Other prerequisites that produced correct magnitudes: people activity level must be ~120 W/person (not the DOE default of 1), and every conditioned zone needs a `ZoneControl:Thermostat` linked to a schedule, or EnergyPlus skips the zone's load.

The two load-correctness rules above are teacher-mandated hard constraints — see `老师反馈与硬约束.md` (repo root) for the authoritative statement and the 扫地式检查 list of disqualifying errors. Shenyang's 87.8 W/m² is the only sub-100 value; it is physically correct for a severe-cold zone where cooling is not the dominant load, not a metric error.

### Paper

LaTeX source in `air-conditioning-design-paper/latex/` using `elsarticle` class. Sections in `sections/` (one per city: `02-shenyang` … `06-shenzhen`, plus `07-comparison`/`08-conclusion`), figures in `figures/`. Build with `latexmk` or your LaTeX toolchain. A standalone Chinese load-calculation report (`负荷计算报告.docx`) and defense materials (`air-conditioning-design-paper/defenses/`) also live here. See `LOAD_CALCULATION_SUMMARY.md` (repo root) for the load-metric investigation record.

### Defense materials

Path: `air-conditioning-design-paper/defenses/`. Includes:
- `01-答辩PPT内容提纲.md` — defense slide outline
- `02-答辩逐字稿-8到10分钟.md` — 8-10 min speech script
- `03-答辩问答准备.md` — Q&A prep
- `04-答辩速记卡.md` — quick reference cards
- `beamer/college-beamer/` — Beamer LaTeX source + generated PDF/PPTX output

### Figures / reporting pipeline

Two analysis "directions" produce paper figures:
1. **Direction 1 (suitability)** — `scripts/plot/plot_direction1_figures.py` → calls `direction1_plots.py` (load split, capacity ratio, climate CDF, energy radar, suitability heatmap, LCC waterfall, VRF COP degradation, primary energy comparison). Also run `scripts/verify_direction1_consistency.py` after data changes.
2. **Report figures** — `scripts/plot/generate_report_data.py` → reads all `eplusout.csv` files, writes `results/processed/report_*.csv`. Then `scripts/plot/plot_report_figures.py` → matplotlib figures into `air-conditioning-design-paper/latex/figures/`.

`scripts/plot/build_report_assets.py` and `scripts/plot/build_model_figures.py` support building model geometry figures from the DXF.

Data flow details documented in `GEMINI.md` (sibling agent doc) — keep in sync. `AGENTS.md` is a parallel guidelines doc for other agents; `老师反馈与硬约束.md` holds the teacher-mandated hard constraints.

### Scripts

`scripts/` are the primary user entry points — run from repo root. They adjust `sys.path` to import the core package. Each wraps a corresponding module in `cli/`.

### Spec-driven workflow & conventions

This project is spec-driven. `docs/spec/` (`target.md`, `architecture.md`, `task.md`) defines goals and a task ledger; `docs/roadmap/` holds numbered design + implementation plans (`01-…` through `18-…`, e.g. `10-multicity-core-refactor-design.md`); `docs/交付物完备性审查.md` and `docs/课程设计合理性审查.md` are delivery-completion audits. Every implementation source file carries a header line referencing its task: `# Ref: docs/spec/task.md (Task-ID: <ID>)`.

Code conventions actually in use: city/building/HVAC data is modeled as `@dataclass(frozen=True, slots=True)` (see `config/cities.py`); files use `from __future__ import annotations` and absolute package imports (`from air_conditioning_design.config.paths import ...`); raw IDF object injection goes through the `IdfObject` wrapper in `idf/io.py`. Tests avoid mocking path builds — they rely on the real local weather packages to exercise system builders end-to-end. No linter/formatter is configured; keep Black-compatible 4-space indentation.

## City config

New cities go in `config/cities.py` as a `CityConfig` dataclass with weather directory info. New systems go in `models/systems/` with a builder function registered in `simulation/runner.py::run_case()`.

## Key Research Context (from reference paper & teacher's DWG)

### Reference paper structure (第七组+暖通空调设计报告.docx)

The reference paper is titled **"基于不同气候分区的某办公楼中央空调系统设计"** from 2021级 students. Its structure:

1. **工程概况** — Building overview, indoor/outdoor design params, envelope parameters, room list & areas, cooling load theory
2. **广州多联机系统设计** (夏热冬暖) — Detailed design for Guangzhou
3. **武汉多联机系统设计** (夏热冬冷) — Detailed design for Wuhan
4. **北京多联机系统设计** (寒冷) — Detailed design for Beijing
5. **哈尔滨多联机系统设计** (严寒) — Detailed design for Harbin
6. **不同气候分区的技术方案对比及适宜性评价** — Cross-climate comparison

Each city chapter follows: 建筑概况 → 室内设计参数 → 室外设计参数 → 围护结构参数 → 负荷计算结果 → 空调系统设备选型与计算

### Building model (implemented)

The simulated building is a **2-story office** (Scheme B, ~911.4 m² total) modeled with **10 thermal zones** — 5 per floor, one per orientation plus a core: `ZF1_S/N/W/E/C` (floor 1) and `ZF2_S/N/W/E/C` (floor 2). Footprint 32.0 m × 14.24 m, 3.5 m floor-to-floor. Zone areas: perimeter zones 115.2 m² (S/N) or 25.3 m² (W/E), core 174.6 m². Floorplan is visualized from a DXF via `figures/` + `ezdxf`; zone geometry lives in `models/building_from_dxf.py`.

This is a thermal-zone abstraction of the teacher's reference DWG (AutoCAD 2024 / 天正暖通, in `example/`), which has many individual rooms per floor — the IDF maps those rooms onto the 5 orientation-based zones rather than modeling each room separately. Do not revert to the DOE reference medium office (4982 m²) — that was an earlier placeholder and has been replaced.

### Indoor design parameters
| Parameter | Value |
|-----------|-------|
| Office design temp/humidity | 26°C, 60% |
| Fresh air per person | 30 m³/(h·person) |
| Lighting power density | 10 W/m² |
| Equipment power density | 20 W/m² |
| Personnel density | 6 m²/person (whole-building 150 people, 4500 m³/h fresh air) |
| Occupancy hours | 10h (8:00-18:00) |

### City mapping to reference paper
| Our city | Reference city | Climate zone |
|----------|---------------|--------------|
| shenzhen (深圳) | 广州/Guangzhou | 夏热冬暖 |
| chengdu (成都) | 武汉/Wuhan | 夏热冬冷 |
| tianjin (天津) | 北京/Beijing | 寒冷 |
| shenyang (沈阳) | 哈尔滨/Harbin | 严寒 |

`chongqing` has weather + builders but is secondary to the 4-city core comparison above.