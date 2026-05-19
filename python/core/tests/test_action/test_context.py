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

from parameterized import parameterized

from core.action._context.groups import (
    GroupOverrides,
    build_node_paths,
    group_hosts_by_common_host_groups,
    prepare_hosts_by_key,
    prepare_vars_by_key,
)
from core.action._context.operations import prepare_groups_for_host_groups
from core.action._context.types import ConfigHostGroupInfo
from core.cluster import ClusterTopology, ComponentTopology, ServiceTopology
from core.config import Configuration
from core.types import ADCMCoreType, CoreObjectDescriptor, ShortObjectInfo


def _component(component_id: int, name: str) -> ComponentTopology:
    return ComponentTopology(info=ShortObjectInfo(id=component_id, name=name), hosts={})


class TestHostGroupHostsDistribution(TestCase):
    @parameterized.expand(
        (
            ("empty", {}, {}),
            ("best-case", {1: [1, 2], 2: [2, 1], 3: [4, 3]}, {(1, 2): {1, 2}, (3,): {3, 4}}),
            ("worst-case", {1: [1, 2, 3], 2: [2], 3: [3]}, {(1,): {1}, (1, 2): {2}, (1, 3): {3}}),
            (
                "srs",
                {1: [1, 2, 3], 2: [4, 5], 3: [1, 2, 5, 6]},
                {(1, 3): {1, 2}, (1,): {3}, (2,): {4}, (2, 3): {5}, (3,): {6}},
            ),
            ("leftover", {3: [1, 4, 3], 1: [1, 2], 2: [1, 2]}, {(1, 2, 3): {1}, (1, 2): {2}, (3,): {3, 4}}),
        )
    )
    def test_by_common_host_groups(self, _, data: dict, expected: dict):
        result = group_hosts_by_common_host_groups(data)

        self.assertDictEqual(result, expected)


class TestContextGroups(TestCase):
    maxDiff = None

    def test_build_node_paths_returns_cluster_service_component_paths(self) -> None:
        topology = ClusterTopology(
            cluster_id=1,
            services={
                10: ServiceTopology(
                    info=ShortObjectInfo(id=10, name="service_1"),
                    components={
                        100: _component(component_id=100, name="component_1"),
                        101: _component(component_id=101, name="component_2"),
                    },
                ),
                20: ServiceTopology(
                    info=ShortObjectInfo(id=20, name="service_2"),
                    components={200: _component(component_id=200, name="component_3")},
                ),
            },
            hosts={},
        )
        expected = {
            CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER): ("cluster",),
            CoreObjectDescriptor(id=10, type=ADCMCoreType.SERVICE): ("services", "service_1"),
            CoreObjectDescriptor(id=20, type=ADCMCoreType.SERVICE): ("services", "service_2"),
            CoreObjectDescriptor(id=100, type=ADCMCoreType.COMPONENT): ("services", "service_1", "component_1"),
            CoreObjectDescriptor(id=101, type=ADCMCoreType.COMPONENT): ("services", "service_1", "component_2"),
            CoreObjectDescriptor(id=200, type=ADCMCoreType.COMPONENT): ("services", "service_2", "component_3"),
        }

        actual = build_node_paths(topology=topology)

        self.assertDictEqual(actual, expected)

    def test_build_node_paths_empty_services_returns_only_cluster(self) -> None:
        topology = ClusterTopology(cluster_id=77, services={}, hosts={})
        expected = {
            CoreObjectDescriptor(id=77, type=ADCMCoreType.CLUSTER): ("cluster",),
        }

        actual = build_node_paths(topology=topology)

        self.assertDictEqual(actual, expected)

    def test_build_node_paths_component_paths_bound_to_correct_service_name(self) -> None:
        topology = ClusterTopology(
            cluster_id=2,
            services={
                11: ServiceTopology(
                    info=ShortObjectInfo(id=11, name="alpha_service"),
                    components={110: _component(component_id=110, name="shared_component_name")},
                ),
                22: ServiceTopology(
                    info=ShortObjectInfo(id=22, name="beta_service"),
                    components={220: _component(component_id=220, name="shared_component_name")},
                ),
            },
            hosts={},
        )
        expected = {
            CoreObjectDescriptor(id=2, type=ADCMCoreType.CLUSTER): ("cluster",),
            CoreObjectDescriptor(id=11, type=ADCMCoreType.SERVICE): ("services", "alpha_service"),
            CoreObjectDescriptor(id=22, type=ADCMCoreType.SERVICE): ("services", "beta_service"),
            CoreObjectDescriptor(id=110, type=ADCMCoreType.COMPONENT): (
                "services",
                "alpha_service",
                "shared_component_name",
            ),
            CoreObjectDescriptor(id=220, type=ADCMCoreType.COMPONENT): (
                "services",
                "beta_service",
                "shared_component_name",
            ),
        }

        actual = build_node_paths(topology=topology)

        self.assertDictEqual(actual, expected)


