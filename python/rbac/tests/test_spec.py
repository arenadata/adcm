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


import os
from pathlib import Path

import ruyaml
from django.conf import settings
from django.test import TestCase

MANDATORY_KEYS = ["name", "type", "module_name", "class_name"]

BUSINESS_PARAMETRISATION = [
    {"cluster"},
    {"cluster", "service"},
    {"cluster", "component"},
    {"cluster", "service", "component"},
    {"service"},
    {"service", "component"},
    {"component"},
    {"provider", "host"},
    {"provider"},
    {"host"},
    set(),
]


class TestRoleSpecification(TestCase):
    def setUp(self) -> None:
        with open(Path(os.path.dirname(__file__), "../upgrade/role_spec.yaml"), encoding=settings.ENCODING_UTF_8) as f:
            self.spec_data: dict = ruyaml.YAML().load(f)
        self.role_map: dict = {role["name"]: role for role in self.spec_data["roles"]}
        self.roots = self.role_map.copy()
        for value in self.role_map.values():
            if "child" in value:
                for child in value["child"]:
                    if child in self.roots:
                        del self.roots[child]

    def test_structure(self):
        self.assertIn("version", self.spec_data)
        self.assertIn("roles", self.spec_data)

    def test_mandatory_fields(self):
        for role in self.spec_data["roles"]:
            for key in MANDATORY_KEYS:
                self.assertIn(key, role)

    def test_children(self):
        for value in self.role_map.values():
            if "child" in value:
                for child in value["child"]:
                    self.assertIn(child, self.role_map)

    @staticmethod
    def _is_in_set(allowed: list[set[str]], value: set):
        for allowed_value in allowed:
            if allowed_value == value:
                return True

        return False

    def test_allowed_parametrization(self):
        for value in self.role_map.values():
            if "parametrized_by" in value:
                if value["type"] == "business":
                    self.assertTrue(self._is_in_set(BUSINESS_PARAMETRISATION, set(value["parametrized_by"])))

    def _tree_dive_in(self, roles: dict, visited: dict, path: list, role: dict, root):
        if role["name"] in visited:
            raise AssertionError(f'In the tree from "{root["name"]}" we got a cycle: {path}')

        visited[role["name"]] = True
        if "child" in role:
            for child_role in role["child"]:
                self._tree_dive_in(roles, visited.copy(), path + [child_role], roles[child_role], root)

    def test_acyclic(self):
        for value in self.roots.values():
            self._tree_dive_in(self.role_map, {}, [value["name"]], value, value)
