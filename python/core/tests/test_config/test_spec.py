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
from core.config._types import ParameterLevelName
from core.tests.test_config.utils import ConfigTestCase

SpecHierarchyLevel = spec.SpecHierarchyLevel


def build_hierarchy_level(
    *,
    rule: spec.HierarchyValidationRule = spec.HierarchyValidationRule.ALL,
    fields: list[ParameterLevelName] | None = None,
    child_groups: dict[ParameterLevelName, SpecHierarchyLevel] | None = None,
) -> SpecHierarchyLevel:
    """
    Build a hierarchy level with an explicit `rule` and optional content.

    `rule` has no domain-agnostic default, so it has to be stated on construction.
    Tests that don't care about it get the same default the production code uses.
    """

    return SpecHierarchyLevel(rule=rule, fields=fields or [], child_groups=child_groups or {})


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

        expected_hierarhcy = build_hierarchy_level(
            fields=["plain", "group-1", "after", "deeply", "control"],
            child_groups={
                "group-1": build_hierarchy_level(
                    fields=["child", "another"],
                ),
                "deeply": build_hierarchy_level(
                    fields=["flag", "nested", "after"], child_groups={"nested": build_hierarchy_level(fields=["item"])}
                ),
            },
        )

        hierarchy = build_hierarchy_level()
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

        expected_hierarhcy = build_hierarchy_level(
            fields=["plain", "group-1", "after", "deeply", "control"],
            child_groups={
                "group-1": build_hierarchy_level(
                    fields=["child", "another"],
                ),
                "deeply": build_hierarchy_level(
                    fields=["flag", "nested", "after"], child_groups={"nested": build_hierarchy_level(fields=["item"])}
                ),
            },
        )

        hierarchy = build_hierarchy_level()
        for names in param_names:
            hierarchy.register(names)

        self.assertDictEqual(asdict(hierarchy), asdict(expected_hierarhcy))

    def test_hierarchy_register_reports_already_present_keys(self):
        hierarchy = build_hierarchy_level()

        # new keys are placed
        self.assertTrue(hierarchy.register(("plain",)))
        self.assertTrue(hierarchy.register(("group", "child")))

        # present keys are reported, group is present too, since it's created implicitly while placing its child
        self.assertFalse(hierarchy.register(("plain",)))
        self.assertFalse(hierarchy.register(("group", "child")))
        self.assertFalse(hierarchy.register(("group",)))

        # present keys aren't placed again
        expected_hierarchy = build_hierarchy_level(
            fields=["plain", "group"], child_groups={"group": build_hierarchy_level(fields=["child"])}
        )
        self.assertDictEqual(asdict(hierarchy), asdict(expected_hierarchy))

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
