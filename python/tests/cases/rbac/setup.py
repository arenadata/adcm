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

"""
Shared setup of the RBAC write-side equivalence suite (ADCM-8502).

One setup carries every setup feature (S-id) of the scenario catalogue,
each scenario is "act + compare diff of snapshots with golden".
The superuser `admin` (in no group) drives the act step, so it never appears in snapshots.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final
from unittest import SkipTest

from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Bundle,
    Cluster,
    Component,
    Host,
    JobLog,
    JobStatus,
    LogStorage,
    Provider,
    Service,
    TaskLog,
)
from cm.transition.status import StatusScenarios
from core.config import ConfigService
from core.logs import CheckLogArguments
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.utils import timezone
from rbac.models import Role
from rbac.roles import assign_view_logstorage_permissions_by_job
from rbac.scenarios import RBACScenarios
from rbac.services.policy import policy_create
from rbac.services.role import role_create
from use_cases.dto import RunActionDTO
from use_cases.logs.check import AddCheckLogRecordForJob
from use_cases.transition.host.duplicate import create_duplicate
from use_cases.transition.job.schedule import ActionTarget, ScheduleTask
import dishka

from tests.cases.rbac.snapshot import (
    ObjectKeys,
    QueryCounter,
    Snapshot,
    assert_matches_golden,
    collect_object_keys,
    diff,
    record_query_count,
    take_snapshot,
)
from tests.suites import SETUP_WITH_RBAC, ADCMDjangoAPISuiteNoBundles

BUNDLES_DIR: Final = Path(__file__).parent / "bundles"
GOLDENS_DIR: Final = Path(__file__).parent / "goldens"
QUERY_COUNTS_DIR: Final = GOLDENS_DIR / "query-counts"


class RBACWriteSideSuite(ADCMDjangoAPISuiteNoBundles):
    """
    Setup features (`setup-features.md`) -> objects:

    - S-B1/S-B3: bundles A v1/v2; S-B2: bundle B; S-B4: provider P v1/v2
    - S-B5: bundle E, cluster E1, policy on its action role
    - S-T1: clusters A1, A2 (A v1), B1; S-T2: providers P1, P2, hosts `h-free`, `h-unmapped` (in A1),
      `h-one` (A1 svc_1/comp_1), `h-multi` (A1 svc_1/comp_1, svc_1/comp_2, svc_2/comp_1), `h-a2`, `h-b1`, `h-free-p2`
    - S-T3: duplicate of `h-free` without cluster
    - S-T4: CHGs on A1, A1/svc_1, A1/svc_1/comp_1, P1 with hosts and 2 config revisions each
    - S-T5: AHGs on A1, A1/svc_1, A1/svc_1/comp_1 with `h-one`
    - S-T6: 2 ConfigLogs on A1, A1/svc_1, A1/svc_1/comp_1, P1, `h-one` (+ CHGs)
    - S-J6: `common` on A1 launched before any policy (TaskRole unattached)
    - S-J1: `common` on A1, A1/svc_1, A1/svc_1/comp_1, P1, `h-one` after the policies
    - S-J2: A1's host action `on_host` on `h-one`; S-J3: `in_ahg` on A1's AHG; S-J4: ADCM `test_ldap_connection`
    - S-J5: custom and check log on the A1 task launched after the policies
    - S-J7: second `common` on A1/svc_1, rotated (TaskLog and orphan JobLogs deleted as logrotate does)
    - S-R1..S-R8, G-*, U-*: see `build_rbac`
    """

    suite_setup = SETUP_WITH_RBAC
    maxDiff = None

    key_map: ObjectKeys
    baseline: Snapshot

    cluster_a1: Cluster
    cluster_a2: Cluster
    cluster_b1: Cluster
    cluster_e1: Cluster
    provider_p1: Provider
    provider_p2: Provider
    hosts: dict[str, Host]

    @classmethod
    def setUpClass(cls) -> None:
        if cls is RBACWriteSideSuite:
            message = "Base suite: shared setup is built for subclasses only"
            raise SkipTest(message)

        super().setUpClass()

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.build_topology()
        cls.launch_action(owner=cls.cluster_a1, action_name="common")
        cls.build_rbac()
        cls.launch_tasks()

        rotated_task = cls.launch_action(owner=cls.service("A1", "svc_1"), action_name="common")
        key_map_before_rotation = collect_object_keys()
        cls.rotate_task(task=rotated_task)

        cls.key_map = key_map_before_rotation | collect_object_keys()
        cls.baseline = take_snapshot(cls.key_map)

    def test_baseline(self) -> None:
        assert_matches_golden(self, GOLDENS_DIR / "baseline.yaml", self.baseline.serialize())

    @contextmanager
    def act(self) -> Iterator[None]:
        """
        Wrap the act step of the scenario and compare "baseline -> after act" diff with the scenario's golden.

        Scenario id is the test method name without `test_` prefix.
        """

        scenario_id = self.id().rsplit(".", maxsplit=1)[-1].removeprefix("test_")

        # cached content types would make query count depend on the tests order
        ContentType.objects.clear_cache()

        query_counter = QueryCounter()
        with connection.execute_wrapper(query_counter):
            yield

        record_query_count(
            path=QUERY_COUNTS_DIR / f"{type(self).__name__}.yaml", scenario=scenario_id, count=query_counter.count
        )

        after = take_snapshot(self.key_map)
        assert_matches_golden(self, GOLDENS_DIR / f"{scenario_id}.yaml", diff(before=self.baseline, after=after))

    # Setup steps

    @classmethod
    def build_topology(cls) -> None:
        bundle_a = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_a_v1")
        cls.uc.upload_bundle(BUNDLES_DIR / "cluster_a_v2")
        bundle_b = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_b")
        bundle_e = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_e")
        bundle_p = cls.uc.upload_bundle(BUNDLES_DIR / "provider_v1")
        cls.uc.upload_bundle(BUNDLES_DIR / "provider_v2")

        cls.cluster_a1 = cls.add_cluster_with_services(bundle=bundle_a, name="A1", services=["svc_1", "svc_2", "svc_3"])
        cls.cluster_a2 = cls.add_cluster_with_services(bundle=bundle_a, name="A2", services=["svc_1", "svc_2", "svc_3"])
        cls.cluster_b1 = cls.add_cluster_with_services(bundle=bundle_b, name="B1", services=["svc_b1"])
        cls.cluster_e1 = cls.uc.add_cluster(bundle=bundle_e, name="E1")

        cls.provider_p1 = cls.uc.add_provider(bundle=bundle_p, name="P1")
        cls.provider_p2 = cls.uc.add_provider(bundle=bundle_p, name="P2")

        cls.hosts = {
            fqdn: cls.uc.add_host(provider=provider, fqdn=fqdn)
            for provider, fqdn in (
                (cls.provider_p1, "h-free"),
                (cls.provider_p1, "h-unmapped"),
                (cls.provider_p1, "h-one"),
                (cls.provider_p1, "h-multi"),
                (cls.provider_p2, "h-a2"),
                (cls.provider_p2, "h-b1"),
                (cls.provider_p2, "h-free-p2"),
            )
        }

        for cluster, fqdn in (
            (cls.cluster_a1, "h-unmapped"),
            (cls.cluster_a1, "h-one"),
            (cls.cluster_a1, "h-multi"),
            (cls.cluster_a2, "h-a2"),
            (cls.cluster_b1, "h-b1"),
        ):
            cls.uc.add_host_to_cluster(cluster=cluster, host=cls.hosts[fqdn])

        cls.uc.set_hostcomponent(
            cluster=cls.cluster_a1,
            entries=[
                (cls.hosts["h-one"], cls.component("A1", "svc_1", "comp_1")),
                (cls.hosts["h-multi"], cls.component("A1", "svc_1", "comp_1")),
                (cls.hosts["h-multi"], cls.component("A1", "svc_1", "comp_2")),
                (cls.hosts["h-multi"], cls.component("A1", "svc_2", "comp_1")),
            ],
        )
        cls.uc.set_hostcomponent(
            cluster=cls.cluster_a2, entries=[(cls.hosts["h-a2"], cls.component("A2", "svc_1", "comp_1"))]
        )
        cls.uc.set_hostcomponent(
            cluster=cls.cluster_b1, entries=[(cls.hosts["h-b1"], cls.component("B1", "svc_b1", "comp_b1"))]
        )

        create_duplicate(
            config_service=cls.container.get(ConfigService),
            host_id=cls.hosts["h-free"].pk,
            name="h-free",
            rbac_scenarios=cls.container.get(RBACScenarios),
            status_scenarios=cls.container.get(StatusScenarios),
        )

        a1_svc_1 = cls.service("A1", "svc_1")
        a1_comp_1 = cls.component("A1", "svc_1", "comp_1")

        for owner, host in (
            (cls.cluster_a1, cls.hosts["h-one"]),
            (a1_svc_1, cls.hosts["h-one"]),
            (a1_comp_1, cls.hosts["h-one"]),
            (cls.provider_p1, cls.hosts["h-free"]),
        ):
            config_host_group = cls.uc.add_config_host_group(owner=owner, name=f"chg-{owner.prototype.type}")
            config_host_group.hosts.add(host)
            cls.uc.change_config(
                config_host_group, values_diff={"value": "group-own"}, meta_diff={"/value": {"isSynchronized": False}}
            )

        for owner in (cls.cluster_a1, a1_svc_1, a1_comp_1):
            action_host_group = cls.uc.create_action_host_group(name=f"ahg-{owner.prototype.type}", owner=owner)
            cls.uc.add_hosts_to_action_host_group(group_id=action_host_group.pk, hosts=[cls.hosts["h-one"].pk])

        for owner in (cls.cluster_a1, a1_svc_1, a1_comp_1, cls.provider_p1, cls.hosts["h-one"]):
            cls.uc.change_config(owner, values_diff={"value": "changed"})

    @classmethod
    def build_rbac(cls) -> None:
        """
        Groups, users and policies (S-R1..S-R8, `G-*` and `U-*` tables of `setup-features.md`).

        `G-solo-*` groups have exactly one policy each, one per role kind (S-R2, S-R3, S-R4).
        `U-idle` is the only member of `G-idle` (that group needs users).
        """

        a1_svc_1 = cls.service("A1", "svc_1")
        a1_svc_2 = cls.service("A1", "svc_2")
        a2_svc_1 = cls.service("A2", "svc_1")

        groups = {
            name: cls.uc.create_group(display_name=name)
            for name in (
                "G-solo-cluster-admin",
                "G-solo-service-admin",
                "G-solo-provider-admin",
                "G-solo-view-cluster-config",
                "G-solo-edit-component-config",
                "G-solo-view-host-config",
                "G-solo-cluster-action",
                "G-solo-service-action",
                "G-solo-component-host-action",
                "G-solo-edit-hc",
                "G-solo-map-hosts",
                "G-solo-adcm-user",
                "G-solo-create-cluster",
                "G-solo-custom",
                "G-solo-e-action",
                "G-overlap",
                "G-cross",
                "G-multi-a",
                "G-multi-b",
                "G-launch-only",
                "G-empty",
                "G-idle",
            )
        }

        custom_role = role_create(
            display_name="Custom Cluster Operator",
            description="S-R4: several business roles of cluster hierarchy",
            child=[
                cls.role("View cluster configurations"),
                cls.role("Cluster Action: Common Action"),
                cls.role("Service Action: Common Action"),
                cls.role("View host-components"),
            ],
        )
        if custom_role is None:
            message = "Custom role wasn't created"
            raise RuntimeError(message)

        policies: Iterable[tuple[str, Role, list[str], list[Cluster | Service | Component | Provider | Host]]] = (
            ("P-solo-cluster-admin", cls.role("Cluster Administrator"), ["G-solo-cluster-admin"], [cls.cluster_a1]),
            ("P-solo-service-admin", cls.role("Service Administrator"), ["G-solo-service-admin"], [a1_svc_1]),
            ("P-solo-provider-admin", cls.role("Provider Administrator"), ["G-solo-provider-admin"], [cls.provider_p1]),
            (
                "P-solo-view-cluster-config",
                cls.role("View cluster configurations"),
                ["G-solo-view-cluster-config"],
                [cls.cluster_a1],
            ),
            (
                "P-solo-edit-component-config",
                cls.role("Edit component configurations"),
                ["G-solo-edit-component-config"],
                [cls.component("A1", "svc_1", "comp_2")],
            ),
            (
                "P-solo-view-host-config",
                cls.role("View host configurations"),
                ["G-solo-view-host-config"],
                [cls.hosts["h-multi"]],
            ),
            (
                "P-solo-cluster-action",
                cls.role("Cluster Action: Common Action"),
                ["G-solo-cluster-action"],
                [cls.cluster_a1],
            ),
            (
                "P-solo-service-action",
                cls.role("Service Action: Common Action"),
                ["G-solo-service-action"],
                [a1_svc_2],
            ),
            (
                "P-solo-component-host-action",
                cls.role("Component Action: Run On Host"),
                ["G-solo-component-host-action"],
                [cls.component("A1", "svc_1", "comp_1")],
            ),
            ("P-solo-edit-hc", cls.role("Edit host-components"), ["G-solo-edit-hc"], [cls.cluster_a1]),
            ("P-solo-map-hosts", cls.role("Map hosts"), ["G-solo-map-hosts"], [cls.cluster_a2]),
            ("P-solo-adcm-user", cls.role("ADCM User"), ["G-solo-adcm-user"], []),
            ("P-solo-create-cluster", cls.role("Create cluster"), ["G-solo-create-cluster"], []),
            ("P-solo-custom", custom_role, ["G-solo-custom"], [cls.cluster_a1]),
            ("P-solo-e-action", cls.role("Cluster Action: E Action"), ["G-solo-e-action"], [cls.cluster_e1]),
            # S-R6: both grant the same rows to G-overlap
            ("P-overlap-admin", cls.role("Cluster Administrator"), ["G-overlap"], [cls.cluster_a1]),
            ("P-overlap-edit-config", cls.role("Edit cluster configurations"), ["G-overlap"], [cls.cluster_a1]),
            # S-R5: same role on different clusters
            ("P-cross-a1", cls.role("Cluster Action: Common Action"), ["G-cross"], [cls.cluster_a1]),
            ("P-cross-a2", cls.role("Cluster Action: Common Action"), ["G-cross"], [cls.cluster_a2]),
            # S-R7 (2 services) + S-R8
            ("P-multi-group", cls.role("Service Administrator"), ["G-multi-a", "G-multi-b"], [a1_svc_2, a2_svc_1]),
            # S-R7 (2 clusters)
            (
                "P-multi-a-clusters",
                cls.role("Edit cluster configurations"),
                ["G-multi-a"],
                [cls.cluster_a2, cls.cluster_b1],
            ),
            # C1: owner view through one policy, action view through another
            ("P-launch-owner", cls.role("View cluster configurations"), ["G-launch-only"], [cls.cluster_a2]),
            ("P-launch-action", cls.role("Cluster Action: Common Action"), ["G-launch-only"], [cls.cluster_a2]),
            # S-R7 (2 hosts), group without users
            (
                "P-empty-hosts",
                cls.role("Edit host configurations"),
                ["G-empty"],
                [cls.hosts["h-one"], cls.hosts["h-a2"]],
            ),
        )

        for name, role, group_names, objects in policies:
            policy_create(name=name, role=role, group=[groups[group] for group in group_names], object=objects)

        users: Iterable[tuple[str, list[str]]] = (
            ("U-overlap", ["G-solo-cluster-admin", "G-solo-view-cluster-config"]),
            ("U-mixed", ["G-solo-service-admin", "G-solo-provider-admin", "G-cross"]),
            ("U-multi", ["G-multi-a", "G-overlap"]),
            ("U-launch", ["G-launch-only", "G-solo-cluster-action"]),
            ("U-single", ["G-solo-custom"]),
            ("U-none", []),
            ("U-idle", ["G-idle"]),
        )

        for username, group_names in users:
            user = cls.uc.create_user(username=username, password=f"{username}-password")
            user.groups.add(*(groups[group] for group in group_names))

    @classmethod
    def launch_tasks(cls) -> None:
        a1_task = cls.launch_action(owner=cls.cluster_a1, action_name="common")
        cls.launch_action(owner=cls.service("A1", "svc_1"), action_name="common")
        cls.launch_action(owner=cls.component("A1", "svc_1", "comp_1"), action_name="common")
        cls.launch_action(owner=cls.provider_p1, action_name="common")
        cls.launch_action(owner=cls.hosts["h-one"], action_name="common")
        cls.launch_action(owner=cls.cluster_a1, action_name="on_host", target=cls.hosts["h-one"])
        cls.launch_action(
            owner=cls.cluster_a1,
            action_name="in_ahg",
            target=ActionHostGroup.objects.get(object_id=cls.cluster_a1.pk, name="ahg-cluster"),
        )

        adcm = ADCM.objects.get()
        cls.uc.change_config(
            adcm,
            values_diff={
                "global": {"adcm_url": "http://adcm.test"},
                "ldap_integration": {
                    "ldap_uri": "ldap://localhost",
                    "ldap_user": "ldap-user",
                    "ldap_password": "ldap-password",
                    "user_search_base": "dc=adcm",
                },
            },
            meta_diff={"/ldap_integration": {"isActive": True}},
        )
        cls.launch_action(owner=adcm, action_name="test_ldap_connection")

        job = JobLog.objects.filter(task=a1_task).order_by("id").first()
        if job is None:
            message = "Task has no jobs"
            raise RuntimeError(message)

        custom_log = LogStorage.objects.create(job=job, name="custom", type="custom", format="txt", body="custom")
        assign_view_logstorage_permissions_by_job(log_storage_id=custom_log.pk)

        with cls.container(scope=dishka.Scope.REQUEST) as request_container:
            request_container.get(AddCheckLogRecordForJob).do(
                job_id=job.pk,
                check_log_arguments=CheckLogArguments(title="check", result=True, success_msg="ok", fail_msg="fail"),
            )

    @classmethod
    def rotate_task(cls, task: TaskLog) -> None:
        """Delete task as `logrotate` does: TaskLog first, then JobLogs left without task"""

        TaskLog.objects.filter(pk=task.pk).delete()
        JobLog.objects.filter(task__isnull=True).delete()

    # Helpers

    @classmethod
    def launch_action(
        cls,
        owner: ADCM | Cluster | Service | Component | Provider | Host,
        action_name: str,
        target: ActionTarget | None = None,
    ) -> TaskLog:
        """
        Launch action as the `run` endpoint does (TaskRole + E4 re-apply), task isn't executed.

        Task is finished right away, so the same action can be launched again on the same object.
        """

        action = Action.objects.get(prototype=owner.prototype, name=action_name)

        with cls.container(scope=dishka.Scope.REQUEST) as request_container:
            task = request_container.get(ScheduleTask).do(
                action_orm=action, target=target or owner, payload=RunActionDTO()
            )

        now = timezone.now()
        TaskLog.objects.filter(pk=task.pk).update(status=JobStatus.SUCCESS, start_date=now, finish_date=now)
        JobLog.objects.filter(task=task).update(status=JobStatus.SUCCESS, start_date=now, finish_date=now)

        return task

    @classmethod
    def add_cluster_with_services(cls, bundle: Bundle, name: str, services: list[str]) -> Cluster:
        cluster = cls.uc.add_cluster(bundle=bundle, name=name)
        cls.uc.add_services_to_cluster(names=services, cluster=cluster)

        return cluster

    @staticmethod
    def service(cluster: str, service: str) -> Service:
        return Service.objects.get(cluster__name=cluster, prototype__name=service)

    @staticmethod
    def component(cluster: str, service: str, component: str) -> Component:
        return Component.objects.get(cluster__name=cluster, service__prototype__name=service, prototype__name=component)

    @staticmethod
    def role(name: str) -> Role:
        return Role.objects.get(name=name, built_in=True)
