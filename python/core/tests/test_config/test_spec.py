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

from dataclasses import asdict

from core.config import spec
from core.tests.test_config.utils import ConfigTestCase

SpecHierarchyLevel = spec.SpecHierarchyLevel


class TestSpecification(ConfigTestCase):
    maxDiff = None

    def test_hierarchy_register_with_groups(self):
        param_names = (
            ("plain",),
            ("group-1",),
            ("group-1", "child"),
            ("group-1", "another"),
            ("after",),
            ("deeply",),
            ("deeply", "flag"),
            ("deeply", "nested"),
            ("deeply", "nested", "item"),
            ("deeply", "after"),
            ("control",),
        )

        expected_hierarhcy = SpecHierarchyLevel(
            fields=["plain", "group-1", "after", "deeply", "control"],
            child_groups={
                "group-1": SpecHierarchyLevel(
                    fields=["child", "another"],
                ),
                "deeply": SpecHierarchyLevel(
                    fields=["flag", "nested", "after"], child_groups={"nested": SpecHierarchyLevel(fields=["item"])}
                ),
            },
        )

        hierarchy = SpecHierarchyLevel()
        for names in param_names:
            hierarchy.register(names)

        self.assertDictEqual(asdict(hierarchy), asdict(expected_hierarhcy))

    def test_hierarchy_register_without_groups(self):
        param_names = (
            ("plain",),
            ("group-1", "child"),
            ("group-1", "another"),
            ("after",),
            ("deeply", "flag"),
            ("deeply", "nested", "item"),
            ("deeply", "after"),
            ("control",),
        )

        expected_hierarhcy = SpecHierarchyLevel(
            fields=["plain", "group-1", "after", "deeply", "control"],
            child_groups={
                "group-1": SpecHierarchyLevel(
                    fields=["child", "another"],
                ),
                "deeply": SpecHierarchyLevel(
                    fields=["flag", "nested", "after"], child_groups={"nested": SpecHierarchyLevel(fields=["item"])}
                ),
            },
        )

        hierarchy = SpecHierarchyLevel()
        for names in param_names:
            hierarchy.register(names)

        self.assertDictEqual(asdict(hierarchy), asdict(expected_hierarhcy))

    def test_get_full_display_name(self):
        simple_param = spec.p.StringParameter(
            identifier=spec.build_identifier_from_name("/simple"),
            extra=spec.p.ExtraProperties(display_name="Simple"),
        )
        group_param = spec.p.ParameterGroup(
            identifier=spec.build_identifier_from_name("/group"),
            extra=spec.p.ExtraProperties(display_name="Group"),
        )
        group_param_no_disp_name = spec.p.ParameterGroup(identifier=spec.build_identifier_from_name("/group/nested"))
        simple_param_in_group = spec.p.StringParameter(
            identifier=spec.build_identifier_from_name("/group/nested/plain"),
            extra=spec.p.ExtraProperties(display_name="Plain"),
        )
        specification = spec.FullSpec.from_parameters(
            simple_param, group_param, group_param_no_disp_name, simple_param_in_group
        )
        expected_names_dict = {
            "/group": "/Group",
            "/simple": "/Simple",
            "/group/nested": "/Group/nested",
            "/group/nested/plain": "/Group/nested/Plain",
        }

        self.assertDictEqual(specification.full_display_names, expected_names_dict)
        self.assertEqual(specification.get_full_display_name("/group"), "/Group")
        self.assertEqual(specification.get_full_display_name("/group/nested/plain"), "/Group/nested/Plain")
