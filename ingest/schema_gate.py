"""Maintainer-side gate; not a runtime dependency of either Python library."""
import json
from pathlib import Path

def validate_generation(repo,package):
    from jsonschema import Draft202012Validator,FormatChecker
    def validate(filename,path):
        schema=json.loads((repo/'schemas'/filename).read_text('utf-8'))
        checker=Draft202012Validator(schema,format_checker=FormatChecker())
        checker.validate(json.loads(path.read_text('utf-8')))
    d=repo/package
    validate('manifest.schema.json',d/'manifest.json')
    for p in d.glob('holidays_*.json'):validate(f'holidays.{package}.schema.json',p)
