import json
from typing import Any


def dict_json_get_or_create(path, field, value=None) -> Any:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if data.get(field) is None:
        data[field] = value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    return data[field]
