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


def extract_from_nested_structure(data: list, value_path: str) -> list:
    """
    Extract values from nested structure.

    Example:

    >>> response = {
    ...     "results": [
    ...         {
    ...             "id": 1,
    ...             "prototype": {"name": "AAA", "status": None},
    ...             "concerns": [{"id": 3}, {"id": 4}],
    ...             "items": [
    ...                 {"stuff": [{"id": 3}, {"id": 432}]},
    ...                 {"stuff": [{"id": 4}]},
    ...             ],
    ...         }
    ...     ]
    ... }
    >>> results = response["results"]
    >>> extract_from_nested_structure(results, "id")
    [1]
    >>> extract_from_nested_structure(results, "prototype.name")
    ['AAA']
    >>> extract_from_nested_structure(results, "prototype.status")
    [None]
    >>> extract_from_nested_structure(results, "concerns.id")
    [3, 4]
    >>> extract_from_nested_structure(results, "items.stuff.id")
    [3, 432, 4]
    """

    keys = value_path.split(".")

    def _extract(current, path) -> list:
        if not path:
            return [current]

        if isinstance(current, list):
            result = []
            for item in current:
                result.extend(_extract(item, path))
            return result

        if not isinstance(current, dict):
            return []

        key = path[0]
        if key not in current:
            return []

        next_value = current[key]
        if next_value is None and path[1:]:
            return [next_value]

        return _extract(next_value, path[1:])

    result = []
    for item in data:
        result.extend(_extract(item, keys))

    return result
