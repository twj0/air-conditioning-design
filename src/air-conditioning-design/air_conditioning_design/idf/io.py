# Ref: docs/spec/task.md (Task-ID: IMPL-TIANJIN-001)
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class IdfObject:
    class_name: str
    fields: list[str]

    @property
    def name(self) -> str | None:
        if not self.fields:
            return None
        value = self.fields[0].strip()
        return value or None


def _strip_inline_comment(line: str) -> str:
    if "!" in line:
        return line.split("!", 1)[0].rstrip()
    return line.rstrip()


def parse_idf_objects(text: str) -> list[IdfObject]:
    objects: list[IdfObject] = []
    buffer: list[str] = []

    for raw_line in text.splitlines():
        line = _strip_inline_comment(raw_line).strip()
        if not line:
            continue

        buffer.append(line)
        if ";" not in line:
            continue

        object_text = " ".join(buffer)
        buffer.clear()
        object_text = object_text.rstrip(";").strip()
        if not object_text or "," not in object_text:
            continue

        class_name, remainder = object_text.split(",", 1)
        fields = [field.strip() for field in remainder.split(",")]
        objects.append(IdfObject(class_name.strip(), fields))

    return objects


def load_idf(path: Path) -> list[IdfObject]:
    return parse_idf_objects(path.read_text(encoding="utf-8", errors="ignore"))


def dump_idf_object(idf_object: IdfObject) -> str:
    lines = [f"  {idf_object.class_name},"]
    for field in idf_object.fields[:-1]:
        if field:
            lines.append(f"    {field},")
        else:
            lines.append("    ,")

    last_field = idf_object.fields[-1] if idf_object.fields else ""
    if last_field:
        lines.append(f"    {last_field};")
    else:
        lines.append("    ;")
    return "\n".join(lines)


def write_idf(path: Path, objects: list[IdfObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n\n".join(dump_idf_object(obj) for obj in objects) + "\n"
    path.write_text(body, encoding="utf-8")


def filter_objects(
    objects: list[IdfObject],
    *,
    remove_classes: set[str] | None = None,
    remove_prefixes: tuple[str, ...] = (),
    remove_name_prefixes: tuple[str, ...] = (),
) -> list[IdfObject]:
    remove_classes = remove_classes or set()
    filtered: list[IdfObject] = []

    for obj in objects:
        if obj.class_name in remove_classes:
            continue
        if any(obj.class_name.startswith(prefix) for prefix in remove_prefixes):
            continue
        if obj.name and any(obj.name.startswith(prefix) for prefix in remove_name_prefixes):
            continue
        filtered.append(obj)

    return filtered


def find_objects(objects: list[IdfObject], class_name: str) -> list[IdfObject]:
    return [obj for obj in objects if obj.class_name == class_name]


def replace_object(
    objects: list[IdfObject], class_name: str, replacement: IdfObject
) -> list[IdfObject]:
    replaced = False
    new_objects: list[IdfObject] = []

    for obj in objects:
        if obj.class_name == class_name and not replaced:
            new_objects.append(replacement)
            replaced = True
            continue
        new_objects.append(obj)

    if not replaced:
        new_objects.append(replacement)
    return new_objects

