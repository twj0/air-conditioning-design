from air_conditioning_design.config import paths


def test_figure_paths_resolve_under_repository_layout() -> None:
    assert paths.RESULTS_FIGURES_ROOT == paths.RESULTS_PROCESSED_ROOT / "figures"
    assert paths.PAPER_FIGURES_ROOT == (
        paths.REPO_ROOT / "air-conditioning-design-paper" / "latex" / "figures"
    )
    assert paths.results_figure_path("medium_office_typical_floor_base") == (
        paths.RESULTS_FIGURES_ROOT / "medium_office_typical_floor_base.svg"
    )
    assert paths.paper_figure_path("medium_office_typical_floor_base") == (
        paths.PAPER_FIGURES_ROOT / "medium_office_typical_floor_base.pdf"
    )


def test_ensure_directories_creates_figure_roots() -> None:
    paths.ensure_directories()

    assert paths.RESULTS_FIGURES_ROOT.exists()
    assert paths.RESULTS_FIGURES_ROOT.is_dir()
    assert paths.PAPER_FIGURES_ROOT.exists()
    assert paths.PAPER_FIGURES_ROOT.is_dir()
