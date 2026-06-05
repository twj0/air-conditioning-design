# GEMINI.md - Project Instructions and Context

This file serves as the definitive source of truth for the **AirConditioningDesign** repository. It outlines the project's purpose, architecture, development conventions, and runtime instructions.

---

## 1. Project Overview

This repository is built for the **"Refrigeration and Air Conditioning Course Design" (制冷空调课程设计)** project. It provides a spec-driven, highly structured, and automated workflow to model, simulate, analyze, and plot building energy performance across multiple Chinese cities and HVAC system alternatives.

The ultimate output of this repository includes:
1.  **A 12-case Simulation Matrix**: Built across **4 cities** and **3 HVAC systems** (1 baseline + 2 actual systems).
2.  **Academic/Technical Paper Support**: Automatic generation of high-quality report-ready CSV data and Matplotlib vector charts for the associated course design paper (under `air-conditioning-design-paper/`).

### 1.1 Core Comparison Questions
- **Load Variation**: How do the peak cooling/heating loads and annual energy needs of the same building shape vary across different climate zones?
- **HVAC Suitability**: How do `FCU+DOAS` (four-pipe Fan Coil + Dedicated Outdoor Air System) and `VRF + DOAS` (Variable Refrigerant Flow + Dedicated Outdoor Air System) compare in terms of energy consumption, efficiency, and suitability across these climates?

### 1.2 Target Cities & Climate Zones
1.  **Shenyang** (`shenyang`): Severe Cold (寒冷/严寒 - 寒冷IIC/A)
2.  **Tianjin** (`tianjin`): Cold (寒冷地区 - 寒冷IA)
3.  **Chengdu** (`chengdu`): Hot Summer Cold Winter (夏热冬冷地区)
4.  **Shenzhen** (`shenzhen`): Hot Summer Warm Winter (夏热冬暖地区)
*Note: Chongqing (`chongqing`) has weather profiles but the primary comparison revolves around the 4 core cities above.*

---

## 2. Directory Structure & Architecture

```text
AirConditioningDesign/
├── pyproject.toml                                      # Python package configuration & dependencies
├── README.md                                           # Project quickstart
├── air-conditioning-design-paper/                      # LaTeX academic paper & defense materials
│   ├── latex/                                          # LaTeX source code, section files, bibliography
│   │   ├── main.tex                                    # Main paper document
│   │   ├── sections/                                   # Paper chapters (intro, mathematical-model, etc.)
│   │   └── figures/                                    # Target destination for generated PDF/Vector figures
│   └── defenses/                                       # Defense PPT outlines, Beamer templates, Q&A briefs
├── src/air-conditioning-design/air_conditioning_design/ # Core Python package
│   ├── analysis/                                       # Results parsing, metric normalization, aggregation
│   ├── cli/                                            # Entrypoints for CLI scripts
│   ├── config/                                         # Configuration files (city specs, path constants)
│   │   ├── cities.py                                   # City Config Dataclasses (frozen, slots)
│   │   └── paths.py                                    # Centralized path routing for inputs, outputs, model templates
│   ├── idf/                                            # Low-level EnergyPlus Input Data File (IDF) parsing/manipulation
│   ├── models/                                         # Model generation logic (neutral base, city variants, HVAC branches)
│   ├── simulation/                                     # EnergyPlus subprocess runner
│   └── weather/                                        # Weather manifest and EPW/DDY cataloging
├── scripts/                                            # Thin user-facing execution wrappers
│   ├── project_paths.py                                # Dynamic sys.path injection helper
│   ├── run_energyplus_case.py                          # Subprocess EnergyPlus case caller
│   └── plot/                                           # Vector figure plotting and comparison data generation
├── data/
│   ├── raw/weather/                                    # Raw meteorological CSWD data (.epw, .ddy)
│   └── interim/                                        # Generated weather manifests
├── models/
│   ├── base/                                           # Shared neutral mother building template (Medium Office)
│   ├── cities/                                         # Derived city variant models (localized envelopes)
│   └── systems/                                        # Final branch IDF models (with ideal_loads, vrf, fcu_doas)
├── results/                                            # Ignored by Git. Populated on-demand during simulation runs
│   ├── raw/                                            # Raw EnergyPlus outputs (eplusout.csv, etc.) grouped by case_id
│   └── processed/                                      # Aggregated KPIs, normalized metrics, chart-ready CSV tables
└── tests/                                              # Pytest test suite covering model building, parsing, and data layers
```

---

## 3. Environment & Setup

### 3.1 Python Requirements
- **Python Version**: `>=3.11` (specified in `.python-version`)
- **Key Dependencies**:
  - `ezdxf>=1.3,<2` (DXF parsing/processing)
  - `matplotlib>=3.8,<4` (plotting and visualizations)
  - `pytest>=8.2,<9.0` (testing, under `dev` dependencies)

