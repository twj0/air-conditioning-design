# Ref: docs/spec/task.md (Task-ID: IMPL-MULTICITY-CORE-001)
from __future__ import annotations

from pathlib import Path

from air_conditioning_design.idf.io import IdfObject
from air_conditioning_design.models.common import (
    build_zone_maps,
    conditioned_zone_names,
    extract_design_objects,
    load_city_manifest,
)


def load_tianjin_manifest() -> dict[str, str]:
    return load_city_manifest("tianjin")


def extract_tianjin_design_objects(ddy_path: Path) -> list[IdfObject]:
    return extract_design_objects(ddy_path)
