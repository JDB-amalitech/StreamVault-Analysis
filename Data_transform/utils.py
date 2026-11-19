import json


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def write_json(path, obj):
    path.write_text(
        json.dumps(obj, indent=4, ensure_ascii=False), encoding="utf-8"
    )