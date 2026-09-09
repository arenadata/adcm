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

from unittest import TestCase

from unittest_parametrize import ParametrizedTestCase, param, parametrize

from core.config import Change
from core.config import ChangeType as ChT
from core.config._operations import changes_to_revision_diff


class TestDiffFormatting(ParametrizedTestCase, TestCase):
    maxDiff = None

    @parametrize(
        ("changes", "expected"),
        [
            param([], {"diff": {}, "attr_diff": {}}, id="no_changes"),
            param(
                [Change(parameter="/simple", type=ChT.VALUE, old="a", new="b")],
                {"diff": {"simple": {"value": ["a", "b"]}}, "attr_diff": {}},
                id="value_root",
            ),
            param(
                [Change(parameter="/root_group/b", type=ChT.VALUE, old=True, new=False)],
                {"diff": {"root_group": {"b": {"value": [True, False]}}}, "attr_diff": {}},
                id="value_nested",
            ),
            param(
                [Change(parameter="/root_act", type=ChT.ACTIVATION, old=True, new=False)],
                {"diff": {}, "attr_diff": {"root_act": {"active": {"value": [True, False]}}}},
                id="activation_root",
            ),
            param(
                [Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=True)],
                {"diff": {}, "attr_diff": {"root_sel/one/ag": {"active": {"value": [False, True]}}}},
                id="activation_nested",
            ),
            param(
                [
                    Change(parameter="/simple", type=ChT.SYNCHRONIZATION, old=True, new=False),
                    Change(parameter="/root_group/b", type=ChT.SYNCHRONIZATION, old=False, new=True),
                ],
                {"diff": {}, "attr_diff": {}},
                id="synchronization_ignored",
            ),
            param(
                [
                    Change(parameter="/root_act", type=ChT.ACTIVATION, old=False, new=True),
                    Change(parameter="/root_act", type=ChT.SYNCHRONIZATION, old=True, new=False),
                ],
                {"diff": {}, "attr_diff": {"root_act": {"active": {"value": [False, True]}}}},
                id="activation_and_synchronization",
            ),
            param(
                [
                    Change(parameter="/root_sel", type=ChT.SELECTION, old=None, new="one"),
                    Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=None, new=["3", "1", "2"]),
                    Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=None, new=False),
                    Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=None, new=False),
                    Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old=None, new="w"),
                ],
                {
                    "diff": {
                        "root_sel": {
                            "one": {
                                "l": {"value": [None, ["3", "1", "2"]]},
                                "ag": {
                                    "b": {"value": [None, False]},
                                    "g": {"s": {"value": [None, "w"]}},
                                },
                            }
                        }
                    },
                    "attr_diff": {
                        "root_sel": {"selection": {"value": [None, "one"]}},
                        "root_sel/one/ag": {"active": {"value": [None, False]}},
                    },
                },
                id="selection_none_to_chosen",
            ),
            param(
                [
                    Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new=None),
                    Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=None),
                    Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=None),
                    Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=False, new=None),
                    Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old="w", new=None),
                ],
                {
                    "diff": {
                        "root_sel": {
                            "one": {
                                "l": {"value": [["3", "1", "2"], None]},
                                "ag": {
                                    "b": {"value": [False, None]},
                                    "g": {"s": {"value": ["w", None]}},
                                },
                            }
                        }
                    },
                    "attr_diff": {
                        "root_sel": {"selection": {"value": ["one", None]}},
                        "root_sel/one/ag": {"active": {"value": [False, None]}},
                    },
                },
                id="selection_chosen_to_none",
            ),
            param(
                [
                    Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new="two"),
                    Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=None),
                    Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=None),
                    Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old="w", new=None),
                    Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=False, new=None),
                    Change(parameter="/root_sel/two/m", type=ChT.VALUE, old=None, new={"k": "v"}),
                ],
                {
                    "diff": {
                        "root_sel": {
                            "one": {
                                "l": {"value": [["3", "1", "2"], None]},
                                "ag": {
                                    "g": {"s": {"value": ["w", None]}},
                                    "b": {"value": [False, None]},
                                },
                            },
                            "two": {"m": {"value": [None, {"k": "v"}]}},
                        }
                    },
                    "attr_diff": {
                        "root_sel": {"selection": {"value": ["one", "two"]}},
                        "root_sel/one/ag": {"active": {"value": [False, None]}},
                    },
                },
                id="selection_changed",
            ),
            param(
                [Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=["4"])],
                {"diff": {"root_sel": {"one": {"l": {"value": [["3", "1", "2"], ["4"]]}}}}, "attr_diff": {}},
                id="value_in_selection",
            ),
            param(
                [Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=True)],
                {"diff": {}, "attr_diff": {"root_sel/one/ag": {"active": {"value": [False, True]}}}},
                id="activation_in_selection",
            ),
            # hypothetical case
            param(
                [
                    Change(parameter="/root", type=ChT.VALUE, old=1, new=2),
                    Change(parameter="/root/child", type=ChT.VALUE, old="a", new="b"),
                ],
                {
                    "diff": {"root": {"value": [1, 2], "child": {"value": ["a", "b"]}}},
                    "attr_diff": {},
                },
                id="collision_leaf_then_branch",
            ),
            # hypothetical case
            param(
                [
                    Change(parameter="/root/child", type=ChT.VALUE, old="a", new="b"),
                    Change(parameter="/root", type=ChT.VALUE, old=1, new=2),
                ],
                {
                    "diff": {"root": {"child": {"value": ["a", "b"]}, "value": [1, 2]}},
                    "attr_diff": {},
                },
                id="collision_branch_then_leaf",
            ),
            param(
                [
                    Change(parameter="/root/child1", type=ChT.VALUE, old="a", new="b"),
                    Change(parameter="/root/child2", type=ChT.VALUE, old=1, new=2),
                ],
                {
                    "diff": {"root": {"child1": {"value": ["a", "b"]}, "child2": {"value": [1, 2]}}},
                    "attr_diff": {},
                },
                id="collision_two_leafs",
            ),
            param(
                [
                    Change(parameter="/root/child1", type=ChT.VALUE, old="a", new="b"),
                    Change(parameter="/root/value", type=ChT.VALUE, old=1, new=2),
                ],
                {
                    "diff": {"root": {"child1": {"value": ["a", "b"]}, "value": {"value": [1, 2]}}},
                    "attr_diff": {},
                },
                id="collision_value_key",
            ),
            # hypothetical, but will work strange
            param(
                [
                    Change(parameter="/root/value", type=ChT.VALUE, old=1, new=2),
                    Change(parameter="/root", type=ChT.VALUE, old="a", new="b"),
                ],
                {
                    "diff": {"root": {"value": ["a", "b"]}},
                    "attr_diff": {},
                },
                id="collision_node_value",
            ),
        ],
    )
    def test_format_from_changes(self, changes: list[Change], expected: dict) -> None:
        result = changes_to_revision_diff(changes)

        self.assertEqual(set(result.keys()), {"diff", "attr_diff"})
        self.assertDictEqual(result["diff"], expected["diff"])
        self.assertDictEqual(result["attr_diff"], expected["attr_diff"])
