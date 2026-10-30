"""Convert Pydantic models to JSON Schema accepted by Bedrock structured output."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from pydantic import BaseModel

# Bedrock structured output rejects many JSON Schema constraint keywords.
_STRIP_KEYS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "default",
        "title",
        "description",
    }
)


def _camel_schema_name(model: type[BaseModel]) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", model.__name__)
    if not name:
        name = "Output"
    return name[:64]


def _sanitize_node(node: Any) -> Any:
    if isinstance(node, list):
        return [_sanitize_node(item) for item in node]
    if not isinstance(node, dict):
        return node

    cleaned: dict[str, Any] = {}
    for key, value in node.items():
        if key in _STRIP_KEYS:
            continue
        cleaned[key] = _sanitize_node(value)

    if cleaned.get("type") == "object":
        cleaned["additionalProperties"] = False

    return cleaned


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        ref = node["$ref"]
        if ref.startswith("#/$defs/"):
            def_name = ref.removeprefix("#/$defs/")
            if def_name in defs:
                return _inline_refs(copy.deepcopy(defs[def_name]), defs)
        return node
    return {key: _inline_refs(value, defs) for key, value in node.items()}


def _inline_schema_defs(schema: dict[str, Any]) -> dict[str, Any]:
    defs = schema.get("$defs") or schema.get("definitions") or {}
    if not defs:
        return schema
    inlined = _inline_refs(copy.deepcopy(schema), defs)
    inlined.pop("$defs", None)
    inlined.pop("definitions", None)
    return inlined


def bedrock_json_schema(model: type[BaseModel]) -> tuple[str, dict[str, Any]]:
    """Return (schema_name, sanitized schema dict) for Bedrock ``outputConfig.textFormat``."""
    raw = copy.deepcopy(model.model_json_schema())
    sanitized = _sanitize_node(raw)
    if not isinstance(sanitized, dict):
        raise TypeError("Expected object root schema from Pydantic model")
    if sanitized.get("type") != "object":
        sanitized = {
            "type": "object",
            "properties": {"data": sanitized},
            "required": ["data"],
            "additionalProperties": False,
        }
    else:
        sanitized["additionalProperties"] = False
    sanitized = _inline_schema_defs(sanitized)
    return _camel_schema_name(model), sanitized


def bedrock_json_schema_string(model: type[BaseModel]) -> tuple[str, str]:
    """Return (schema_name, schema as JSON string) for the Converse API."""
    name, schema = bedrock_json_schema(model)
    return name, json.dumps(schema)
