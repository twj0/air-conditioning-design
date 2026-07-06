# Repository Guidelines

## Project Structure & Module Organization

This repository models and simulates air-conditioning system schemes with EnergyPlus.

- `src/air-conditioning-design/air_conditioning_design/`: core Python package.
  - `models/`: building, city, and system IDF builders.
  - `simulation/`: EnergyPlus execution logic.
  - `analysis/`: result summaries and plotting data.
  - `config/`: shared paths and city metadata.
  - `cli/`: package-level command entry points.
- `scripts/`: runnable convenience scripts that set up imports for local use.
- `data/raw/weather/`: EPW/DDY weather packages; `data/interim/` stores generated manifests.
- `models/base/`, `models/cities/`, `models/systems/`: generated or reusable IDF model assets.
- `results/`: local simulation outputs; this directory is gitignored.
- `tests/`: pytest suite mirroring build, parse, weather, figure, and simulation behavior.
- `air-conditioning-design-paper/`: LaTeX/report assets.

## Build, Test, and Development Commands

- `uv sync --extra dev`: create/update the locked development environment.
- `python -m pip install -e ".[dev]"`: editable install when not using uv.
- `pytest`: run the full test suite.
- `python .\scripts\prepare_tianjin_weather.py`: generate or refresh Tianjin weather manifest data.
- `python .\scripts\run_energyplus_case.py --case-id tianjin__ideal_loads`: run one EnergyPlus case.
- `python .\scripts\parse_tianjin_results.py --case-id tianjin__ideal_loads`: summarize a completed case into `results/processed/`.

EnergyPlus is expected at `D:/energyplus/2320/energyplus.exe`, or available as `energyplus` on `PATH`.

## Coding Style & Naming Conventions

Use Python 3.11 and standard Python naming: modules/functions/variables in `snake_case`, classes in `PascalCase`, constants in `UPPER_SNAKE_CASE`. Keep source files importable from the package and use `scripts/` only as thin local runners. Prefer `pathlib.Path` and centralize repository paths in `air_conditioning_design/config/paths.py`. No formatter or linter is configured in `pyproject.toml`; keep formatting Black-compatible with 4-space indentation.

## Testing Guidelines

Tests use pytest and follow `tests/test_*.py` naming. Add or update tests when changing builders, parsers, path logic, weather manifests, figures, or simulation behavior. Use targeted runs while developing, for example `pytest tests/test_run_energyplus_case.py`, then run `pytest` before committing.

## Commit & Pull Request Guidelines

Recent history uses concise scoped messages such as `feat(model, latex): ...`, `docs(latex): ...`, and `chore(latex, models): ...`. Prefer `<type>(<scope>): <summary>` with types like `feat`, `fix`, `docs`, `test`, or `chore`. For pull requests, include the changed scenario or system, commands run, generated outputs affected under `models/` or `results/`, and screenshots/PDF snippets when changing paper or figure assets.

## Security & Configuration Tips

Do not commit machine-specific paths, large generated `results/` outputs, or local virtual environments. Document any new external dependency, weather package, or EnergyPlus version assumption in `README.md`.
