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

# pylint:disable=redefined-outer-name

import os
import pytest
import ruyaml

MANDATORY_KEYS = ["name", "type", "module_name", "class_name"]

BUSINESS_PARAMETRISATION = [
    set(["cluster"]),
    set(["cluster", "service"]),
    set(["cluster", "component"]),
    set(["cluster", "service", "component"]),
    set(["service"]),
    set(["service", "component"]),
    set(["provider", "host"]),
    set(["provider"]),
    set(["host"]),
    set([]),
]


@pytest.fixture(scope="module")
def spec_data():
    """Read role_spec.yaml and parse it to structure"""
    with open(os.path.join(os.path.dirname(__file__), "role_spec.yaml"), encoding="utf-8") as f:
        return ruyaml.YAML().load(f)


@pytest.fixture(scope="module")
def role_map(spec_data):
    """Make a map from spec_data based on name"""
    result = {}
    for r in spec_data["roles"]:
        result[r["name"]] = r
    return result


@pytest.fixture(scope="module")
def roots(role_map: dict):
    roots = role_map.copy()
    for v in role_map.values():
        if "child" in role_map:
            for c in role_map["child"]:
                if c in roots:
                    del roots[c]
    return roots


def test_structure(spec_data):
    """Test that role spec is map and has keys version and roles"""
    assert "version" in spec_data
    assert "roles" in spec_data


def test_mandatory_fields(spec_data):
    """All roles must have mandatory fields"""
    for r in spec_data["roles"]:
        for mk in MANDATORY_KEYS:
            assert mk in r, f'There is no field "{mk}" in  role {r["name"]}'


def test_childs(role_map: map):
    """Check that all children defined"""
    for k, v in role_map.items():
        if "child" in v:
            for ch in v["child"]:
                assert ch in role_map, f'There is no such role "{ch}". Error in role "{k}"'


def test_leaf_parametriation(spec_data: list):
    """Leaf should has no more than one parametrized_by elements.
    That is a restriction of apply role function.
    """
    for r in spec_data["roles"]:
        if not "child" in r or not r["child"]:
            if "parametrized_by" in r:
                assert (
                    len(r["parametrized_by"]) < 2
                ), f'Role entry {r["name"]} has more then one parametrized_by entry'


def is_in_set(allowed: list[set], value: set):
    for s in allowed:
        if s == value:
            return True
    return False


def test_allowed_parametrization(role_map: dict):
    """Check that parametrize_by_type for business permissions is in allowed list."""
    for k, v in role_map.items():
        if "parametrized_by" in v:
            if v["type"] == "business":
                assert is_in_set(
                    BUSINESS_PARAMETRISATION, set(v["parametrized_by"])
                ), f'Wrong parametrization for role "{k}". See ADCM-2498 for more information.'


class Visited(Exception):
    pass


def tree_dive_in(roles: dict, visited: dict, path: list, role: dict, root):
    if role["name"] in visited:
        raise AssertionError(f'In the tree from \"{root["name"]}\" we got a cycle: {path}')
    visited[role["name"]] = True
    if "child" in role:
        for c in role["child"]:
            tree_dive_in(roles, visited.copy(), path + [c], roles[c], root)


def test_acyclic(role_map: dict, roots: dict):
    """Check that role specification is a DAG"""
    for v in roots.values():
        tree_dive_in(role_map, dict(), [v["name"]], v, v)


EXCLUDE = {"ADCM User": True, "Cluster Administrator": True, "Service Administrator": True}


def is_exclude(name: str) -> bool:
    try:
        return EXCLUDE[name]
    except KeyError:
        return False


def parametrized_by(role: dict) -> list:
    if "parametrized_by" in role:
        return role["parametrized_by"]
    return []


def tree_sum(role_map: dict, role: dict) -> list:
    role_params = parametrized_by(role)
    if "child" in role:
        child_params = []
        for c in role['child']:
            child_params.extend(tree_sum(role_map, role_map[c]))
        if not is_exclude(role["name"]):
            assert set(child_params) == set(
                role_params
            ), f'For role \"{role["name"]}\" parametrize_by is not a sum of child parametrization: {set(role_params)} != {set(child_params)}'
    return role_params


def test_parametrization_sum(roots: dict, role_map: dict):
    for v in roots.values():
        tree_sum(role_map, v)
