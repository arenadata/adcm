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
Behavior "freeze" of bundle revert (rollback of cluster/provider to the bundle it was upgraded from).

Revert is performed only by `bundle_revert` internal script, so each scenario upgrades the target via API
(no scripts), changes what's required after upgrade and then runs `revert_upgrade` action of new version.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Final

from cm.models import (
    Action,
    ActionHostGroup,
    Bundle,
    Cluster,
    ClusterBind,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    ConfigHostGroup,
    ConfigLog,
    Host,
    HostComponent,
    LogStorage,
    MainObject,
    ObjectType,
    Prototype,
    Provider,
    Service,
    TaskLog,
    Upgrade,
)
from rbac.models import Role
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from unittest_parametrize import param, parametrize
import dishka

from tests.dependencies import MockWithEnvProvider, get_status_scenarios_manager, make_overridden_container
from tests.suites import SETUP_WITH_RBAC, ADCMDjangoAPISuiteNoBundles

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "bundle_revert"
SWITCH_REVERT_BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "switch_revert"

STATE_BEFORE_UPGRADE: Final = "installed"
STATE_AFTER_UPGRADE: Final = "changed_after_upgrade"


def run_upgrade(case: ADCMDjangoAPISuiteNoBundles, target: Cluster | Provider, upgrade: Upgrade) -> None:
    """Runs upgrade without scripts via API, so switch is performed right in the request"""

    response = case.client.v2[target, "upgrades", upgrade, "run"].post()
    case.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)


def run_revert(
    case: ADCMDjangoAPISuiteNoBundles,
    target: Cluster | Provider,
    expected_status: str = "success",
    task_runner_container: dishka.Container | None = None,
) -> int:
    """Runs `revert_upgrade` action of target's current prototype, launches its task and returns task's id"""

    target.refresh_from_db(fields=["prototype"])
    action = Action.objects.get(prototype=target.prototype, name="revert_upgrade")

    response = case.client.v2[target, "actions", action, "run"].post()
    case.assertEqual(response.status_code, HTTP_200_OK, response.content)
    task_id = response.json()["id"]

    case.task_runner(task_runner_container).launch_task(task_id)

    case.assertEqual(TaskLog.objects.values_list("status", flat=True).get(id=task_id), expected_status)

    return task_id


def bind_to_exporter(case: ADCMDjangoAPISuiteNoBundles, importer: Cluster | Service, exporter: Cluster) -> None:
    response = case.client.v2[importer, "imports"].post(data=[{"source": {"id": exporter.pk, "type": "cluster"}}])
    case.assertEqual(response.status_code, HTTP_201_CREATED, response.content)


def get_upgrades(bundle: Bundle) -> dict[str, Upgrade]:
    return {upgrade.name: upgrade for upgrade in Upgrade.objects.filter(bundle=bundle)}


def get_prototypes(bundle: Bundle) -> dict[tuple[str, str], Prototype]:
    return {(prototype.type, prototype.name): prototype for prototype in Prototype.objects.filter(bundle=bundle)}


def get_current_config(owner: MainObject | ConfigHostGroup) -> ConfigLog:
    owner.refresh_from_db(fields=["config"])
    return ConfigLog.objects.get(id=owner.config.current)  # pyright: ignore[reportOptionalMemberAccess]


def get_hostcomponent_names(cluster: Cluster) -> set[tuple[str, str, str]]:
    return set(
        HostComponent.objects.filter(cluster=cluster).values_list(
            "host__fqdn", "service__prototype__name", "component__prototype__name"
        )
    )


def keep_group(case: ADCMDjangoAPISuiteNoBundles, group: ConfigHostGroup) -> None:
    _ = case, group


def delete_group(case: ADCMDjangoAPISuiteNoBundles, group: ConfigHostGroup) -> None:
    response = case.client.v2[group.object, "config-groups", str(group.pk)].delete()
    case.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)


def delete_group_config_before_upgrade(case: ADCMDjangoAPISuiteNoBundles, group: ConfigHostGroup) -> None:
    owner = group.object
    owner.refresh_from_db(fields=["before_upgrade"])
    config_id = owner.before_upgrade["config_host_groups"][group.name]["config_id"]
    case.assertTrue(ConfigLog.objects.filter(id=config_id).exists())

    ConfigLog.objects.filter(id=config_id).delete()


