import json
from typing import Any


def dict_json_get_or_create(path: str, field: str, value: Any = None) -> Any:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if field not in data:
        data[field] = value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    return data[field]