class TestPrepareVarsByKey(TestCase):
    maxDiff = None

    def test_single_group_applies_config_and_before_upgrade(self) -> None:
        grouped_hosts_by_common_groups = {(1,): {10}}
        cluster_vars = {"cluster": {}, "services": {"svc": {"cmp": {}}}}
        groups_data_by_id = {
            1: GroupOverrides(node_path=("cluster",), before_upgrade={"old": 1}, prepared_config_values={"new": 2})
        }
        expected = {
            "chg_1": {"cluster": {"config": {"new": 2}, "before_upgrade": {"old": 1}}, "services": {"svc": {"cmp": {}}}}
        }

        actual = prepare_vars_by_key(
            grouped_hosts_by_common_groups=grouped_hosts_by_common_groups,
            cluster_vars=cluster_vars,
            groups_data_by_id=groups_data_by_id,
        )

        self.assertDictEqual(actual, expected)

    def test_multi_group_tuple_order_overwrites_config(self) -> None:
        # Not a real case for production grouping, but covers current tuple-order behavior.
        grouped_hosts_by_common_groups = {(2, 3): {10}}
        cluster_vars = {"cluster": {}}
        groups_data_by_id = {
            2: GroupOverrides(node_path=("cluster",), before_upgrade=None, prepared_config_values={"v": "from_2"}),
            3: GroupOverrides(node_path=("cluster",), before_upgrade=None, prepared_config_values={"v": "from_3"}),
        }
        expected = {"chg_2_3": {"cluster": {"config": {"v": "from_3"}}}}

        actual = prepare_vars_by_key(
            grouped_hosts_by_common_groups=grouped_hosts_by_common_groups,
            cluster_vars=cluster_vars,
            groups_data_by_id=groups_data_by_id,
        )

        self.assertDictEqual(actual, expected)

    def test_before_upgrade_absent_not_written(self) -> None:
        grouped_hosts_by_common_groups = {(1,): {10}}
        cluster_vars = {"cluster": {}}
        groups_data_by_id = {
            1: GroupOverrides(node_path=("cluster",), before_upgrade=None, prepared_config_values={"x": 1})
        }
        expected = {"chg_1": {"cluster": {"config": {"x": 1}}}}

        actual = prepare_vars_by_key(
            grouped_hosts_by_common_groups=grouped_hosts_by_common_groups,
            cluster_vars=cluster_vars,
            groups_data_by_id=groups_data_by_id,
        )

        self.assertDictEqual(actual, expected)

    def test_multiple_keys_cover_cluster_service_component_paths(self) -> None:
        grouped_hosts_by_common_groups = {(1,): {10}, (2, 3): {20}}
        cluster_vars = {"cluster": {}, "services": {"svc1": {"cmp1": {}}, "svc2": {"cmp2": {}}}}
        groups_data_by_id = {
            1: GroupOverrides(node_path=("cluster",), before_upgrade=None, prepared_config_values={"cluster": 1}),
            2: GroupOverrides(
                node_path=("services", "svc1"), before_upgrade={"old_svc": 2}, prepared_config_values={"svc": 2}
            ),
            3: GroupOverrides(
                node_path=("services", "svc2", "cmp2"), before_upgrade={"old_cmp": 3}, prepared_config_values={"cmp": 3}
            ),
        }
        expected = {
            "chg_1": {
                "cluster": {"config": {"cluster": 1}},
                "services": {"svc1": {"cmp1": {}}, "svc2": {"cmp2": {}}},
            },
            "chg_2_3": {
                "cluster": {},
                "services": {
                    "svc1": {"cmp1": {}, "config": {"svc": 2}, "before_upgrade": {"old_svc": 2}},
                    "svc2": {"cmp2": {"config": {"cmp": 3}, "before_upgrade": {"old_cmp": 3}}},
                },
            },
        }

        actual = prepare_vars_by_key(
            grouped_hosts_by_common_groups=grouped_hosts_by_common_groups,
            cluster_vars=cluster_vars,
            groups_data_by_id=groups_data_by_id,
        )

        self.assertDictEqual(actual, expected)

    def test_missing_group_override_key_raises_key_error(self) -> None:
        # Covers current behavior only; such missing keys are not expected in production.
        grouped_hosts_by_common_groups = {(99,): {1}}
        cluster_vars = {"cluster": {}}
        groups_data_by_id = {}

        with self.assertRaises(KeyError):
            prepare_vars_by_key(
                grouped_hosts_by_common_groups=grouped_hosts_by_common_groups,
                cluster_vars=cluster_vars,
                groups_data_by_id=groups_data_by_id,
            )


