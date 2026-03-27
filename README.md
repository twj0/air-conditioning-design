# AirConditioningDesign（空调系统方案 + EnergyPlus 仿真）

本项目用于基于 **EnergyPlus** 对办公建筑（`Medium Office` 原型）进行多城市、多系统方案的建模与仿真，并用 **Python** 自动化完成：

- 生成/改造 IDF（城市设计日对象、系统对象等）
- 调用 EnergyPlus 批量运行 case
- 解析输出结果（如 `eplusout.csv`）并生成汇总 CSV/报告数据

> 备注：本仓库包含天气数据包、已生成的系统 IDF、以及用于复现实验的脚本。`results/` 目录被 `.gitignore` 忽略，运行后会在本地生成。

---

## 1. 运行环境

- **Python**：`3.11`（见 `.python-version`）
- **EnergyPlus**：建议 23.2（代码默认路径指向 `D:/energyplus/2320/energyplus.exe`）

### 1.1 Python 依赖

依赖声明位于 `pyproject.toml`。

- 运行依赖：`matplotlib`
- 开发依赖（可选）：`pytest`

建议使用虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .
```

如果你需要运行测试：

```powershell
python -m pip install -e ".[dev]"
pytest
```

---

## 2. EnergyPlus 安装与路径配置（关键）

项目运行 EnergyPlus 的方式是：在 Python 中通过 `subprocess` 调用 EnergyPlus 可执行文件。

默认的 EnergyPlus 路径解析逻辑在：

- `src/air-conditioning-design/air_conditioning_design/config/paths.py`

其中：

- 默认可执行文件路径：`D:/energyplus/2320/energyplus.exe`
- 如果默认路径不存在，会尝试在 `PATH` 中查找 `energyplus`

### 2.1 你需要做什么

- **方式 A（推荐）**：把 EnergyPlus 安装到 `D:/energyplus/2320/`，确保存在：
  - `D:/energyplus/2320/energyplus.exe`
  - `D:/energyplus/2320/ExampleFiles/`

- **方式 B**：将 `energyplus.exe` 所在目录加入系统 `PATH`，确保命令行可直接运行：

```powershell
energyplus --version
```

> 注意：如果你采用方式 B，但不想放到 `D:/energyplus/2320/`，仍然可以运行（会走 `PATH` 查找）。

---

## 3. 项目目录结构（从 EnergyPlus 到 Python 仿真全链路）

```text
AirConditioningDesign/
  pyproject.toml
  src/air-conditioning-design/air_conditioning_design/   # 核心 Python 包
  scripts/                                               # 便捷脚本（直接可运行）
  data/
    raw/
      weather/                                           # 天气包（EPW/DDY）
    interim/                                             # 运行过程中生成的 manifest
  models/
    base/                                                # 中性母模型（neutral）
    cities/                                              # 城市变体模型（中间产物）
    systems/                                             # 最终可运行的系统 case（IDF）
  results/                                               # 仿真结果输出（被 gitignore）
  tests/
