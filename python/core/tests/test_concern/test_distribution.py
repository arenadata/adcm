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

from core.cluster import ClusterService
from core.concern.operations import detect_concern_distribution, detect_hosts_concern_distribution
from core.concern.types import ConcernType
from core.provider import HostInfo, ProviderService
from core.scenarios.concern import ConcernDistributionScenarios
from core.tests.doubles.cluster import FakeClusterRepo
from core.tests.doubles.provider import FakeProviderRepo
from core.tests.utils import build_cluster_topology
from core.types import ADCMCoreType, ClusterID, CoreObjectDescriptor, HostID, MaintenanceModeState, ObjectMM

CLUSTER, SERVICE, COMPONENT, HOST, PROVIDER, ADCM = (
    ADCMCoreType.CLUSTER,
    ADCMCoreType.SERVICE,
    ADCMCoreType.COMPONENT,
    ADCMCoreType.HOST,
    ADCMCoreType.PROVIDER,
    ADCMCoreType.ADCM,
)
LOCK, ISSUE, FLAG = ConcernType.LOCK, ConcernType.ISSUE, ConcernType.FLAG


def cluster(id_: int) -> CoreObjectDescriptor:
    return CoreObjectDescriptor(id=id_, type=CLUSTER)


def service(id_: int) -> CoreObjectDescriptor:
    return CoreObjectDescriptor(id=id_, type=SERVICE)


def component(id_: int) -> CoreObjectDescriptor:
    return CoreObjectDescriptor(id=id_, type=COMPONENT)


def host(id_: int) -> CoreObjectDescriptor:
    return CoreObjectDescriptor(id=id_, type=HOST)


def host_info(id_: HostID, cluster_id: ClusterID | None) -> HostInfo:
    return HostInfo(
        id=id_, type=ADCMCoreType.HOST, cluster_id=cluster_id, maintenance_mode=ObjectMM(MaintenanceModeState.OFF)
    )


def build_scenario(provider_repo: FakeProviderRepo, cluster_repo: FakeClusterRepo) -> ConcernDistributionScenarios:
    return ConcernDistributionScenarios(
        provider_service=ProviderService(repo=provider_repo), cluster_service=ClusterService(repo=cluster_repo)
    )


