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

# Locks in the *currently observed* behavior of the legacy `detect_concern_distribution`, and
# cross-checks it against its drop-in replacement — `ConcernDistributionScenarios.
# detect_concern_distribution` — on the same fixture — both are asserted against the same
# `expected_*` maps, so a mismatch between them shows up as one of the two failing. Only
# detection is exercised here — nothing is actually linked/persisted. Self-contained module/class
# so it's easy to remove once the rework lands and the legacy function is retired.
#
# Topology built for every case (cluster_1, from the default `cluster_one` bundle):
#   service_1/component_1: host_1, host_3
#   service_1/component_2: host_2
#   service_6_delete_with_action/component: host_1
#   service_1_clone/component_1: host_5
#   service_with_miss_config_service: no hosts mapped at all
#   host_4: added to the cluster, deliberately left unmapped
#   host_unbound: not added to any cluster at all
#
# host_1 is intentionally shared between service_1 (via component_1) and
# service_6_delete_with_action (via component) — this is what triggers the "leak via shared
# host" widening (`_distribute_by_hosts`) for SERVICE/COMPONENT-owned LOCK/ISSUE concerns.
# service_1_clone/host_5 shares nothing with anyone, to confirm the no-leak case at service level
# too (component_2/host_2 already covers the no-leak case at component level).
# service_with_miss_config_service is mapped to nothing at all, to confirm a fully unmapped
# service still resolves (with an empty HOST set) instead of erroring out.
#
# For PROVIDER cases, four providers cover: a single-cluster provider with a mapped/unmapped/
# unbound host mix (`self.provider`, reusing host_1..host_5/host_unbound above), a provider whose
# hosts span *two different clusters* at once (`provider_2` — cluster_a and cluster_b, both fresh
# instances of the same bundle used only for these cases), a provider none of whose hosts are
# mapped to anything at all (`provider_3`), and a provider isolating the "in a cluster but
# unmapped" case on its own, without an unbound host mixed in (`provider_4`).

from cm.legacy.services.concern.distribution import detect_concern_distribution
from cm.models import ConcernType
from core.concern.types import ConcernType as CoreConcernType
from core.scenarios.concern import ConcernDistributionScenarios
from core.types import ADCMCoreType, CoreObjectDescriptor
from tests.suites import ADCMDjangoAPISuite
from unittest_parametrize import param, parametrize


