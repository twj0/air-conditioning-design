from pathlib import Path

import air_conditioning_design.simulation.runner as runner
from air_conditioning_design.config.paths import RESULTS_RAW_ROOT


def test_safe_reset_output_dir_retries_after_permission_error(monkeypatch) -> None:
    output_dir = RESULTS_RAW_ROOT / "_pytest_safe_reset_output_dir"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "placeholder.txt").write_text("locked", encoding="utf-8")

    real_rmtree = runner.shutil.rmtree
    call_count = {"value": 0}

    def flaky_rmtree(path: Path, onerror=None) -> None:
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise PermissionError(32, "The process cannot access the file", str(path))
        real_rmtree(path, onerror=onerror)

    monkeypatch.setattr(runner.shutil, "rmtree", flaky_rmtree)
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)

    runner._safe_reset_output_dir(output_dir)

    assert call_count["value"] == 2
    assert output_dir.exists()
    assert list(output_dir.iterdir()) == []


def test_run_case_supports_tianjin_fcu_doas(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_tianjin_fcu_doas"
    idf_path = tmp_path / "tianjin__fcu_doas.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_fcu_doas_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("tianjin__fcu_doas")

    assert built == ["tianjin"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "tianjin.epw") in commands[0]


def test_run_case_supports_chengdu_ideal_loads(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_chengdu_ideal_loads"
    idf_path = tmp_path / "chengdu__ideal_loads.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_ideal_loads_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("chengdu__ideal_loads")

    assert built == ["chengdu"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "chengdu.epw") in commands[0]


def test_run_case_supports_shenzhen_ideal_loads(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_shenzhen_ideal_loads"
    idf_path = tmp_path / "shenzhen__ideal_loads.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_ideal_loads_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("shenzhen__ideal_loads")

    assert built == ["shenzhen"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "shenzhen.epw") in commands[0]


def test_run_case_supports_shenyang_ideal_loads(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_shenyang_ideal_loads"
    idf_path = tmp_path / "shenyang__ideal_loads.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_ideal_loads_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("shenyang__ideal_loads")

    assert built == ["shenyang"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "shenyang.epw") in commands[0]


def test_run_case_supports_chengdu_vrf(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_chengdu_vrf"
    idf_path = tmp_path / "chengdu__vrf.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_vrf_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("chengdu__vrf")

    assert built == ["chengdu"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "chengdu.epw") in commands[0]


def test_run_case_supports_shenzhen_vrf(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_shenzhen_vrf"
    idf_path = tmp_path / "shenzhen__vrf.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_vrf_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("shenzhen__vrf")

    assert built == ["shenzhen"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "shenzhen.epw") in commands[0]


def test_run_case_supports_shenyang_vrf(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_shenyang_vrf"
    idf_path = tmp_path / "shenyang__vrf.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_vrf_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("shenyang__vrf")

    assert built == ["shenyang"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "shenyang.epw") in commands[0]


def test_run_case_supports_chengdu_fcu_doas(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_chengdu_fcu_doas"
    idf_path = tmp_path / "chengdu__fcu_doas.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_fcu_doas_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("chengdu__fcu_doas")

    assert built == ["chengdu"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "chengdu.epw") in commands[0]


def test_run_case_supports_shenzhen_fcu_doas(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_shenzhen_fcu_doas"
    idf_path = tmp_path / "shenzhen__fcu_doas.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_fcu_doas_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("shenzhen__fcu_doas")

    assert built == ["shenzhen"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "shenzhen.epw") in commands[0]


def test_run_case_supports_shenyang_fcu_doas(monkeypatch, tmp_path: Path) -> None:
    built: list[str] = []
    output_dir = RESULTS_RAW_ROOT / "_pytest_shenyang_fcu_doas"
    idf_path = tmp_path / "shenyang__fcu_doas.idf"
    idf_path.write_text("Version,23.2;", encoding="utf-8")

    def fake_builder(city_id: str) -> Path:
        built.append(city_id)
        return idf_path

    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "build_fcu_doas_case", fake_builder)
    monkeypatch.setattr(
        runner,
        "load_weather_manifest",
        lambda city_id: {"epw_path": str(tmp_path / f"{city_id}.epw")},
    )
    monkeypatch.setattr(runner, "system_model_path", lambda case_id: idf_path)
    monkeypatch.setattr(runner, "results_dir_for_case", lambda case_id: output_dir)
    monkeypatch.setattr(runner, "resolve_energyplus_executable", lambda: Path("energyplus"))
    monkeypatch.setattr(
        runner,
        "_safe_reset_output_dir",
        lambda path: path.mkdir(parents=True, exist_ok=True),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, check: commands.append(command),
    )

    result = runner.run_case("shenyang__fcu_doas")

    assert built == ["shenyang"]
    assert result == output_dir
    assert commands
    assert str(idf_path) in commands[0]
    assert str(tmp_path / "shenyang.epw") in commands[0]
