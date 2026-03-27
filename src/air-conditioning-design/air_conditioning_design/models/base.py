# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

import json
from pathlib import Path

from air_conditioning_design.config.paths import (
    NEUTRAL_METADATA_PATH,
    NEUTRAL_MODEL_PATH,
    REFERENCE_MEDIUM_OFFICE_IDF,
    ensure_directories,
)
from air_conditioning_design.idf.io import (
    IdfObject,
    filter_objects,
    load_idf,
    replace_object,
    write_idf,
)


def neutralize_reference_model(source: Path, target: Path) -> Path:
    ensure_directories()
    objects = load_idf(source)
    filtered = filter_objects(
        objects,
        remove_classes={
            "Site:Location",
            "RunPeriodControl:DaylightSavingTime",
            "RunPeriodControl:SpecialDays",
            "Output:Table:SummaryReports",
            "OutputControl:Table:Style",
        },
        remove_prefixes=("SizingPeriod:", "Output:Variable"),
    )

    filtered = replace_object(
        filtered,
        "Building",
        IdfObject(
            "Building",
            [
                "Medium Office Neutral Base",
                "0.0000",
                "City",
                "0.0400",
                "0.2000",
                "FullInteriorAndExterior",
                "25",
                "6",
            ],
        ),
    )

    write_idf(target, filtered)
    NEUTRAL_METADATA_PATH.write_text(
        json.dumps(
            {
                "source_idf": str(source.resolve()),
                "target_idf": str(target.resolve()),
                "removed_classes": [
                    "Site:Location",
                    "RunPeriodControl:DaylightSavingTime",
                    "RunPeriodControl:SpecialDays",
                    "SizingPeriod:*",
                    "Output:Variable",
                    "Output:Table:SummaryReports",
                    "OutputControl:Table:Style",
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return target


def build_neutral_mother_model() -> Path:
    return neutralize_reference_model(REFERENCE_MEDIUM_OFFICE_IDF, NEUTRAL_MODEL_PATH)

