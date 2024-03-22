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
from itertools import chain
from typing import Iterable

from drf_spectacular.generators import SchemaGenerator
from rest_framework.request import Request

_REF_PREFIX = "#/components/schemas/"


def make_all_fields_required_in_response(generator: SchemaGenerator, request: Request, public: bool, result: dict):
    _ = generator, request, public

    schemas = result.get("components", {}).get("schemas", {})
    if not schemas:
        return result

    references_to_response_models = {
        response_dict.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", None)
        for response_dict in chain.from_iterable(
            chain.from_iterable(m.get("responses", {}).values() for m in methods_dict.values())
            for methods_dict in result.get("paths", {}).values()
        )
    } - {None}

    nested_models = (
        _make_all_properties_required(
            components=(
                _deref_component(schemas=schemas, component_ref=ref)
                for ref in references_to_response_models
                if ref.startswith(_REF_PREFIX)
            )
        )
        - references_to_response_models
    )

    if not nested_models:
        return result

    while (
        nested_models := _make_all_properties_required(
            components=(
                _deref_component(schemas=schemas, component_ref=ref)
                for ref in nested_models
                if ref.startswith(_REF_PREFIX)
            )
        )
        - references_to_response_models
        - nested_models
    ):
        continue

    return result


def _deref_component(schemas: dict, component_ref: str) -> dict | None:
    return schemas.get(component_ref.rsplit("/", maxsplit=1)[-1])


def _make_all_properties_required(components: Iterable[dict | None]) -> set[str]:
    nested_models = set()

    for response_component in components:
        if not (response_component and response_component.get("type") in ("object", "array")):
            continue

        if response_component["type"] == "array":
            _find_inner_component_links(node=response_component["items"], acc=nested_models)
            continue

        properties = response_component.get("properties")
        if not properties:
            continue

        if properties.get("results", {}).get("type") == "array":
            _find_inner_component_links(node=properties["results"]["items"], acc=nested_models)
            continue

        response_component["required"] = list(properties.keys())

        _find_inner_component_links(node=properties, acc=nested_models)

    return nested_models


def _find_inner_component_links(node: dict, acc: set[str]) -> set[str]:
    if "$ref" in node:
        acc.add(node["$ref"])
        return acc

    for inner in node.values():
        if isinstance(inner, dict):
            _find_inner_component_links(inner, acc=acc)

    return acc
