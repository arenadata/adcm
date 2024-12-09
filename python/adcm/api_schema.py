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

_ID_REPLACE_MAP = {
    "{login_id}": "{audit_login_id}",
    "{operation_id}": "{audit_operation_id}",
    "{group_config_id}": "{config_group_id}",
    "{config_host_group_id}": "{config_group_id}",
}


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


def convert_pks_in_path_to_camel_case_ids(generator: SchemaGenerator, request: Request, public: bool, result: dict):
    _ = generator, request, public

    original_paths = result.pop("paths")
    new_paths = {}

    for path, description in original_paths.items():
        new_key = path.replace("_pk}", "_id}")
        altered_base_id = None

        # unoptimized section start
        if "{id}" in new_key:
            before, _ = new_key.split("{id}")
            *_, entry = before.rstrip("/").rsplit("/", maxsplit=1)
            altered_base_id = "{" + f"{entry.rstrip('s')}_id".replace("-", "_") + "}"

            new_key = new_key.replace("{id}", altered_base_id)

        altered_keys = {}
        if altered_base_id:
            altered_keys["id"] = _ID_REPLACE_MAP.get(altered_base_id, altered_base_id)[1:-1]

        # maybe use here regex to extract such keys
        for id_to_replace, replacement in _ID_REPLACE_MAP.items():
            if id_to_replace in new_key:
                altered_keys[id_to_replace[1:-1]] = replacement[1:-1]
                new_key = new_key.replace(id_to_replace, replacement)

        new_paths[_to_camel_case(new_key)] = _replace_pk_with_id_for_path_parameters(
            path_dict=description, replacements=altered_keys
        )
        # unoptimized section end

    result["paths"] = new_paths

    return result


def _to_camel_case(line: str) -> str:
    first, *rest = line.split("_")
    return f"{first}{''.join(map(str.capitalize, rest))}"


def _replace_pk_with_id_for_path_parameters(path_dict: dict, replacements: dict[str, str]) -> dict:
    for entry in path_dict.values():
        for param in entry.get("parameters", ()):
            if param["in"] != "path":
                continue

            param["name"] = param["name"].replace("pk", "id")
            param["name"] = replacements.get(param["name"], param["name"])

    return path_dict


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


def postprocess_hook_exclude_advanced_filters(generator: SchemaGenerator, request: Request, public: bool, result: dict):
    # This is postprocess hook for remove advanced filters from schema

    _ = generator, request, public

    paths = result.get("paths", {})

    for description in paths.values():
        if get_parameters := description.get("get", {}).get("parameters", []):
            new_parameters = []
            for param in get_parameters:
                if param["in"] == "query" and "__" not in param["name"]:
                    new_parameters.append(param)

            description["get"]["parameters"] = new_parameters

    return result