class TestConcernDistributionDetection(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        services = cls.uc.add_services_to_cluster(
            [
                "service_1",
                "service_6_delete_with_action",
                "service_1_clone",
                "service_with_miss_config_service",
            ],
            cluster=cls.cluster_1,
        )
        cls.service_1 = next(s for s in services if s.prototype.name == "service_1")
        cls.service_6 = next(s for s in services if s.prototype.name == "service_6_delete_with_action")
        cls.service_1_clone = next(s for s in services if s.prototype.name == "service_1_clone")
        cls.service_unmapped = next(s for s in services if s.prototype.name == "service_with_miss_config_service")

        cls.component_1 = cls.service_1.components.get(prototype__name="component_1")
        cls.component_2 = cls.service_1.components.get(prototype__name="component_2")
        cls.component_3 = cls.service_1.components.get(prototype__name="component_3")
        cls.component_6 = cls.service_6.components.get(prototype__name="component")
        cls.clone_component_1 = cls.service_1_clone.components.get(prototype__name="component_1")
        cls.clone_component_2 = cls.service_1_clone.components.get(prototype__name="component_2")
        cls.clone_component_3 = cls.service_1_clone.components.get(prototype__name="component_3")
        cls.unmapped_component_1 = cls.service_unmapped.components.get(prototype__name="have_no_config")
        cls.unmapped_component_2 = cls.service_unmapped.components.get(prototype__name="will_miss_config")

        cls.host_1 = cls.uc.add_host(cls.provider, fqdn="host_1", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(cls.provider, fqdn="host_2", cluster=cls.cluster_1)
        cls.host_3 = cls.uc.add_host(cls.provider, fqdn="host_3", cluster=cls.cluster_1)
        # left unmapped on purpose — see `expected_cluster`
        cls.host_4 = cls.uc.add_host(cls.provider, fqdn="host_4", cluster=cls.cluster_1)
        cls.host_5 = cls.uc.add_host(cls.provider, fqdn="host_5", cluster=cls.cluster_1)
        # not attached to any cluster — for the "host outside a cluster" wrapper case
        cls.host_unbound = cls.uc.add_host(cls.provider, fqdn="host_unbound")

        cls.uc.set_hostcomponent(
            cls.cluster_1,
            [
                (cls.host_1, cls.component_1),
                (cls.host_3, cls.component_1),
                (cls.host_2, cls.component_2),
                (cls.host_1, cls.component_6),
                (cls.host_5, cls.clone_component_1),
            ],
        )

        # two extra clusters (same bundle, separate instances), untouched by anything above — a
        # provider's hosts get mapped into these instead of `cluster_1`, so the PROVIDER cases
        # below can't perturb any of the CLUSTER/SERVICE/COMPONENT/HOST expectations already
        # locked in against `cluster_1`
        cls.cluster_a = cls.uc.add_cluster(bundle=cls.bundle_1, name="cluster_provider_a")
        (cls.cluster_a_service_1,) = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster_a)
        cls.cluster_a_component_1 = cls.cluster_a_service_1.components.get(prototype__name="component_1")

        cls.cluster_b = cls.uc.add_cluster(bundle=cls.bundle_1, name="cluster_provider_b")
        (cls.cluster_b_service_1,) = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster_b)
        cls.cluster_b_component_1 = cls.cluster_b_service_1.components.get(prototype__name="component_1")

        cls.provider_2 = cls.uc.add_provider(bundle=cls.provider_bundle, name="provider_2")
        cls.provider_2_host_in_cluster_a = cls.uc.add_host(
            cls.provider_2, fqdn="provider_2_host_in_cluster_a", cluster=cls.cluster_a
        )
        cls.provider_2_host_in_cluster_b = cls.uc.add_host(
            cls.provider_2, fqdn="provider_2_host_in_cluster_b", cluster=cls.cluster_b
        )
        # in cluster_a, but not mapped to any component
        cls.provider_2_host_unmapped = cls.uc.add_host(
            cls.provider_2, fqdn="provider_2_host_unmapped", cluster=cls.cluster_a
        )
        cls.provider_2_host_unbound = cls.uc.add_host(cls.provider_2, fqdn="provider_2_host_unbound")

        cls.uc.set_hostcomponent(cls.cluster_a, [(cls.provider_2_host_in_cluster_a, cls.cluster_a_component_1)])
        cls.uc.set_hostcomponent(cls.cluster_b, [(cls.provider_2_host_in_cluster_b, cls.cluster_b_component_1)])

        # none of this provider's hosts are mapped to anything at all
        cls.provider_3 = cls.uc.add_provider(bundle=cls.provider_bundle, name="provider_3")
        cls.provider_3_host_unmapped = cls.uc.add_host(
            cls.provider_3, fqdn="provider_3_host_unmapped", cluster=cls.cluster_a
        )
        cls.provider_3_host_unbound = cls.uc.add_host(cls.provider_3, fqdn="provider_3_host_unbound")

        # isolates the "in a cluster but unmapped" case on its own — provider_3 always paired it
        # with an unbound host, this confirms it behaves the same way with no unbound host at all
        cls.provider_4 = cls.uc.add_provider(bundle=cls.provider_bundle, name="provider_4")
        cls.provider_4_host_unmapped_in_cluster = cls.uc.add_host(
            cls.provider_4, fqdn="provider_4_host_unmapped_in_cluster", cluster=cls.cluster_b
        )

    def expected_cluster(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {
                self.service_1.pk,
                self.service_6.pk,
                self.service_1_clone.pk,
                self.service_unmapped.pk,
            },
            ADCMCoreType.COMPONENT: {
                self.component_1.pk,
                self.component_2.pk,
                self.component_3.pk,
                self.component_6.pk,
                self.clone_component_1.pk,
                self.clone_component_2.pk,
                self.clone_component_3.pk,
                self.unmapped_component_1.pk,
                self.unmapped_component_2.pk,
            },
            # host_4 is excluded: the cluster branch collects hosts via `HostComponent`,
            # so an unmapped host never appears here even though it belongs to the cluster
            ADCMCoreType.HOST: {self.host_1.pk, self.host_2.pk, self.host_3.pk, self.host_5.pk},
        }

    def expected_service_1_leaks_via_host(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1.pk, self.service_6.pk},
            ADCMCoreType.COMPONENT: {
                self.component_1.pk,
                self.component_2.pk,
                self.component_3.pk,
                self.component_6.pk,
            },
            ADCMCoreType.HOST: {self.host_1.pk, self.host_2.pk, self.host_3.pk},
        }

    def expected_service_1_flag(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1.pk},
            ADCMCoreType.COMPONENT: {self.component_1.pk, self.component_2.pk, self.component_3.pk},
            ADCMCoreType.HOST: {self.host_1.pk, self.host_2.pk, self.host_3.pk},
        }

    def expected_component_1_leaks_via_host(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1.pk, self.service_6.pk},
            ADCMCoreType.COMPONENT: {self.component_1.pk, self.component_6.pk},
            ADCMCoreType.HOST: {self.host_1.pk, self.host_3.pk},
        }

    def expected_component_2_no_shared_host(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1.pk},
            ADCMCoreType.COMPONENT: {self.component_2.pk},
            ADCMCoreType.HOST: {self.host_2.pk},
        }

    def expected_service_1_clone_isolated(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1_clone.pk},
            ADCMCoreType.COMPONENT: {
                self.clone_component_1.pk,
                self.clone_component_2.pk,
                self.clone_component_3.pk,
            },
            ADCMCoreType.HOST: {self.host_5.pk},
        }

    def expected_service_unmapped(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_unmapped.pk},
            ADCMCoreType.COMPONENT: {self.unmapped_component_1.pk, self.unmapped_component_2.pk},
            ADCMCoreType.HOST: set(),
        }

    def expected_host_1_mapped_to_multiple_services(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1.pk, self.service_6.pk},
            ADCMCoreType.COMPONENT: {self.component_1.pk, self.component_6.pk},
            ADCMCoreType.HOST: {self.host_1.pk},
        }

    def expected_host_2_mapped_to_single_component(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1.pk},
            ADCMCoreType.COMPONENT: {self.component_2.pk},
            ADCMCoreType.HOST: {self.host_2.pk},
        }

    def expected_host_4_unmapped(self) -> dict[ADCMCoreType, set[int]]:
        # matches legacy: an unmapped host stays cluster-less, even though it belongs to the cluster
        return {ADCMCoreType.HOST: {self.host_4.pk}}

    def expected_host_unbound(self) -> dict[ADCMCoreType, set[int]]:
        return {ADCMCoreType.HOST: {self.host_unbound.pk}}

    def expected_provider_single_cluster_mixed_hosts(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.PROVIDER: {self.provider.pk},
            ADCMCoreType.CLUSTER: {self.cluster_1.pk},
            ADCMCoreType.SERVICE: {self.service_1.pk, self.service_6.pk, self.service_1_clone.pk},
            ADCMCoreType.COMPONENT: {
                self.component_1.pk,
                self.component_2.pk,
                self.component_6.pk,
                self.clone_component_1.pk,
            },
            ADCMCoreType.HOST: {
                self.host_1.pk,
                self.host_2.pk,
                self.host_3.pk,
                self.host_4.pk,
                self.host_5.pk,
                self.host_unbound.pk,
            },
        }

    def expected_provider_2_spans_multiple_clusters(self) -> dict[ADCMCoreType, set[int]]:
        return {
            ADCMCoreType.PROVIDER: {self.provider_2.pk},
            ADCMCoreType.CLUSTER: {self.cluster_a.pk, self.cluster_b.pk},
            ADCMCoreType.SERVICE: {self.cluster_a_service_1.pk, self.cluster_b_service_1.pk},
            ADCMCoreType.COMPONENT: {self.cluster_a_component_1.pk, self.cluster_b_component_1.pk},
            ADCMCoreType.HOST: {
                self.provider_2_host_in_cluster_a.pk,
                self.provider_2_host_in_cluster_b.pk,
                self.provider_2_host_unmapped.pk,
                self.provider_2_host_unbound.pk,
            },
        }

    def expected_provider_3_fully_unmapped(self) -> dict[ADCMCoreType, set[int]]:
        # matches legacy: a provider whose hosts are all unbound/unmapped stays cluster-less too
        return {
            ADCMCoreType.PROVIDER: {self.provider_3.pk},
            ADCMCoreType.HOST: {self.provider_3_host_unmapped.pk, self.provider_3_host_unbound.pk},
        }

    def expected_provider_4_unmapped_in_cluster_only(self) -> dict[ADCMCoreType, set[int]]:
        # same "stays cluster-less" behavior, isolated to a host that's in a cluster (no unbound
        # host involved at all this time)
        return {
            ADCMCoreType.PROVIDER: {self.provider_4.pk},
            ADCMCoreType.HOST: {self.provider_4_host_unmapped_in_cluster.pk},
        }

    @parametrize(
        ("owner_attr", "owner_type", "concern_type", "expected_attr", "cluster_attr"),
        [
            param(
                "cluster_1",
                ADCMCoreType.CLUSTER,
                ConcernType.LOCK,
                "expected_cluster",
                None,
                id="cluster_lock_excludes_unmapped_host",
            ),
            param(
                "service_1",
                ADCMCoreType.SERVICE,
                ConcernType.LOCK,
                "expected_service_1_leaks_via_host",
                "cluster_1",
                id="service_lock_leaks_via_host",
            ),
            param(
                "service_1",
                ADCMCoreType.SERVICE,
                ConcernType.ISSUE,
                "expected_service_1_leaks_via_host",
                "cluster_1",
                id="service_issue_leaks_via_host",
            ),
            param(
                "service_1",
                ADCMCoreType.SERVICE,
                ConcernType.FLAG,
                "expected_service_1_flag",
                "cluster_1",
                id="service_flag_no_leak",
            ),
            param(
                "component_1",
                ADCMCoreType.COMPONENT,
                ConcernType.LOCK,
                "expected_component_1_leaks_via_host",
                "cluster_1",
                id="component_lock_leaks_via_host",
            ),
            param(
                "component_1",
                ADCMCoreType.COMPONENT,
                ConcernType.ISSUE,
                "expected_component_1_leaks_via_host",
                "cluster_1",
                id="component_issue_leaks_via_host",
            ),
            param(
                "component_2",
                ADCMCoreType.COMPONENT,
                ConcernType.LOCK,
                "expected_component_2_no_shared_host",
                "cluster_1",
                id="component_lock_no_shared_host",
            ),
            param(
                "service_1_clone",
                ADCMCoreType.SERVICE,
                ConcernType.LOCK,
                "expected_service_1_clone_isolated",
                "cluster_1",
                id="service_lock_no_shared_host",
            ),
            param(
                "service_unmapped",
                ADCMCoreType.SERVICE,
                ConcernType.LOCK,
                "expected_service_unmapped",
                "cluster_1",
                id="service_lock_fully_unmapped",
            ),
            # a HOST owner never backtracks, regardless of concern type, so mapped/unmapped are
            # covered for every concern type here to confirm none of them behave differently
            param(
                "host_1",
                ADCMCoreType.HOST,
                ConcernType.LOCK,
                "expected_host_1_mapped_to_multiple_services",
                "cluster_1",
                id="host_lock_mapped_to_multiple_services",
            ),
            param(
                "host_1",
                ADCMCoreType.HOST,
                ConcernType.ISSUE,
                "expected_host_1_mapped_to_multiple_services",
                "cluster_1",
                id="host_issue_mapped_to_multiple_services",
            ),
            param(
                "host_2",
                ADCMCoreType.HOST,
                ConcernType.FLAG,
                "expected_host_2_mapped_to_single_component",
                "cluster_1",
                id="host_flag_mapped_to_single_component",
            ),
            param(
                "host_4",
                ADCMCoreType.HOST,
                ConcernType.LOCK,
                "expected_host_4_unmapped",
                "cluster_1",
                id="host_lock_unmapped_stays_clusterless",
            ),
            param(
                "host_4",
                ADCMCoreType.HOST,
                ConcernType.ISSUE,
                "expected_host_4_unmapped",
                "cluster_1",
                id="host_issue_unmapped_stays_clusterless",
            ),
            param(
                "host_4",
                ADCMCoreType.HOST,
                ConcernType.FLAG,
                "expected_host_4_unmapped",
                "cluster_1",
                id="host_flag_unmapped_stays_clusterless",
            ),
            param(
                "host_unbound",
                ADCMCoreType.HOST,
                ConcernType.LOCK,
                "expected_host_unbound",
                None,
                id="host_lock_outside_any_cluster",
            ),
            param(
                "provider",
                ADCMCoreType.PROVIDER,
                ConcernType.LOCK,
                "expected_provider_single_cluster_mixed_hosts",
                None,
                id="provider_lock_single_cluster_mixed_hosts",
            ),
            param(
                "provider",
                ADCMCoreType.PROVIDER,
                ConcernType.FLAG,
                "expected_provider_single_cluster_mixed_hosts",
                None,
                id="provider_flag_single_cluster_mixed_hosts",
            ),
            param(
                "provider_2",
                ADCMCoreType.PROVIDER,
                ConcernType.LOCK,
                "expected_provider_2_spans_multiple_clusters",
                None,
                id="provider_lock_spans_multiple_clusters",
            ),
            param(
                "provider_2",
                ADCMCoreType.PROVIDER,
                ConcernType.ISSUE,
                "expected_provider_2_spans_multiple_clusters",
                None,
                id="provider_issue_spans_multiple_clusters",
            ),
            param(
                "provider_2",
                ADCMCoreType.PROVIDER,
                ConcernType.FLAG,
                "expected_provider_2_spans_multiple_clusters",
                None,
                id="provider_flag_spans_multiple_clusters",
            ),
            param(
                "provider_3",
                ADCMCoreType.PROVIDER,
                ConcernType.LOCK,
                "expected_provider_3_fully_unmapped",
                None,
                id="provider_lock_fully_unmapped",
            ),
            param(
                "provider_4",
                ADCMCoreType.PROVIDER,
                ConcernType.LOCK,
                "expected_provider_4_unmapped_in_cluster_only",
                None,
                id="provider_lock_unmapped_in_cluster_only",
            ),
        ],
    )
    def test_detect_distribution(
        self,
        owner_attr: str,
        owner_type: ADCMCoreType,
        concern_type: ConcernType,
        expected_attr: str,
        cluster_attr: str | None,
    ) -> None:
        owner_object = getattr(self, owner_attr)
        owner = CoreObjectDescriptor(id=owner_object.pk, type=owner_type)
        expected = getattr(self, expected_attr)()
        # mirrors what a real caller (e.g. `ConcernScenarios.create_job_concern`) is expected to
        # already know — the scenario itself no longer resolves this for SERVICE/COMPONENT/HOST
        cluster_id = getattr(self, cluster_attr).pk if cluster_attr is not None else None

        result = detect_concern_distribution(owner=owner, concern_type=concern_type)
        self.assertDictEqual(dict(result), expected, "legacy detection mismatch")

        scenario = self.container.get(ConcernDistributionScenarios)
        result_by_scenario = scenario.detect_concern_distribution(
            owner=owner, concern_type=CoreConcernType(concern_type), cluster_id=cluster_id
        )
        self.assertDictEqual(dict(result_by_scenario), expected, "scenario-based detection mismatch")