class TestClusterBundleRevert(ADCMDjangoAPISuiteNoBundles):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cluster_bundle_v1 = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v1")
        cls.cluster_bundle_v2 = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v2")
        cls.upgrade = get_upgrades(cls.cluster_bundle_v2)["api"]
        cls.prototypes_v1 = get_prototypes(cluster_bundle_v1)

        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle_v1, name="Reverted")
        cls.uc.add_services_to_cluster(
            names=["service_kept", "service_removed", "service_without_config"], cluster=cls.cluster
        )
        cls.service_kept = Service.objects.get(cluster=cls.cluster, prototype__name="service_kept")
        cls.service_removed = Service.objects.get(cluster=cls.cluster, prototype__name="service_removed")
        cls.service_without_config = Service.objects.get(cluster=cls.cluster, prototype__name="service_without_config")
        cls.component_kept = Component.objects.get(service=cls.service_kept, prototype__name="component_kept")
        cls.component_removed = Component.objects.get(service=cls.service_kept, prototype__name="component_removed")
        cls.component_of_removed = Component.objects.get(service=cls.service_removed)

        provider = cls.uc.add_provider(
            bundle=cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "provider_v1"), name="Hosts Source"
        )
        cls.host_1 = cls.uc.add_host_to_cluster(cluster=cls.cluster, host=cls.uc.add_host(provider=provider, fqdn="h1"))
        cls.host_2 = cls.uc.add_host_to_cluster(cluster=cls.cluster, host=cls.uc.add_host(provider=provider, fqdn="h2"))

        exporter_bundle = cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "exporter")
        cls.exporter = cls.uc.add_cluster(bundle=exporter_bundle, name="Exporter")
        cls.another_exporter = cls.uc.add_cluster(bundle=exporter_bundle, name="Another Exporter")

        # state that should be restored by revert
        cls.uc.set_hostcomponent(
            cluster=cls.cluster,
            entries=[
                (cls.host_1, cls.component_kept),
                (cls.host_2, cls.component_kept),
                (cls.host_2, cls.component_removed),
                (cls.host_1, cls.component_of_removed),
            ],
        )
        cls.hostcomponent_before_upgrade = {
            ("h1", "service_kept", "component_kept"),
            ("h2", "service_kept", "component_kept"),
            ("h2", "service_kept", "component_removed"),
            ("h1", "service_removed", "component_of_removed"),
        }

        for object_ in (
            cls.service_kept,
            cls.component_kept,
            cls.component_removed,
            cls.service_removed,
            cls.component_of_removed,
        ):
            object_.set_state(STATE_BEFORE_UPGRADE)

        cls.uc.change_config(cls.cluster, values_diff={"kept": "cluster-before", "removed": 10})
        cls.uc.change_config(cls.service_kept, values_diff={"kept": "service-before", "removed": 20})
        cls.uc.change_config(cls.service_removed, values_diff={"value": "service-removed-before"})

        cls.cluster_group = cls.uc.add_config_host_group(owner=cls.cluster, name="Cluster Group")
        cls.cluster_group.hosts.add(cls.host_1)
        cls.uc.change_config(
            cls.cluster_group, values_diff={"kept": "group-own"}, meta_diff={"/kept": {"isSynchronized": False}}
        )

        removed_service_group = cls.uc.add_config_host_group(owner=cls.service_removed, name="Removed Service Group")
        removed_service_group.hosts.add(cls.host_1)
        cls.uc.change_config(
            removed_service_group, values_diff={"value": "group-own"}, meta_diff={"/value": {"isSynchronized": False}}
        )

        action_group = cls.uc.create_action_host_group(name="Removed Service Actions", owner=cls.service_removed)
        cls.uc.add_hosts_to_action_host_group(group_id=action_group.pk, hosts=[cls.host_1.pk])

    def setUp(self) -> None:
        super().setUp()

        # cluster's import is required
        bind_to_exporter(self, importer=self.cluster, exporter=self.exporter)
        bind_to_exporter(self, importer=self.service_kept, exporter=self.exporter)

    def test_kept_objects_reverted(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        self.cluster.refresh_from_db(fields=["state"])
        self.assertEqual(self.cluster.state, "upgraded")
        for object_ in (self.service_kept, self.component_kept):
            object_.set_state(STATE_AFTER_UPGRADE)
        self.uc.change_config(self.cluster, values_diff={"kept": "cluster-after"})
        self.uc.change_config(self.service_kept, values_diff={"kept": "service-after"})
        config_gained_on_upgrade = get_current_config(self.service_without_config)
        self.assertDictEqual(config_gained_on_upgrade.config, {"added": "service-gains-config"})
        # only events of revert are counted
        get_status_scenarios_manager().reset()

        run_revert(self, target=self.cluster)

        self.assertEqual(get_status_scenarios_manager().get_calls("send_prototype_and_state_update_event"), 1)

        expected = (
            (self.cluster, self.prototypes_v1["cluster", "revert_cluster"], "created"),
            (self.service_kept, self.prototypes_v1["service", "service_kept"], STATE_BEFORE_UPGRADE),
            (self.component_kept, self.prototypes_v1["component", "component_kept"], STATE_BEFORE_UPGRADE),
            (self.service_without_config, self.prototypes_v1["service", "service_without_config"], "created"),
        )
        for object_, prototype, state in expected:
            object_.refresh_from_db()
            self.assertEqual(object_.prototype, prototype)
            self.assertEqual(object_.state, state)
            self.assertDictEqual(object_.before_upgrade, {"state": None})

        cluster_config = get_current_config(self.cluster)
        self.assertDictEqual(cluster_config.config, {"kept": "cluster-before", "removed": 10})
        self.assertEqual(cluster_config.description, "revert_upgrade")

        service_config = get_current_config(self.service_kept)
        self.assertDictEqual(service_config.config, {"kept": "service-before", "removed": 20})
        self.assertEqual(service_config.description, "revert_upgrade")

        # object had no config before upgrade, so the one it got on upgrade stays
        self.assertEqual(get_current_config(self.service_without_config), config_gained_on_upgrade)

    def test_hierarchy_reverted(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        self.cluster.refresh_from_db(fields=["prototype"])
        self.uc.add_services_to_cluster(names=["service_v2_only"], cluster=self.cluster)
        self.assertCountEqual(
            Component.objects.filter(cluster=self.cluster, prototype__bundle=self.cluster_bundle_v2).values_list(
                "prototype__name", flat=True
            ),
            ["component_kept", "component_added", "component_of_v2_only"],
        )

        run_revert(self, target=self.cluster)

        # objects of new bundle are deleted, the ones removed by switch are restored
        self.assertCountEqual(
            Service.objects.filter(cluster=self.cluster).values_list("prototype", flat=True),
            [
                self.prototypes_v1["service", name].pk
                for name in ("service_kept", "service_removed", "service_without_config")
            ],
        )
        self.assertCountEqual(
            Component.objects.filter(cluster=self.cluster).values_list("prototype", flat=True),
            [
                self.prototypes_v1["component", name].pk
                for name in ("component_kept", "component_removed", "component_of_removed")
            ],
        )

        component = Component.objects.get(service=self.service_kept, prototype__name="component_removed")
        self.assertEqual(component.state, STATE_BEFORE_UPGRADE)

        service = Service.objects.get(cluster=self.cluster, prototype__name="service_removed")
        self.assertEqual(service.state, STATE_BEFORE_UPGRADE)

        service_config = get_current_config(service)
        self.assertDictEqual(service_config.config, {"value": "service-removed-before"})
        self.assertEqual(service_config.description, "revert_upgrade")

        config_group = ConfigHostGroup.objects.get(object_id=service.pk, object_type=service.content_type)
        self.assertEqual(config_group.name, "Removed Service Group")
        self.assertEqual(config_group.description, "revert_upgrade")
        self.assertListEqual(list(config_group.hosts.values_list("fqdn", flat=True)), ["h1"])
        group_config = get_current_config(config_group)
        self.assertDictEqual(group_config.config, {"value": "group-own"})
        self.assertDictEqual(group_config.attr["group_keys"], {"value": True})

        action_group = ActionHostGroup.objects.get(object_id=service.pk, object_type=service.content_type)
        self.assertEqual(action_group.name, "Removed Service Actions")
        self.assertEqual(action_group.description, "revert_upgrade")
        self.assertListEqual(list(action_group.hosts.values_list("fqdn", flat=True)), ["h1"])

        self.assertEqual(Component.objects.get(service=service).state, STATE_BEFORE_UPGRADE)

    def test_service_removed_by_user_after_upgrade_not_restored(self) -> None:
        # ADCM-8315: deleted service is indistinguishable from the one removed by switch
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        response = self.client.v2[self.service_without_config].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

        run_revert(self, target=self.cluster)

        self.assertCountEqual(
            Service.objects.filter(cluster=self.cluster).values_list("prototype__name", flat=True),
            ["service_kept", "service_removed"],
        )

    def test_hostcomponent_restored(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(self.host_1, self.component_kept)])

        run_revert(self, target=self.cluster)

        self.assertSetEqual(get_hostcomponent_names(self.cluster), self.hostcomponent_before_upgrade)

    @parametrize(
        "lose_data,expected_config,expected_group_keys",
        [
            param(keep_group, {"kept": "group-own", "removed": 10}, {"kept": True, "removed": False}, id="kept"),
            param(
                delete_group, {"kept": "group-own", "removed": 10}, {"kept": True, "removed": False}, id="chg_deleted"
            ),
            param(
                delete_group_config_before_upgrade,
                {"kept": "cluster-before", "removed": 10},
                {"kept": False, "removed": False},
                id="configlog_deleted",
            ),
        ],
    )
    def test_config_host_group_restored(
        self,
        lose_data: Callable[[ADCMDjangoAPISuiteNoBundles, ConfigHostGroup], None],
        expected_config: dict,
        expected_group_keys: dict,
    ) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        self.uc.change_config(self.cluster_group, values_diff={"kept": "group-after"})
        lose_data(self, self.cluster_group)

        run_revert(self, target=self.cluster)

        group = ConfigHostGroup.objects.get(
            object_id=self.cluster.pk, object_type=self.cluster.content_type, name="Cluster Group"
        )
        self.assertListEqual(list(group.hosts.values_list("fqdn", flat=True)), ["h1"])
        group_config = get_current_config(group)
        self.assertDictEqual(group_config.config, expected_config)
        self.assertDictEqual(group_config.attr["group_keys"], expected_group_keys)

    def test_binds_restored(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        # service's import is dropped by upgrade, cluster's one is replaced
        bind_to_exporter(self, importer=self.cluster, exporter=self.another_exporter)
        self.assertListEqual(
            list(ClusterBind.objects.filter(cluster=self.cluster).values_list("service_id", "source_cluster_id")),
            [(None, self.another_exporter.pk)],
        )

        run_revert(self, target=self.cluster)

        self.assertCountEqual(
            ClusterBind.objects.filter(cluster=self.cluster).values_list(
                "service_id", "source_cluster_id", "source_service_id"
            ),
            [(None, self.exporter.pk, None), (self.service_kept.pk, self.exporter.pk, None)],
        )

    def test_import_issue_on_required_import_without_bind(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        response = self.client.v2[self.exporter].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)
        self.assertFalse(
            ConcernItem.objects.filter(
                type=ConcernType.ISSUE,
                cause=ConcernCause.IMPORT,
                owner_id=self.cluster.pk,
                owner_type=self.cluster.content_type,
            ).exists()
        )

        run_revert(self, target=self.cluster)

        issue = ConcernItem.objects.get(
            type=ConcernType.ISSUE,
            cause=ConcernCause.IMPORT,
            owner_id=self.cluster.pk,
            owner_type=self.cluster.content_type,
        )
        self.assertIn(issue, self.cluster.concerns.all())

    def test_missing_record_fails_revert(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        cluster_prototype_v2 = Prototype.objects.get(bundle=self.cluster_bundle_v2, type=ObjectType.CLUSTER)
        # host from `before_upgrade.hc` leaves the cluster
        self.uc.set_hostcomponent(cluster=self.cluster, entries=[(self.host_1, self.component_kept)])
        response = self.client.v2[self.cluster, "hosts", self.host_2].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)
        # only events of revert are counted
        get_status_scenarios_manager().reset()

        # internal script's error ends up in job's logs only with real (not mocked) internal executor
        task_id = run_revert(
            self,
            target=self.cluster,
            expected_status="failed",
            task_runner_container=make_overridden_container(MockWithEnvProvider()),
        )

        self.cluster.refresh_from_db(fields=["prototype"])
        self.assertEqual(self.cluster.prototype, cluster_prototype_v2)
        self.assertTrue(Component.objects.filter(cluster=self.cluster, prototype__name="component_added").exists())
        self.assertFalse(Service.objects.filter(cluster=self.cluster, prototype__name="service_removed").exists())
        stderr = LogStorage.objects.get(job__task_id=task_id, type="stderr").body
        self.assertIn("The configuration cannot be restored because the record was deleted.", stderr)
        # event is sent even though revert failed
        self.assertEqual(get_status_scenarios_manager().get_calls("send_prototype_and_state_update_event"), 1)


class TestProviderBundleRevert(ADCMDjangoAPISuiteNoBundles):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        provider_bundle_v1 = cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "provider_v1")
        cls.upgrade = get_upgrades(cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "provider_v2"))["api_with_state"]
        cls.prototypes_v1 = get_prototypes(provider_bundle_v1)

        cls.provider = cls.uc.add_provider(bundle=provider_bundle_v1, name="Reverted")
        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="h1")
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="h2")

        cls.host_1.set_state(STATE_BEFORE_UPGRADE)
        cls.uc.change_config(cls.provider, values_diff={"kept": "provider-before", "removed": 10})
        cls.uc.change_config(cls.host_1, values_diff={"kept": "host-before", "removed": 20})

    def test_provider_reverted(self) -> None:
        run_upgrade(self, target=self.provider, upgrade=self.upgrade)
        self.host_1.set_state(STATE_AFTER_UPGRADE)
        self.uc.change_config(self.provider, values_diff={"kept": "provider-after"})
        self.uc.change_config(self.host_1, values_diff={"kept": "host-after"})
        # only events of revert are counted
        get_status_scenarios_manager().reset()

        run_revert(self, target=self.provider)

        self.assertEqual(get_status_scenarios_manager().get_calls("send_prototype_and_state_update_event"), 1)

        self.provider.refresh_from_db()
        self.assertEqual(self.provider.prototype, self.prototypes_v1["provider", "revert_provider"])
        self.assertEqual(self.provider.state, "created")
        self.assertDictEqual(self.provider.before_upgrade, {"state": None})
        provider_config = get_current_config(self.provider)
        self.assertDictEqual(provider_config.config, {"kept": "provider-before", "removed": 10})
        self.assertEqual(provider_config.description, "revert_upgrade")

        host_prototype_v1 = self.prototypes_v1["host", "revert_host"]
        self.assertCountEqual(
            Host.objects.filter(provider=self.provider).values_list("fqdn", "prototype", "state"),
            [("h1", host_prototype_v1.pk, STATE_BEFORE_UPGRADE), ("h2", host_prototype_v1.pk, "created")],
        )
        host_config = get_current_config(self.host_1)
        self.assertDictEqual(host_config.config, {"kept": "host-before", "removed": 20})
        self.assertEqual(host_config.description, "revert_upgrade")
        self.assertDictEqual(get_current_config(self.host_2).config, {"kept": "host-kept", "removed": 2})


