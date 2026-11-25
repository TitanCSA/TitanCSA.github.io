"""Validate the published integration document with its public JSON schema."""

from pathlib import Path
import json

from jsonschema import Draft202012Validator, FormatChecker


dist = Path(__file__).resolve().parents[1] / "dist"
schema = json.loads((dist / "integration.schema.json").read_text(encoding="utf-8"))
manifest = json.loads((dist / "integration.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())
errors = list(validator.iter_errors(manifest))
for error in errors:
    location = ".".join(str(part) for part in error.absolute_path) or "integration"
    print(f"{location}: {error.message}")
if errors:
    raise SystemExit(1)
print("Integration manifest conforms to its public JSON schema.")
