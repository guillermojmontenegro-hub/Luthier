from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def _schema_path(filename: str) -> Path:
    return SCHEMA_DIR / filename


def load_schema(filename: str) -> dict[str, Any]:
    return json.loads(_schema_path(filename).read_text(encoding="utf-8"))


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(value, float)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return True


def _validate(instance: Any, schema: dict[str, Any], path: str) -> None:
    expected_type = schema.get("type")
    if expected_type and not _matches_type(instance, expected_type):
        actual_type = type(instance).__name__
        raise ValueError(f"{path} should be `{expected_type}`, got `{actual_type}`")

    if "enum" in schema and instance not in schema["enum"]:
        raise ValueError(f"{path} should be one of {schema['enum']}, got {instance!r}")

    if expected_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional_properties = schema.get("additionalProperties", True)

        for field in required:
            if field not in instance:
                raise ValueError(f"{path} is missing required field `{field}`")

        if additional_properties is False:
            for field in instance:
                if field not in properties:
                    raise ValueError(f"{path} contains unsupported field `{field}`")

        for field, value in instance.items():
            child_schema = properties.get(field)
            if child_schema is None:
                continue
            _validate(value, child_schema, f"{path}.{field}")
        return

    if expected_type == "array":
        item_schema = schema.get("items")
        if not item_schema:
            return
        for index, item in enumerate(instance):
            _validate(item, item_schema, f"{path}[{index}]")


def validate_instance(instance: Any, schema: dict[str, Any], *, name: str) -> None:
    _validate(instance, schema, name)


def validate_profile_payload(profile: dict[str, Any]) -> None:
    validate_instance(profile, load_schema("profile.schema.json"), name="profile")


def validate_report_payload(report: dict[str, Any]) -> None:
    validate_instance(report, load_schema("report.schema.json"), name="report")