class TestConcernDistributionByTopology(ParametrizedTestCase, TestCase):
    def setUp(self) -> None:
        super().setUp()

        # cluster_id=1:
        #   service_1(1)/component_1(11): host_1(1), host_3(3)
        #   service_1(1)/component_2(12): host_2(2)
        #   service_1(1)/component_3(13): unmapped
        #   service_6(6)/component(61): host_1(1)              <- shares host_1 with component_1
        #   service_1_clone(2)/component_1(21): host_5(5)
        #   service_1_clone(2)/component_2(22), component_3(23): unmapped
        #   service_unmapped(7)/component_1(71), component_2(72): unmapped
        #   host_4(4): added to the cluster, deliberately left unmapped
        self.topology = build_cluster_topology(
            cluster_id=1,
            mapping=[
                (1, 11, 1),
                (1, 11, 3),
                (1, 12, 2),
                (6, 61, 1),
                (2, 21, 5),
            ],
            unmapped_components=[(1, 13), (2, 22), (2, 23), (7, 71), (7, 72)],
            unmapped_hosts=[4],
        )

    @parametrize(
        ("owner", "concern_type", "expected"),
        [
            param(
                cluster(1),
                LOCK,
                {
                    CLUSTER: {1},
                    SERVICE: {1, 6, 2, 7},
                    COMPONENT: {11, 12, 13, 61, 21, 22, 23, 71, 72},
                    # host_4 is excluded: it's never mapped, so it's unreachable via the triplets
                    HOST: {1, 2, 3, 5},
                },
                id="cluster_lock_excludes_unmapped_host",
            ),
            param(
                service(1),
                LOCK,
                {CLUSTER: {1}, SERVICE: {1, 6}, COMPONENT: {11, 12, 13, 61}, HOST: {1, 2, 3}},
                id="service_lock_backtracks_via_host",
            ),
            param(
                service(1),
                ISSUE,
                {CLUSTER: {1}, SERVICE: {1, 6}, COMPONENT: {11, 12, 13, 61}, HOST: {1, 2, 3}},
                id="service_issue_backtracks_via_host",
            ),
            param(
                service(1),
                FLAG,
                {CLUSTER: {1}, SERVICE: {1}, COMPONENT: {11, 12, 13}, HOST: {1, 2, 3}},
                id="service_flag_no_backtrack",
            ),
            param(
                component(11),
                LOCK,
                {CLUSTER: {1}, SERVICE: {1, 6}, COMPONENT: {11, 61}, HOST: {1, 3}},
                id="component_lock_backtracks_via_host",
            ),
            param(
                component(11),
                ISSUE,
                {CLUSTER: {1}, SERVICE: {1, 6}, COMPONENT: {11, 61}, HOST: {1, 3}},
                id="component_issue_backtracks_via_host",
            ),
            param(
                component(12),
                LOCK,
                {CLUSTER: {1}, SERVICE: {1}, COMPONENT: {12}, HOST: {2}},
                id="component_lock_no_shared_host",
            ),
            param(
                service(2),
                LOCK,
                {CLUSTER: {1}, SERVICE: {2}, COMPONENT: {21, 22, 23}, HOST: {5}},
                id="service_lock_no_shared_host",
            ),
            param(
                service(7),
                LOCK,
                {CLUSTER: {1}, SERVICE: {7}, COMPONENT: {71, 72}, HOST: set()},
                id="service_lock_fully_unmapped",
            ),
        ],
    )
    def test_detect_distribution(self, owner: CoreObjectDescriptor, concern_type: ConcernType, expected: dict) -> None:
        result = detect_concern_distribution(topology=self.topology, owner=owner, concern_type=concern_type)

        self.assertEqual(dict(result), expected)

    def test_component_owner_backtrack_reaches_sibling_component_of_its_own_service(self) -> None:
        # component_11 and component_12 are both in service_1, both mapped to host_1.
        # When owner is component_11, its own service (1) is already in `targets` before the backtrack loop runs,
        # but component_12 is *not* — skipping a whole service just because it's already registered would
        # silently drop component_12 even though it shares the owner's host.
        topology = build_cluster_topology(cluster_id=1, mapping=[(1, 11, 1), (1, 12, 1)])

        result = detect_concern_distribution(topology=topology, owner=component(11), concern_type=LOCK)

        self.assertEqual(dict(result), {CLUSTER: {1}, SERVICE: {1}, COMPONENT: {11, 12}, HOST: {1}})

    def test_owner_types_not_handled_by_this_function_raise(self) -> None:
        # HOST/PROVIDER/ADCM are handled at the scenario level instead (see TestConcernDistributionScenario below) —
        # this function stays CLUSTER/SERVICE/COMPONENT only
        for owner in (host(1), CoreObjectDescriptor(id=1, type=PROVIDER), CoreObjectDescriptor(id=1, type=ADCM)):
            with self.assertRaises(NotImplementedError):
                detect_concern_distribution(topology=self.topology, owner=owner, concern_type=LOCK)

    def test_hosts_batched_matches_union_of_individual_calls(self) -> None:
        # host_1 -> service_1/component_11 & service_6/component_61, host_2 -> service_1/component_12,
        # host_4 -> mapped to nothing
        result = detect_hosts_concern_distribution(topology=self.topology, host_ids=[1, 2, 4])

        merged: dict = {}
        for host_id in (1, 2, 4):
            for core_type, ids in detect_hosts_concern_distribution(topology=self.topology, host_ids=[host_id]).items():
                merged.setdefault(core_type, set()).update(ids)

        self.assertEqual(dict(result), merged)
        self.assertEqual(dict(result), {CLUSTER: {1}, SERVICE: {1, 6}, COMPONENT: {11, 12, 61}, HOST: {1, 2, 4}})


