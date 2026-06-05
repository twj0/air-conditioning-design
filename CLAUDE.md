# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run a single EnergyPlus case:** `python scripts/run_energyplus_case.py --case-id <city>__<system>`
- **Parse results:** `python scripts/parse_tianjin_results.py --case-id <case_id>`
- **Parse per-system results:** `python scripts/parse_<city>_<system>_results.py`
- **Build city model:** `python scripts/build_<city>_<system>.py`
- **Run all tests:** `pytest`
- **Run single test:** `pytest tests/test_<name>.py -v`
- **Run tests matching pattern:** `pytest -k "<pattern>" -v`
- **Install package (editable):** `pip install -e ".[dev]"`
- **Build neutral mother model:** `python scripts/build_neutral_mother_model.py`
- **Build model figures:** `python -c "from air_conditioning_design.cli.build_model_figures import main; main()"`

## EnergyPlus Paths

EnergyPlus executable defaults to `D:/energyplus/2320/energyplus.exe`. Falls back to PATH lookup. Configure in `src/air-conditioning-design/air_conditioning_design/config/paths.py`.

## Project Architecture

### Package: `src/air-conditioning-design/air_conditioning_design/`

| Layer | Path | Responsibility |
|-------|------|----------------|
| **Config** | `config/` | Path constants, city definitions, case ID encoding/decoding |
| **IDF IO** | `idf/io.py` | Parse, filter, find, replace, write IDF objects (`IdfObject` dataclass) |
| **Models** | `models/` | IDF generation: neutral base model, city variants, system cases (ideal_loads, vrf, fcu_doas) |
| **Weather** | `weather/` | EPW/DDY manifest generation and loading per city |
| **Simulation** | `simulation/runner.py` | Orchestrates IDF generation + EnergyPlus subprocess execution |
| **Analysis** | `analysis/` | Parse eplusout.csv → summary CSVs for each system type |
| **Figures** | `figures/` | IDF floorplan visualization via ezdxf + matplotlib |
| **CLI** | `cli/` | Lightweight argument-parsing entry points called by `scripts/` |

### Key data flow

`case_id` format: `{city_id}__{system_id}` (e.g., `tianjin__vrf`, `shenzhen__fcu_doas`)

1. `run_case(case_id)` in `runner.py` splits the case ID, builds the city's IDF variant from the neutral mother model
2. Generates system-specific IDF objects (ideal_loads/vrf/fcu_doas builders in `models/systems/`)
3. Loads weather manifest for EPW path
4. Executes `energyplus --readvars -w <epw> -d <output_dir> <idf>`
5. Analysis scripts parse `eplusout.csv` → summary metrics (peak load, annual energy)

### City × System matrix

5 cities (shenyang, tianjin, chengdu, shenzhen, chongqing) × 3 systems (ideal_loads, vrf, fcu_doas) = 15 cases. City configs defined in `config/cities.py` with climate zone classification. Builder functions in `models/systems/` accept a city parameter and support all 5 cities; convenience scripts under `scripts/` exist for Tianjin, while `scripts/run_energyplus_case.py --case-id <city>__<system>` handles any case.

### Test pattern

Tests mirror the build/parse matrix: `test_build_<city>_<system>.py` and `test_parse_<city>_<system>_results.py`. These validate IDF generation and CSV parsing, not EnergyPlus execution (no EnergyPlus in CI).

### Paper

LaTeX source in `air-conditioning-design-paper/latex/` using `elsarticle` class. Sections in `sections/`, figures in `figures/`. Build with `latexmk` or your LaTeX toolchain.

### Scripts

`scripts/` are the primary user entry points — run from repo root. They adjust `sys.path` to import the core package. Each wraps a corresponding module in `cli/`.

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

### Building layout (from paper, ~2000m², 2 floors)

**First floor (1001-1009):** 行政办公大厅, 女卫, 男卫, 晒图室, 电梯厅(前室), 消防控制室, 大厅, 库房, 陈列室
**Second floor (2001-2013):** 监理档案资料室, 监理办公室, 设计办公室1, 设计办公室2, 女卫, 男卫, 小会议室, 候梯厅, 设计档案资料室, 库房, 休息室, (2 unnamed rooms)

### Indoor design parameters used in reference
| Parameter | Value |
|-----------|-------|
| Office design temp/humidity | 26°C, 60% |
| Fresh air per person | 30 m³/(h·person) |
| Lighting power density | 10 W/m² |
| Equipment power density | 15 W/m² |
| Window area | 5 m² (standard) |
| Door area | 1.6 m² (standard) |
| Personnel density | 10 m²/person |
| Occupancy hours | 10h (8:00-18:00) |

### Our city mapping to reference cities
| Our city | Reference city | Climate zone |
|----------|---------------|--------------|
| shenzhen (深圳) | 广州/Guangzhou | 夏热冬暖 |
| chengdu (成都) | 武汉/Wuhan | 夏热冬冷 |
| tianjin (天津) | 北京/Beijing | 寒冷 |
| shenyang (沈阳) | 哈尔滨/Harbin | 严寒 |

### Current gap
- Current project uses DOE reference medium office model (4982 m²) — much larger than teacher's building (~2000 m²)
- Teacher provided actual DWG drawing (AutoCAD 2024, 天正暖通 format) in `example/`
- DWG-to-DXF conversion blocked by sandbox; manual building definition from paper needed
- City-specific IDF variants (`models/cities/<city>/`) exist for all 5 cities. System builders in `models/systems/` work for all cities. Only the convenience `scripts/build_<city>_<system>.py` scripts are Tianjin-only — use `scripts/run_energyplus_case.py` for other cities.