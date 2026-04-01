import shutil
from pathlib import Path

from air_conditioning_design.cli.build_model_figures import (
    BASE_FIGURE_NAME,
    BUILDING_STRUCTURE_FIGURE_NAME,
    FCU_DOAS_FIGURE_NAME,
    VRF_DOAS_FIGURE_NAME,
    ZONING_FIGURE_NAME,
    build_model_figures,
)
from air_conditioning_design.figures.annotations import build_floor_annotations
from air_conditioning_design.figures.geometry import load_floorplan_geometry
from air_conditioning_design.figures.overlays import build_fcu_doas_overlay, build_vrf_doas_overlay

FIXTURE_DXF = Path("tests/fixtures/tianjin_ideal_loads_eplusout.dxf")
FIXTURE_IDF = Path("models/systems/tianjin__ideal_loads.idf")


def test_build_model_figures_writes_base_and_zoning_svg_and_pdf(
    monkeypatch, tmp_path: Path
) -> None:
    case_id = "tianjin__ideal_loads"
    case_root = tmp_path / "raw" / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURE_DXF, case_root / "eplusout.dxf")

    monkeypatch.setattr(
        "air_conditioning_design.cli.build_model_figures.results_dir_for_case",
        lambda requested_case_id: case_root,
    )

    output_root = tmp_path / "figures"
    outputs = build_model_figures(
        case_id,
        figure_set="all",
        output_root=output_root,
        file_formats=("svg", "pdf"),
    )

    assert [path.name for path in outputs] == [
        f"{BASE_FIGURE_NAME}.svg",
        f"{ZONING_FIGURE_NAME}.svg",
        f"{BUILDING_STRUCTURE_FIGURE_NAME}.svg",
        f"{BASE_FIGURE_NAME}.pdf",
        f"{ZONING_FIGURE_NAME}.pdf",
        f"{BUILDING_STRUCTURE_FIGURE_NAME}.pdf",
    ]
    assert outputs[0].read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert outputs[1].read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert outputs[2].read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert outputs[3].read_bytes().startswith(b"%PDF")
    assert outputs[4].read_bytes().startswith(b"%PDF")
    assert outputs[5].read_bytes().startswith(b"%PDF")


def test_build_model_figures_writes_vrf_overlay(monkeypatch, tmp_path: Path) -> None:
    case_id = "tianjin__vrf"
    case_root = tmp_path / "raw" / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURE_DXF, case_root / "eplusout.dxf")

    monkeypatch.setattr(
        "air_conditioning_design.cli.build_model_figures.results_dir_for_case",
        lambda requested_case_id: case_root,
    )

    output_root = tmp_path / "figures"
    outputs = build_model_figures(
        case_id,
        figure_set="vrf_doas",
        output_root=output_root,
        file_formats=("svg",),
    )

    assert [path.name for path in outputs] == [f"{VRF_DOAS_FIGURE_NAME}.svg"]
    assert outputs[0].read_text(encoding="utf-8").lstrip().startswith("<?xml")


def test_build_model_figures_writes_fcu_overlay(monkeypatch, tmp_path: Path) -> None:
    case_id = "tianjin__fcu_doas"
    case_root = tmp_path / "raw" / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURE_DXF, case_root / "eplusout.dxf")

    monkeypatch.setattr(
        "air_conditioning_design.cli.build_model_figures.results_dir_for_case",
        lambda requested_case_id: case_root,
    )

    output_root = tmp_path / "figures"
    outputs = build_model_figures(
        case_id,
        figure_set="fcu_doas",
        output_root=output_root,
        file_formats=("svg",),
    )

    assert [path.name for path in outputs] == [f"{FCU_DOAS_FIGURE_NAME}.svg"]
    assert outputs[0].read_text(encoding="utf-8").lstrip().startswith("<?xml")


def test_system_overlays_expose_multiview_metadata() -> None:
    annotations = build_floor_annotations(FIXTURE_IDF, geometry=load_floorplan_geometry(FIXTURE_DXF))
    vrf_overlay = build_vrf_doas_overlay(annotations)
    fcu_overlay = build_fcu_doas_overlay(annotations)

    assert vrf_overlay.system_type == "vrf_doas"
    assert vrf_overlay.roof_equipment_labels == ("DOAS AHU", "VRF ODU bank")
    assert vrf_overlay.section_service_label == "Refrigerant riser"
    assert fcu_overlay.system_type == "fcu_doas"
    assert fcu_overlay.roof_equipment_labels == ("DOAS AHU",)
    assert fcu_overlay.section_service_label == "CHW/HW riser"


def test_build_model_figures_writes_requested_paper_export(
    monkeypatch, tmp_path: Path
) -> None:
    case_id = "tianjin__ideal_loads"
    case_root = tmp_path / "raw" / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURE_DXF, case_root / "eplusout.dxf")

    monkeypatch.setattr(
        "air_conditioning_design.cli.build_model_figures.results_dir_for_case",
        lambda requested_case_id: case_root,
    )

    output_root = tmp_path / "figures"
    paper_root = tmp_path / "paper"
    outputs = build_model_figures(
        case_id,
        figure_set="base",
        output_root=output_root,
        paper_output_root=paper_root,
        file_formats=("pdf",),
    )

    assert [path.name for path in outputs] == [
        f"{BASE_FIGURE_NAME}.pdf",
        f"{BASE_FIGURE_NAME}.pdf",
    ]
    assert (paper_root / f"{BASE_FIGURE_NAME}.pdf").exists()


def test_build_model_figures_writes_building_structure_figure(tmp_path: Path) -> None:
    outputs = build_model_figures(
        "tianjin__ideal_loads",
        figure_set="building_structure",
        output_root=tmp_path / "figures",
        file_formats=("svg",),
    )

    assert [path.name for path in outputs] == [f"{BUILDING_STRUCTURE_FIGURE_NAME}.svg"]
    assert outputs[0].read_text(encoding="utf-8").lstrip().startswith("<?xml")
