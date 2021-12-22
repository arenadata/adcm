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