```

### 3.1 天气数据（EPW/DDY）

天气包根目录：

- `data/raw/weather/`

每个城市一个文件夹（示例）：

- `data/raw/weather/CHN_TJ_Tianjin/CHN_TJ_Tianjin.545270_CSWD/`
  - `... .epw`
  - `... .ddy`

天气数据来源链接记录在：

- `data/raw/weather/link.txt`

### 3.2 天气 manifest（Python 自动生成/复用）

为便于代码统一读取 EPW/DDY 路径，项目会为每个城市写入一个 `*_weather_manifest.json`：

- `data/interim/tianjin_weather_manifest.json`
- `data/interim/shenyang_weather_manifest.json`
- `data/interim/chengdu_weather_manifest.json`
- `data/interim/shenzhen_weather_manifest.json`

对应逻辑：

- `src/air-conditioning-design/air_conditioning_design/weather/catalog.py`
  - `write_weather_manifest(city_id)`
  - `load_weather_manifest(city_id)`（若不存在会自动生成）

### 3.3 模型（IDF）

- **母模型（neutral）**：`models/base/medium_office_neutral.idf`
- **城市变体模型**：`models/cities/<city_id>/medium_office_<city_id>.idf`
- **系统 case（最终仿真入口 IDF）**：`models/systems/<case_id>.idf`

其中 `case_id` 约定：

- 格式：`{city_id}__{system_id}`（双下划线分隔）
- 例如：
  - `tianjin__ideal_loads`
  - `tianjin__vrf`
  - `tianjin__fcu_doas`

case id 的拼装/解析在：

- `src/air-conditioning-design/air_conditioning_design/config/paths.py`
  - `build_case_id()`
  - `split_case_id()`

### 3.4 仿真输出（results）

运行某个 case 会把 EnergyPlus 的输出写入：

- `results/raw/<case_id>/`

并且该目录会在运行前被安全清空（仅允许清空 `results/raw` 子目录）：

- `src/air-conditioning-design/air_conditioning_design/simulation/runner.py`
  - `_safe_reset_output_dir()`

结果汇总（示例：Ideal Loads）会写入：

- `results/processed/<case_id>_summary.csv`

---

## 4. 如何运行：从准备天气到跑 EnergyPlus

项目提供两套入口：

- **推荐**：直接运行根目录 `scripts/` 下的脚本（已处理 `sys.path`）
- **进阶**：以包方式运行 `src/` 下的 CLI（需要你自己处理包导入/安装）

### 4.1（可选）准备天气 manifest

一般情况下，运行 case 时会自动读取并生成 manifest。

你也可以手动生成天津天气 manifest：

```powershell
python .\scripts\prepare_tianjin_weather.py
```

对应 CLI：

- `src/air-conditioning-design/air_conditioning_design/cli/prepare_tianjin_weather.py`

### 4.2 运行 EnergyPlus case

运行某个 case（示例：天津 Ideal Loads）：

```powershell
python .\scripts\run_energyplus_case.py --case-id tianjin__ideal_loads
```

该命令的核心逻辑：

- 入口 CLI：`src/air-conditioning-design/air_conditioning_design/cli/run_energyplus_case.py`
- 仿真运行器：`src/air-conditioning-design/air_conditioning_design/simulation/runner.py`
  - `run_case(case_id)`

`run_case()` 会做三件事：

1. 根据 `case_id` 生成系统 IDF（若系统属于 `ideal_loads`/`vrf`/`fcu_doas`）
2. 读取城市天气 manifest，拿到 `.epw` 路径
3. 调用 EnergyPlus：

```text
energyplus --readvars -w <epw> -d <output_dir> <idf>
```

---

## 5. 系统方案说明（当前支持）

系统方案由 `system_id` 决定，当前实现了：

- `ideal_loads`
  - 生成逻辑：`air_conditioning_design/models/systems/ideal_loads.py`
  - 主要用于获得峰值冷负荷、年冷/热负荷等
- `vrf`
  - 生成逻辑：`air_conditioning_design/models/systems/vrf.py`
  - 使用 EnergyPlus 示例文件中的 DOAS+VRF 作为 donor，并做了若干 retune
- `fcu_doas`
  - 生成逻辑：`air_conditioning_design/models/systems/fcu_doas.py`
  - 使用 DOAS + 四管制风机盘管系统的 donor，并做了若干 retune

可用城市见：

- `src/air-conditioning-design/air_conditioning_design/config/cities.py`
  - `shenyang / tianjin / chengdu / shenzhen`

---

## 6. 结果解析与汇总（Python）

### 6.1 Ideal Loads 汇总

天津 Ideal Loads 汇总脚本：

```powershell
python .\scripts\parse_tianjin_results.py --case-id tianjin__ideal_loads
```

对应逻辑：

- `src/air-conditioning-design/air_conditioning_design/analysis/ideal_loads_summary.py`
  - 从 `results/raw/<case_id>/eplusout.csv` 读取逐时结果
  - 识别关键词列：
    - `Zone Ideal Loads Supply Air Sensible Cooling Rate`
    - `Zone Ideal Loads Supply Air Sensible Heating Rate`
  - 生成：
    - `peak_cooling_load`（kW）
    - `annual_cooling_load`（kWh）
    - `annual_heating_load`（kWh）
    - 以及单位面积指标等

---

## 7. 常见问题（Troubleshooting）

### 7.1 找不到 EnergyPlus

报错类似：`EnergyPlus executable was not found at the default path or on PATH.`

处理：

- 检查 `D:/energyplus/2320/energyplus.exe` 是否存在
- 或将 EnergyPlus 安装目录加入 `PATH`，确保 `energyplus` 可直接运行

### 7.2 天气文件缺失（EPW/DDY）

`build_weather_manifest()` 会检查 `.epw/.ddy` 是否存在；缺失会抛 `FileNotFoundError`。

处理：

- 确认 `data/raw/weather/<城市目录>/<包目录>/` 下确实有 `.epw/.ddy`
- 天气包来源参考：`data/raw/weather/link.txt`

### 7.3 `results/` 没有提交到仓库

这是正常的：`results/` 在 `.gitignore` 中被忽略。你需要在本地运行仿真生成结果。

---

## 8. 快速复现（推荐流程）

以天津为例：

1. 配置 EnergyPlus（见第 2 节）
2. 安装 Python 依赖（见第 1 节）
3. 运行仿真：

```powershell
python .\scripts\run_energyplus_case.py --case-id tianjin__ideal_loads
```

4. 解析汇总：

```powershell
python .\scripts\parse_tianjin_results.py --case-id tianjin__ideal_loads
```

完成后你将看到：

- `results/raw/tianjin__ideal_loads/`（EnergyPlus 原始输出）
- `results/processed/tianjin__ideal_loads_summary.csv`（汇总 CSV）

---

## 9. 开发者入口（可选）

如果你要在代码层面扩展：

- **新增城市**：在 `config/cities.py` 增加 `CityConfig`（需要对应天气包目录/文件名）
- **新增系统方案**：在 `models/systems/` 添加 builder，并在 `simulation/runner.py::run_case()` 中注册
- **生成/管理路径**：统一在 `config/paths.py` 中维护（`models/`、`data/`、`results/`）