class TestPrepareHostsByKey(TestCase):
    maxDiff = None

    def test_multiple_keys_expected_hosts_dict(self) -> None:
        grouped_hosts_by_common_groups = {(1,): {2, 1}, (3, 4): {5, 3, 4}}
        host_name_by_id = {1: "host-b", 2: "host-a", 3: "host-f", 4: "host-d", 5: "host-e"}
        expected = {
            "chg_1": {"host-a": {}, "host-b": {}},
            "chg_3_4": {"host-d": {}, "host-e": {}, "host-f": {}},
        }

        actual = prepare_hosts_by_key(
            grouped_hosts_by_common_groups=grouped_hosts_by_common_groups, host_name_by_id=host_name_by_id
        )

        self.assertDictEqual(actual, expected)

    def test_preserves_tuple_order_in_key(self) -> None:
        grouped_hosts_by_common_groups = {(3, 1): {1}}
        host_name_by_id = {1: "host-a"}
        expected = {"chg_3_1": {"host-a": {}}}

        actual = prepare_hosts_by_key(
            grouped_hosts_by_common_groups=grouped_hosts_by_common_groups, host_name_by_id=host_name_by_id
        )

        self.assertDictEqual(actual, expected)

    def test_missing_host_name_key_raises_key_error(self) -> None:
        # Covers current behavior only; such missing keys are not expected in production.
        grouped_hosts_by_common_groups = {(1,): {42}}
        host_name_by_id = {}

        with self.assertRaises(KeyError):
            prepare_hosts_by_key(
                grouped_hosts_by_common_groups=grouped_hosts_by_common_groups, host_name_by_id=host_name_by_id
            )


