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


from unittest.mock import Mock
import unittest

from cm.legacy.services.config_host_group import ConfigHostGroupInfo
from cm.legacy.services.job.context._before_upgrade import (
    DEFAULT_BEFORE_UPGRADE,
    ProcessedBeforeUpgrade,
    construct_processed_before_upgrade,
    get_before_upgrades,
)
from core.config import Configuration, spec
from core.tests.doubles.config import build_config_service_with_fakes
from core.tests.test_config.utils import name_id
from core.types import ADCMCoreType, CoreObjectDescriptor, ShortObjectInfo
from parameterized import parameterized


class TestGBU(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.descriptor_cluster = CoreObjectDescriptor(id=4, type=ADCMCoreType.CLUSTER)
        cls.descriptor_service = CoreObjectDescriptor(id=2, type=ADCMCoreType.SERVICE)
        cls.descriptor_component = CoreObjectDescriptor(id=9, type=ADCMCoreType.COMPONENT)
        cls.descriptor_default = cls.descriptor_cluster

        cls.pbu_is_default_true = ProcessedBeforeUpgrade(is_default=True, before_upgrade=DEFAULT_BEFORE_UPGRADE)

        configuration = Configuration(values={"a": "filecontent"})
        specification = spec.FullSpec.from_parameters(
            spec.p.StringParameter(identifier=name_id("a"), as_file=True, supports_multiline=True)
        )
        cs, repo = build_config_service_with_fakes()
        repo.data.configs = {14: configuration, 43: configuration, 16: configuration, 11: configuration}
        repo.data.specs = {4: specification, 20: specification}
        cls.config_service = cs

    def prepare_pbu_from_raw(self, before_upgrade: dict) -> ProcessedBeforeUpgrade:
        return construct_processed_before_upgrade(before_upgrade, prototype_name=None, parent_before_upgrade={})

    def prepare_two_chg(self) -> tuple[ConfigHostGroupInfo, ConfigHostGroupInfo]:
        hosts = {ShortObjectInfo(id=2, name="h1"), ShortObjectInfo(id=4, name="h0")}
        chg_1 = ConfigHostGroupInfo(
            id=59, name="nice", hosts=hosts, current_config_id=43, owner=self.descriptor_cluster
        )
        chg_2 = ConfigHostGroupInfo(id=44, name="not", hosts=hosts, current_config_id=11, owner=self.descriptor_service)
        return chg_1, chg_2

    @parameterized.expand(
        [
            ("default", DEFAULT_BEFORE_UPGRADE, DEFAULT_BEFORE_UPGRADE),
            ("empty", {}, {"state": None, "config": None}),
            ("only_state", {"state": "x"}, {"state": "x", "config": None}),
            ("only_config", {"config_id": 4}, {"state": None, "config": None}),
            ("only_bundle_id", {"bundle_id": 4}, {"state": None, "config": None}),
            # imports and states are passed AS IS, so content's not important for this test
            ("only_imports", {"imports": {"config": "!"}}, {"imports": "!", "state": None, "config": None}),
            ("config_and_state", {"config_id": 4, "state": "created"}, {"state": "created", "config": None}),
            (
                "imports_and_state",
                {"imports": {"config": [2]}, "state": 12},
                {"imports": [2], "state": 12, "config": None},
            ),
            (
                "config_imports_and_state",
                {"imports": {"config": {"o": "a"}}, "state": 12, "config_id": 1},
                {"imports": {"o": "a"}, "state": 12, "config": None},
            ),
            (
                "bundle_id_and_imports",
                {"bundle_id": 100, "imports": {"config": {"a": "b"}}},
                {"imports": {"a": "b"}, "state": None, "config": None},
            ),
            (
                "bundle_id_imports_and_state",
                {"bundle_id": 100, "imports": {"config": {"a": "b"}}, "state": "created"},
                {"imports": {"a": "b"}, "state": "created", "config": None},
            ),
        ]
    )
    def test_no_config(self, _, input_raw, expected):
        input_pbu = self.prepare_pbu_from_raw(input_raw)
        cs_mock = Mock()
        cs_mock.retrieve_configurations_by_id = Mock()
        rep_mock = Mock()

        result = get_before_upgrades(
            before_upgrades={self.descriptor_default: input_pbu},
            config_service=cs_mock,
            retrieve_existing_prototypes=rep_mock,
        )[self.descriptor_default]

        self.assertEqual(result, expected)
        cs_mock.retrieve_configurations_by_id.assert_not_called()
        rep_mock.assert_not_called()

    @parameterized.expand(
        [
            ("no_extra", {}, {}),
            ("with_imports", {"imports": {"config": [{"o": "e"}]}}, {"imports": [{"o": "e"}]}),
        ]
    )
    def test_with_config(self, _, extra_input, extra_expected):
        input_pbu = self.prepare_pbu_from_raw({"bundle_id": 1, "config_id": 14} | extra_input)
        expected = {"state": None, "config": {"a": f"cluster.{self.descriptor_default.id}.a."}} | extra_expected

        result = get_before_upgrades(
            before_upgrades={self.descriptor_default: input_pbu},
            config_service=self.config_service,
            retrieve_existing_prototypes=lambda _: {(ADCMCoreType.CLUSTER, None, None): 4},
        )[self.descriptor_default]

        self.assertEqual(result, expected)

    def test_with_config_host_groups_on_two_objects(self):
        chg_1, chg_2 = self.prepare_two_chg()
        imports_block = {"imports": {"config": [{"o": "e"}]}}
        expected_imports_block = {"imports": imports_block["imports"]["config"]}
        cluster_pbu = self.prepare_pbu_from_raw(
            {
                "bundle_id": 1,
                "config_id": 14,
                "config_host_groups": {chg_1.name: {"config_id": chg_1.current_config_id}},
            }
            | imports_block
        )
        service_pbu = self.prepare_pbu_from_raw(
            # bundle passed directly, yet in reality it'll come from cluster def
            {
                "bundle_id": 1,
                "config_id": 16,
                "state": "installed",
                "config_host_groups": {chg_2.name: {"config_id": chg_2.current_config_id}},
            }
        )
        service_pbu.prototype_name = "awesome"
        expected_cluster = {
            "state": None,
            "config": {"a": f"cluster.{self.descriptor_cluster.id}.a."},
        } | expected_imports_block
        expected_cluster_group = expected_cluster | {
            "config": {"a": f"cluster.{self.descriptor_default.id}.group.{chg_1.id}.a."},
        }
        expected_service = {"state": "installed", "config": {"a": f"service.{self.descriptor_service.id}.a."}}
        expected_service_group = expected_service | {
            "config": {"a": f"service.{self.descriptor_service.id}.group.{chg_2.id}.a."},
        }

        result = get_before_upgrades(
            before_upgrades={self.descriptor_cluster: cluster_pbu, self.descriptor_service: service_pbu},
            config_host_groups=[chg_1, chg_2],
            config_service=self.config_service,
            retrieve_existing_prototypes=lambda _: {
                (ADCMCoreType.CLUSTER, None, None): 4,
                (ADCMCoreType.SERVICE, service_pbu.prototype_name, None): 20,
            },
        )

        self.assertEqual(result[self.descriptor_cluster], expected_cluster)
        self.assertEqual(result[self.descriptor_cluster, chg_1.name], expected_cluster_group)
        self.assertEqual(result[self.descriptor_service], expected_service)
        self.assertEqual(result[self.descriptor_service, chg_2.name], expected_service_group)

    def test_missing_config(self):
        # when object config is missing, groups are excluded, config is None
        # when group's config is missing, group is excluded
        chg_1, chg_2 = self.prepare_two_chg()
        chg_2.current_config_id = -1
        cluster_pbu = self.prepare_pbu_from_raw(
            {
                "bundle_id": 1,
                "state": "ooo",
                "config_id": -1,  # doesn't exist in data
                "config_host_groups": {chg_1.name: {"config_id": chg_1.current_config_id}},
            }
        )
        component_pbu = self.prepare_pbu_from_raw(
            # bundle passed directly, yet in reality it'll come from cluster def
            {
                "bundle_id": 1,
                "config_id": 16,
                "state": "installed",
                "config_host_groups": {chg_2.name: {"config_id": chg_2.current_config_id}},
            }
        )
        component_parent_name, component_own_name = component_pbu.prototype_name = ("awesome", "cname")
        expected_cluster = {"state": "ooo", "config": None}
        expected_component = {"state": "installed", "config": {"a": f"component.{self.descriptor_component.id}.a."}}

        result = get_before_upgrades(
            before_upgrades={self.descriptor_cluster: cluster_pbu, self.descriptor_component: component_pbu},
            config_host_groups=[chg_1, chg_2],
            config_service=self.config_service,
            retrieve_existing_prototypes=lambda _: {
                (ADCMCoreType.CLUSTER, None, None): 4,
                # key is "reversed": own name first, parent name last
                (ADCMCoreType.COMPONENT, component_own_name, component_parent_name): 20,
            },
        )

        self.assertSetEqual(set(result.keys()), {self.descriptor_cluster, self.descriptor_component})
        self.assertEqual(result[self.descriptor_cluster], expected_cluster)
        self.assertEqual(result[self.descriptor_component], expected_component)