class TestConcernDistributionScenario(TestCase):
    def test_adcm_owner_returns_itself_without_any_lookup(self) -> None:
        # no repo data configured at all — proves no DB access is attempted
        scenario = build_scenario(FakeProviderRepo(), FakeClusterRepo())

        result = scenario.detect_concern_distribution(owner=CoreObjectDescriptor(id=1, type=ADCM), concern_type=LOCK)

        self.assertEqual(dict(result), {ADCM: {1}})

    def test_cluster_owner_delegates_to_operations_using_its_own_id_as_cluster_id(self) -> None:
        topology = build_cluster_topology(cluster_id=1, mapping=[(1, 11, 100)])
        scenario = build_scenario(FakeProviderRepo(), FakeClusterRepo(topologies={1: topology}))

        result = scenario.detect_concern_distribution(owner=cluster(1), concern_type=LOCK)

        self.assertEqual(
            dict(result), detect_concern_distribution(topology=topology, owner=cluster(1), concern_type=LOCK)
        )

    def test_service_owner_requires_cluster_id_from_caller(self) -> None:
        # no internal fallback lookup — cluster_id is the caller's responsibility for SERVICE/COMPONENT/HOST;
        # omitting it is a caller error, not "please resolve it for me"
        scenario = build_scenario(FakeProviderRepo(), FakeClusterRepo())

        with self.assertRaises(ValueError):
            scenario.detect_concern_distribution(owner=service(1), concern_type=LOCK)

    def test_service_owner_with_cluster_id_delegates_to_operations(self) -> None:
        topology = build_cluster_topology(cluster_id=1, mapping=[(1, 11, 100)])
        scenario = build_scenario(FakeProviderRepo(), FakeClusterRepo(topologies={1: topology}))

        result = scenario.detect_concern_distribution(owner=service(1), concern_type=LOCK, cluster_id=1)

        self.assertEqual(
            dict(result), detect_concern_distribution(topology=topology, owner=service(1), concern_type=LOCK)
        )

    def test_component_owner_with_cluster_id_delegates_to_operations(self) -> None:
        topology = build_cluster_topology(cluster_id=1, mapping=[(1, 11, 100)])
        scenario = build_scenario(FakeProviderRepo(), FakeClusterRepo(topologies={1: topology}))

        result = scenario.detect_concern_distribution(owner=component(11), concern_type=LOCK, cluster_id=1)

        self.assertEqual(
            dict(result), detect_concern_distribution(topology=topology, owner=component(11), concern_type=LOCK)
        )

    def test_host_owner_with_cluster_id_delegates_to_hosts_concern_distribution(self) -> None:
        topology = build_cluster_topology(cluster_id=1, mapping=[(1, 11, 100)])
        scenario = build_scenario(FakeProviderRepo(), FakeClusterRepo(topologies={1: topology}))

        result = scenario.detect_concern_distribution(owner=host(100), concern_type=LOCK, cluster_id=1)

        self.assertEqual(dict(result), {CLUSTER: {1}, SERVICE: {1}, COMPONENT: {11}, HOST: {100}})

    def test_host_owner_without_cluster_id_returns_itself_without_topology_lookup(self) -> None:
        # unlike SERVICE/COMPONENT, `cluster_id=None` is a legitimate value for HOST — it means the caller
        # already checked and the host isn't in any cluster, not "go look it up"
        scenario = build_scenario(FakeProviderRepo(), FakeClusterRepo())

        result = scenario.detect_concern_distribution(owner=host(400), concern_type=LOCK)

        self.assertEqual(dict(result), {HOST: {400}})

    def test_provider_spans_multiple_clusters_with_mapped_unmapped_and_unbound_hosts(self) -> None:
        # host_100 -> cluster_1/service_1/component_11, host_200 -> cluster_2/service_2/component_21,
        # host_300 -> in cluster_1 but not mapped to anything, host_400 -> not in any cluster at all
        cluster_repo = FakeClusterRepo(
            topologies={
                1: build_cluster_topology(cluster_id=1, mapping=[(1, 11, 100)]),
                2: build_cluster_topology(cluster_id=2, mapping=[(2, 21, 200)]),
            }
        )
        provider_repo = FakeProviderRepo(
            hosts=(
                host_info(100, cluster_id=1),
                host_info(200, cluster_id=2),
                host_info(300, cluster_id=1),
                host_info(400, cluster_id=None),
            )
        )
        scenario = build_scenario(provider_repo, cluster_repo)

        result = scenario.detect_concern_distribution(
            owner=CoreObjectDescriptor(id=99, type=PROVIDER), concern_type=LOCK
        )

        self.assertEqual(
            dict(result),
            {
                PROVIDER: {99},
                CLUSTER: {1, 2},
                SERVICE: {1, 2},
                COMPONENT: {11, 21},
                HOST: {100, 200, 300, 400},
            },
        )

    def test_provider_fully_unmapped(self) -> None:
        cluster_repo = FakeClusterRepo(topologies={1: build_cluster_topology(cluster_id=1)})
        provider_repo = FakeProviderRepo(hosts=(host_info(300, cluster_id=1), host_info(400, cluster_id=None)))
        scenario = build_scenario(provider_repo, cluster_repo)

        result = scenario.detect_concern_distribution(
            owner=CoreObjectDescriptor(id=99, type=PROVIDER), concern_type=LOCK
        )

        self.assertEqual(dict(result), {PROVIDER: {99}, HOST: {300, 400}})

    def test_provider_unmapped_in_cluster_only(self) -> None:
        # isolates the "in a cluster but unmapped" case on its own, no unbound host involved
        cluster_repo = FakeClusterRepo(topologies={1: build_cluster_topology(cluster_id=1)})
        provider_repo = FakeProviderRepo(hosts=(host_info(300, cluster_id=1),))
        scenario = build_scenario(provider_repo, cluster_repo)

        result = scenario.detect_concern_distribution(
            owner=CoreObjectDescriptor(id=99, type=PROVIDER), concern_type=LOCK
        )

        self.assertEqual(dict(result), {PROVIDER: {99}, HOST: {300}})