Initialize the environment and install in editable mode:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

### 3.2 EnergyPlus Installation & Configuration
The system leverages a direct `subprocess` call to EnergyPlus via Python.
- **Version Compatibility**: EnergyPlus `23.2`
- **Default Path Setup**: Ensure `D:/energyplus/2320/energyplus.exe` exists with `ExampleFiles/` present.
- **Alternative (PATH fallback)**: If not present at the default location, add the directory containing `energyplus.exe` to your system's `PATH`.

---

## 4. Key Workflows & CLI Commands

All primary tasks should be run from the root directory using the scripts provided. These scripts automatically resolve Python's `sys.path` via `scripts/project_paths.py`.

### 4.1 Weather Manifest Preparation
Generates local JSON manifests containing parsed paths and sizing data from local CSWD weather directories:
```powershell
python .\scripts\prepare_tianjin_weather.py
```

### 4.2 Executing EnergyPlus Simulation Cases
Runs a specific case in EnergyPlus. The input `case_id` follows the `{city_id}__{system_id}` template (double underscore).
```powershell
python .\scripts\run_energyplus_case.py --case-id tianjin__ideal_loads
```
*How it works*:
1.  Loads the city envelope model and local weather manifest.
2.  Generates the specified system model under `models/systems/{case_id}.idf` if it does not exist.
3.  Resets the target raw directory (`results/raw/{case_id}`) safely.
4.  Invokes: `energyplus --readvars -w <epw> -d <output_dir> <idf>`

### 4.3 Results Processing & Reporting
Parse EnergyPlus hourly outputs (`eplusout.csv`) to produce aggregated KPIs (e.g., peak loads, monthly/annual cooling, heating, system electricity, equipment sizing profiles):
```powershell
# Parse single-case results
python .\scripts\parse_tianjin_results.py --case-id tianjin__ideal_loads

# Compile complete 12-case comparison matrix CSVs (needed for report plotting)
python .\scripts\plot\generate_report_data.py
```
Output processed tables will be generated under `results/processed/`:
- `report_case_matrix.csv`
- `report_ideal_loads_comparison.csv`
- `report_system_energy_comparison.csv`
- `report_equipment_summary.csv`

### 4.4 Automated Figure Plotting
Generates LaTeX report-ready figures and places them directly into the academic paper's directory:
```powershell
python .\scripts\plot\plot_report_figures.py
```
This updates charts inside `air-conditioning-design-paper/latex/figures/` (e.g., `annual_ideal_loads_by_city.pdf`, `system_electricity_by_city.pdf`, etc.) instantly, eliminating manual copy-pasting of spreadsheet charts.

---

## 5. Development Conventions

To maintain consistency across the codebase, adhere strictly to these conventions:

### 5.1 Code Architecture & Design
- **Separation of Concerns**: Keep simulation, analysis, and data logic in `src/air-conditioning-design`. Keep `scripts/` as very thin wrapper entrypoints calling CLI modules.
- **Metadata Configuration**: Do not hardcode city parameters or envelope parameters. Update `src/air-conditioning-design/air_conditioning_design/config/cities.py` or `paths.py` instead.
- **Dataclasses**: When modeling city, building, or HVAC data, use frozen dataclasses with `slots=True` for memory efficiency and safety (e.g., `@dataclass(frozen=True, slots=True)`).
- **Imports**: Utilize absolute imports within the package (`from air_conditioning_design.config.paths import ...`). Use `__future__.annotations` on every file to support clean postponed type evaluations.
- **IDF Object Handling**: For raw IDF injection, utilize the `IdfObject` wrapper from `air_conditioning_design.idf.io`.

### 5.2 Task References
All implementation files and tests should reference their corresponding task specifications and Task-IDs in comments at the top of the file:
```python
# Ref: docs/spec/task.md (Task-ID: IMPL-REPORT-DATA-PLOTS-001)
```

### 5.3 Sizing and Case ID Naming Conventions
- **Case IDs**: Formed as `{city_id}__{system_id}` (e.g., `shenyang__vrf`, `chengdu__fcu_doas`). Always split and build using `split_case_id()` and `build_case_id()` helpers under `paths.py`.
- **System Alternatives**: Avoid preferring one over another in names or directories; keep `vrf` and `fcu_doas` as equal partners across the pipeline.

### 5.4 Testing Strategy
- All logic changes or additions (such as adding cities, systems, or reporting parsers) must have corresponding unit tests in the `tests/` directory.
- Run the full test suite using:
  ```powershell
  pytest
  ```
- Tests must pass cleanly without warning suppression hacks.
- Mocking is generally avoided for core path builds; instead, rely on the provided local weather packages to run real system tests where possible.
