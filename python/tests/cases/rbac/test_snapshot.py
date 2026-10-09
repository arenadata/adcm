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

"""Golden comparison and natural key rules of the snapshot module, no database involved"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
import yaml

from tests.cases.rbac.snapshot import assert_matches_golden, take_snapshot


class TestSnapshotGoldens(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()

        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.goldens_dir = Path(directory.name)

    def test_missing_golden_is_recorded_and_fails(self) -> None:
        golden = self.goldens_dir / "scenario.yaml"
        actual = {"rbac_role": {"added": ["task-role:task:cluster:A1:common#1 | role"], "removed": []}}

        with self.assertRaisesRegex(AssertionError, "scenario.yaml was missing: recorded .*, review it"):
            assert_matches_golden(self, golden, actual)

        self.assertEqual(yaml.safe_load(golden.read_text()), actual)

    def test_recorded_golden_matches_same_output(self) -> None:
        golden = self.goldens_dir / "baseline.yaml"
        actual = {"auth_user_groups": ["U-single | G-solo-custom"], "rbac_role": []}
        golden.write_text(yaml.safe_dump(actual))

        assert_matches_golden(self, golden, actual)

    def test_baseline_differs_names_table_and_rows(self) -> None:
        golden = self.goldens_dir / "baseline.yaml"
        golden.write_text(
            yaml.safe_dump({"auth_user_groups": ["U-single | G-solo-custom"], "rbac_role": ["Custom | role"]})
        )

        with self.assertRaisesRegex(
            AssertionError,
            r"table auth_user_groups:\n"
            r"  - U-single \| G-solo-custom  \(in golden, not in actual\)\n"
            r"  \+ U-single \| G-overlap  \(in actual, not in golden\)",
        ):
            assert_matches_golden(
                self, golden, {"auth_user_groups": ["U-single | G-overlap"], "rbac_role": ["Custom | role"]}
            )

    def test_diff_differs_names_table_section_and_rows(self) -> None:
        golden = self.goldens_dir / "scenario.yaml"
        golden.write_text(
            yaml.safe_dump({"effective_model_perm": {"added": ["U-launch | cm.add_cluster"], "removed": []}})
        )

        with self.assertRaisesRegex(
            AssertionError,
            r"table effective_model_perm \(added\):\n"
            r"  - U-launch \| cm.add_cluster  \(in golden, not in actual\)\n"
            r"table effective_model_perm \(removed\):\n"
            r"  \+ U-launch \| cm.add_cluster  \(in actual, not in golden\)",
        ):
            assert_matches_golden(
                self,
                golden,
                {"effective_model_perm": {"added": [], "removed": ["U-launch | cm.add_cluster"]}},
            )


class TestSnapshotNaturalKeys(SimpleTestCase):
    def test_unknown_content_type_raises(self) -> None:
        models = {
            name: MagicMock(**{"objects.values_list.return_value": []})
            for name in ("Permission", "AuthGroup", "Group", "AuthUser", "Policy", "Role")
        }
        models["Permission"].objects.values_list.return_value = [(1, "cm", "view_unknownmodel")]
        models["AuthGroup"].objects.values_list.return_value = [(1, "G-solo-custom")]
        content_type = MagicMock(**{"objects.values_list.return_value": [(7, "cm", "unknownmodel")]})
        group_object_permission = MagicMock(**{"objects.values_list.return_value": [(1, 1, 1, 7, "42")]})

        with (
            patch.multiple(
                "tests.cases.rbac.snapshot",
                ContentType=content_type,
                GroupObjectPermission=group_object_permission,
                **models,
            ),
            self.assertRaisesRegex(RuntimeError, "no natural key rule for model `cm.unknownmodel`"),
        ):
            take_snapshot(key_map={})
