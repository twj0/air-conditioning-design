# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from pathlib import Path

from air_conditioning_design.models.base import neutralize_reference_model


def test_neutralize_reference_model_writes_output(tmp_path: Path) -> None:
    source = Path(r"D:/energyplus/2320/ExampleFiles/RefBldgMediumOfficeNew2004_Chicago.idf")
    target = tmp_path / "medium_office_neutral.idf"
    neutralize_reference_model(source, target)

    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert "Medium Office Neutral Base" in text
    assert "RunPeriodControl:SpecialDays" not in text
    assert "Site:Location" not in text
