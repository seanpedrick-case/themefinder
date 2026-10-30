import json

from themefinder.bedrock_schema import bedrock_json_schema, bedrock_json_schema_string
from themefinder.models import ThemeGenerationResponses, ThemeMappingResponses


def _all_objects_have_additional_properties_false(node) -> bool:
    if isinstance(node, dict):
        if node.get("type") == "object" and node.get("additionalProperties") is not False:
            return False
        return all(
            _all_objects_have_additional_properties_false(v) for v in node.values()
        )
    if isinstance(node, list):
        return all(_all_objects_have_additional_properties_false(i) for i in node)
    return True


def test_bedrock_schema_strips_numeric_constraints():
    name, schema = bedrock_json_schema(ThemeMappingResponses)
    assert name == "ThemeMappingResponses"
    dumped = json.dumps(schema)
    assert "minimum" not in dumped
    assert "maximum" not in dumped
    assert _all_objects_have_additional_properties_false(schema)


def test_bedrock_schema_round_trip_theme_mapping():
    sample = {
        "responses": [
            {"response_id": 1, "labels": ["Theme A"]},
            {"response_id": 2, "labels": ["Theme B", "Theme C"]},
        ]
    }
    _, schema = bedrock_json_schema(ThemeMappingResponses)
    assert schema["type"] == "object"
    parsed = ThemeMappingResponses.model_validate(sample)
    assert len(parsed.responses) == 2


def test_bedrock_schema_theme_generation():
    name, schema_str = bedrock_json_schema_string(ThemeGenerationResponses)
    assert name == "ThemeGenerationResponses"
    schema = json.loads(schema_str)
    assert schema["additionalProperties"] is False
    assert "responses" in schema.get("properties", {})
    assert "$defs" not in schema
    assert "$ref" not in schema_str


def test_bedrock_schema_inlines_item_properties():
    _, schema = bedrock_json_schema(ThemeGenerationResponses)
    items = schema["properties"]["responses"]["items"]
    assert items.get("type") == "object"
    assert "topic_label" in items.get("properties", {})
