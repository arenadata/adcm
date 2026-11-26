# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections.abc import Iterable
from functools import reduce
from typing import Any


def get_nested(source: dict, path: Iterable[str]) -> Any:
    return reduce(dict.__getitem__, path, source)


def convert_keys_to_camel_case(value: Any) -> Any:
    if isinstance(value, dict):
        return {_to_camel_case(key): convert_keys_to_camel_case(item) for key, item in value.items()}

    if isinstance(value, list):
        return [convert_keys_to_camel_case(item) for item in value]

    return value


def _to_camel_case(value: str) -> str:
    first, *rest = value.split("_")
    return f"{first}{''.join(part.capitalize() for part in rest)}"