class TestBundleRevertPolicies(ADCMDjangoAPISuiteNoBundles):
    suite_setup = SETUP_WITH_RBAC

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cluster_bundle_v1 = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v1")
        cls.upgrade = get_upgrades(cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v2"))["api"]

        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle_v1, name="Reverted")
        cls.uc.add_services_to_cluster(names=["service_removed"], cluster=cls.cluster)
        cls.exporter = cls.uc.add_cluster(
            bundle=cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "exporter"), name="Exporter"
        )

        cls.user_credentials = {"username": "cluster_admin", "password": "cluster_admin_pass"}
        user = cls.uc.create_user(**cls.user_credentials)
        cls.group = cls.uc.create_group(display_name="Cluster Admins", users=[user.pk])

    def setUp(self) -> None:
        super().setUp()

        # cluster's import is required
        bind_to_exporter(self, importer=self.cluster, exporter=self.exporter)

    def test_policy_on_cluster_applied_to_restored_service(self) -> None:
        response = (self.client.v2 / "rbac" / "policies").post(
            data={
                "name": "Cluster Admins Policy",
                "role": {"id": Role.objects.get(name="Cluster Administrator").pk},
                "objects": [{"id": self.cluster.pk, "type": "cluster"}],
                "groups": [self.group.pk],
            }
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

        run_upgrade(self, target=self.cluster, upgrade=self.upgrade)
        run_revert(self, target=self.cluster)

        restored_service = Service.objects.get(cluster=self.cluster, prototype__name="service_removed")
        self.client.login(**self.user_credentials)
        response = self.client.v2[restored_service, "configs"].get()
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())