class TestPrepareGroupsForHostGroups(TestCase):
    maxDiff = None

    def test_end_to_end_shape_assembly(self) -> None:
        topology = ClusterTopology(
            cluster_id=1,
            services={
                10: ServiceTopology(
                    info=ShortObjectInfo(id=10, name="svc"),
                    components={100: _component(component_id=100, name="cmp")},
                )
            },
            hosts={
                1: ShortObjectInfo(id=1, name="h1"),
                2: ShortObjectInfo(id=2, name="h2"),
            },
        )
        groups_with_hosts = (
            ConfigHostGroupInfo(
                id=1,
                name="g1",
                hosts={ShortObjectInfo(id=1, name="h1")},
                current_config_id=111,
                owner=CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER),
            ),
            ConfigHostGroupInfo(
                id=2,
                name="g2",
                hosts={ShortObjectInfo(id=2, name="h2")},
                current_config_id=222,
                owner=CoreObjectDescriptor(id=10, type=ADCMCoreType.SERVICE),
            ),
        )
        updated_configurations_by_group_id = {
            1: Configuration(values={"c": 1}),
            2: Configuration(values={"s": 2}),
        }
        objects_before_upgrade: dict = {
            (CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER), "g1"): {"b": 1},
            (CoreObjectDescriptor(id=10, type=ADCMCoreType.SERVICE), "g2"): {"b": 2},
        }
        cluster_vars = {"cluster": {}, "services": {"svc": {"cmp": {}}}}
        expected = {
            "chg_1": {
                "vars": {"cluster": {"config": {"c": 1}, "before_upgrade": {"b": 1}}, "services": {"svc": {"cmp": {}}}},
                "hosts": {"h1": {}},
            },
            "chg_2": {
                "vars": {
                    "cluster": {},
                    "services": {"svc": {"cmp": {}, "config": {"s": 2}, "before_upgrade": {"b": 2}}},
                },
                "hosts": {"h2": {}},
            },
        }

        actual = prepare_groups_for_host_groups(
            groups_with_hosts=groups_with_hosts,
            updated_configurations_by_group_id=updated_configurations_by_group_id,
            cluster_vars=cluster_vars,
            objects_before_upgrade=objects_before_upgrade,
            topology=topology,
        )

        self.assertDictEqual(actual, expected)

    def test_multi_owner_cluster_service_component_in_one_run(self) -> None:
        topology = ClusterTopology(
            cluster_id=1,
            services={
                10: ServiceTopology(
                    info=ShortObjectInfo(id=10, name="svc"),
                    components={100: _component(component_id=100, name="cmp")},
                )
            },
            hosts={
                1: ShortObjectInfo(id=1, name="h1"),
                2: ShortObjectInfo(id=2, name="h2"),
                3: ShortObjectInfo(id=3, name="h3"),
            },
        )
        groups_with_hosts = (
            ConfigHostGroupInfo(
                id=1,
                name="cluster_g",
                hosts={ShortObjectInfo(id=1, name="h1")},
                current_config_id=11,
                owner=CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER),
            ),
            ConfigHostGroupInfo(
                id=2,
                name="service_g",
                hosts={ShortObjectInfo(id=2, name="h2")},
                current_config_id=22,
                owner=CoreObjectDescriptor(id=10, type=ADCMCoreType.SERVICE),
            ),
            ConfigHostGroupInfo(
                id=3,
                name="component_g",
                hosts={ShortObjectInfo(id=3, name="h3")},
                current_config_id=33,
                owner=CoreObjectDescriptor(id=100, type=ADCMCoreType.COMPONENT),
            ),
        )
        updated_configurations_by_group_id = {
            1: Configuration(values={"cluster_cfg": 1}),
            2: Configuration(values={"service_cfg": 2}),
            3: Configuration(values={"component_cfg": 3}),
        }
        objects_before_upgrade: dict = {
            (CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER), "cluster_g"): {"old_cluster": 1},
            (CoreObjectDescriptor(id=10, type=ADCMCoreType.SERVICE), "service_g"): {"old_service": 2},
            (CoreObjectDescriptor(id=100, type=ADCMCoreType.COMPONENT), "component_g"): {"old_component": 3},
        }
        cluster_vars = {"cluster": {}, "services": {"svc": {"cmp": {}}}}
        expected = {
            "chg_1": {
                "vars": {
                    "cluster": {"config": {"cluster_cfg": 1}, "before_upgrade": {"old_cluster": 1}},
                    "services": {"svc": {"cmp": {}}},
                },
                "hosts": {"h1": {}},
            },
            "chg_2": {
                "vars": {
                    "cluster": {},
                    "services": {
                        "svc": {"cmp": {}, "config": {"service_cfg": 2}, "before_upgrade": {"old_service": 2}}
                    },
                },
                "hosts": {"h2": {}},
            },
            "chg_3": {
                "vars": {
                    "cluster": {},
                    "services": {
                        "svc": {"cmp": {"config": {"component_cfg": 3}, "before_upgrade": {"old_component": 3}}}
                    },
                },
                "hosts": {"h3": {}},
            },
        }

        actual = prepare_groups_for_host_groups(
            groups_with_hosts=groups_with_hosts,
            updated_configurations_by_group_id=updated_configurations_by_group_id,
            cluster_vars=cluster_vars,
            objects_before_upgrade=objects_before_upgrade,
            topology=topology,
        )

        self.assertDictEqual(actual, expected)

    def test_shared_host_grouping_is_applied_in_operations(self) -> None:
        topology = ClusterTopology(
            cluster_id=1,
            services={},
            hosts={
                1: ShortObjectInfo(id=1, name="h1"),
                2: ShortObjectInfo(id=2, name="h2"),
                3: ShortObjectInfo(id=3, name="h3"),
            },
        )
        groups_with_hosts = (
            ConfigHostGroupInfo(
                id=1,
                name="g1",
                hosts={ShortObjectInfo(id=1, name="h1"), ShortObjectInfo(id=2, name="h2")},
                current_config_id=11,
                owner=CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER),
            ),
            ConfigHostGroupInfo(
                id=2,
                name="g2",
                hosts={ShortObjectInfo(id=1, name="h1"), ShortObjectInfo(id=3, name="h3")},
                current_config_id=22,
                owner=CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER),
            ),
        )
        updated_configurations_by_group_id = {
            1: Configuration(values={"cfg": 1}),
            2: Configuration(values={"cfg": 2}),
        }
        expected = {
            "chg_1_2": {"vars": {"cluster": {"config": {"cfg": 2}}}, "hosts": {"h1": {}}},
            "chg_1": {"vars": {"cluster": {"config": {"cfg": 1}}}, "hosts": {"h2": {}}},
            "chg_2": {"vars": {"cluster": {"config": {"cfg": 2}}}, "hosts": {"h3": {}}},
        }

        actual = prepare_groups_for_host_groups(
            groups_with_hosts=groups_with_hosts,
            updated_configurations_by_group_id=updated_configurations_by_group_id,
            cluster_vars={"cluster": {}},
            objects_before_upgrade={},
            topology=topology,
        )

        self.assertDictEqual(actual, expected)

    def test_host_names_are_taken_from_topology_not_from_chg_hosts(self) -> None:
        topology = ClusterTopology(
            cluster_id=1,
            services={},
            hosts={1: ShortObjectInfo(id=1, name="from_topology")},
        )
        groups_with_hosts = (
            ConfigHostGroupInfo(
                id=1,
                name="g1",
                hosts={ShortObjectInfo(id=1, name="from_chg")},
                current_config_id=11,
                owner=CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER),
            ),
        )
        expected = {"chg_1": {"vars": {"cluster": {"config": {"cfg": 1}}}, "hosts": {"from_topology": {}}}}

        actual = prepare_groups_for_host_groups(
            groups_with_hosts=groups_with_hosts,
            updated_configurations_by_group_id={1: Configuration(values={"cfg": 1})},
            cluster_vars={"cluster": {}},
            objects_before_upgrade={},
            topology=topology,
        )

        self.assertDictEqual(actual, expected)
