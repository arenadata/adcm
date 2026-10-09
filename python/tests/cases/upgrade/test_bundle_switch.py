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
Behavior "freeze" of bundle switch (upgrade of cluster/provider to another bundle).

Switch is reachable in two ways: upgrade without scripts (API path, switch is performed right in the request)
and upgrade with `bundle_switch` internal script (task path, switch is performed by the task runner).
Both are expected to give the same result, so most of the scenarios are parametrized by `path`.
"""

from pathlib import Path
from typing import Final

from cm.models import (
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
    MainObject,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Provider,
    Service,
    TaskLog,
    Upgrade,
)
from rbac.models import Role
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_409_CONFLICT
from unittest_parametrize import param, parametrize

from tests.dependencies import get_status_scenarios_manager
from tests.suites import SETUP_WITH_RBAC, ADCMDjangoAPISuiteNoBundles

BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "bundle_switch"
SWITCH_REVERT_BUNDLES_DIR: Final = Path(__file__).parent / "bundles" / "switch_revert"

# `api` upgrades have no scripts (switch is performed during request),
# `task` ones have a single `bundle_switch` internal script
BY_PATH: Final = [param("api", id="api"), param("task", id="task")]


def run_upgrade(case: ADCMDjangoAPISuiteNoBundles, target: Cluster | Provider, upgrade: Upgrade) -> None:
    """Runs upgrade via API, if it's upgrade with scripts, launches its task and expects it to succeed"""

    response = case.client.v2[target, "upgrades", upgrade, "run"].post()

    if upgrade.action_id is None:  # pyright: ignore[reportAttributeAccessIssue]
        case.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)
        return

    case.assertEqual(response.status_code, HTTP_200_OK, response.content)
    task_id = response.json()["id"]

    case.task_runner().launch_task(task_id)

    case.assertEqual(TaskLog.objects.values_list("status", flat=True).get(id=task_id), "success")


def get_upgrades(bundle: Bundle) -> dict[str, Upgrade]:
    return {upgrade.name: upgrade for upgrade in Upgrade.objects.filter(bundle=bundle)}


def get_current_config(owner: MainObject | ConfigHostGroup) -> ConfigLog:
    owner.refresh_from_db(fields=["config"])
    return ConfigLog.objects.get(id=owner.config.current)  # pyright: ignore[reportOptionalMemberAccess]


def get_config_issue(owner: MainObject) -> ConcernItem:
    return ConcernItem.objects.get(
        type=ConcernType.ISSUE, cause=ConcernCause.CONFIG, owner_id=owner.pk, owner_type=owner.content_type
    )


class TestClusterBundleSwitch(ADCMDjangoAPISuiteNoBundles):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cluster_bundle_v1 = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v1")
        cls.cluster_bundle_v2 = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v2")
        cls.upgrades = get_upgrades(cls.cluster_bundle_v2)
        cls.upgrades_to_no_config_no_mm = get_upgrades(cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v2_no_config_no_mm"))
        cls.upgrades_to_required_param = get_upgrades(cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v2_required_param"))
        cls.upgrades_to_license = get_upgrades(cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v2_license"))
        # `allow_maintenance_mode` is the same in v1 and v2, but differs in "no_config_no_mm" one
        cls.task_upgrades_by_allow_mm = {
            "same": cls.upgrades["task"],
            "differs": cls.upgrades_to_no_config_no_mm["task"],
        }

        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle_v1, name="Switched")
        cls.uc.add_services_to_cluster(names=["service_kept", "service_removed"], cluster=cls.cluster)
        cls.service_kept = Service.objects.get(cluster=cls.cluster, prototype__name="service_kept")
        cls.service_removed = Service.objects.get(cluster=cls.cluster, prototype__name="service_removed")
        cls.component_kept = Component.objects.get(service=cls.service_kept, prototype__name="component_kept")
        cls.component_removed = Component.objects.get(service=cls.service_kept, prototype__name="component_removed")
        cls.component_of_removed = Component.objects.get(service=cls.service_removed)

        provider = cls.uc.add_provider(
            bundle=cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "provider_v1"), name="Hosts Source"
        )
        cls.host_1 = cls.uc.add_host_to_cluster(cluster=cls.cluster, host=cls.uc.add_host(provider=provider, fqdn="h1"))
        cls.host_2 = cls.uc.add_host_to_cluster(cluster=cls.cluster, host=cls.uc.add_host(provider=provider, fqdn="h2"))

        cls.exporter = cls.uc.add_cluster(
            bundle=cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "exporter"), name="Exporter"
        )

        prototypes_v2 = {
            (prototype.type, prototype.name): prototype
            for prototype in Prototype.objects.filter(bundle=cls.cluster_bundle_v2)
        }
        cls.cluster_prototype_v2 = prototypes_v2[ObjectType.CLUSTER, "switch_cluster"]
        cls.service_prototype_v2 = prototypes_v2[ObjectType.SERVICE, "service_kept"]
        cls.expected_components = {
            "component_kept": prototypes_v2[ObjectType.COMPONENT, "component_kept"],
            "component_added": prototypes_v2[ObjectType.COMPONENT, "component_added"],
        }

        cls.expected_deleted_services = {
            "service_removed": {
                "state": "created",
                "config": {"data": {"value": "service-removed"}, "attributes": {}},
                "config_host_groups": {},
                "action_host_groups": {},
                "components": {
                    "component_of_removed": {
                        "state": "created",
                        "config": None,
                        "config_host_groups": {},
                        "action_host_groups": {},
                    }
                },
            }
        }
        cls.expected_service_deleted_components = {
            "service_kept": {
                "component_removed": {
                    "state": "created",
                    "config": None,
                    "config_host_groups": {},
                    "action_host_groups": {},
                }
            }
        }

    @parametrize("path", BY_PATH)
    def test_cluster_switch(self, path: str) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[path])

        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.prototype, self.cluster_prototype_v2)

        # removed service is deleted, kept one is switched
        self.assertListEqual(
            list(Service.objects.filter(cluster=self.cluster).values_list("id", "prototype")),
            [(self.service_kept.pk, self.service_prototype_v2.pk)],
        )

        # removed component is deleted, kept one is switched, missing one is created
        components = {
            component.prototype.name: component
            for component in Component.objects.select_related("prototype").filter(cluster=self.cluster)
        }
        self.assertDictEqual(
            {name: component.prototype for name, component in components.items()}, self.expected_components
        )
        self.assertEqual(components["component_kept"].pk, self.component_kept.pk)
        self.assertDictEqual(get_current_config(components["component_added"]).config, {"added": "component-added"})

        # deleted objects are recorded in cluster's before upgrade
        self.assertDictEqual(self.cluster.before_upgrade["deleted_services"], self.expected_deleted_services)
        self.assertDictEqual(
            self.cluster.before_upgrade["service_deleted_components"], self.expected_service_deleted_components
        )

    @parametrize("path", BY_PATH)
    def test_config_adaptation(self, path: str) -> None:
        self.uc.change_config(self.cluster, values_diff={"kept": "cluster-changed", "removed": 100})
        self.uc.change_config(self.service_kept, values_diff={"kept": "service-changed", "removed": 200})

        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[path])

        cluster_config = get_current_config(self.cluster)
        self.assertDictEqual(cluster_config.config, {"kept": "cluster-changed", "added": "cluster-added"})
        self.assertEqual(cluster_config.description, "upgrade")

        service_config = get_current_config(self.service_kept)
        self.assertDictEqual(service_config.config, {"kept": "service-changed", "added": "service-added"})
        self.assertEqual(service_config.description, "upgrade")

    @parametrize("path", BY_PATH)
    def test_config_created_for_object_without_config(self, path: str) -> None:
        service, *_ = self.uc.add_services_to_cluster(names=["service_gains_config"], cluster=self.cluster)
        self.assertIsNone(service.config)

        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[path])

        self.assertDictEqual(get_current_config(service).config, {"added": "service-gains-config"})

    @parametrize("path", BY_PATH)
    def test_empty_config_created_for_object_without_config_in_both_versions(self, path: str) -> None:
        # `Defaults` of empty spec is still truthy, so initial config is created anyway
        service, *_ = self.uc.add_services_to_cluster(names=["service_without_config"], cluster=self.cluster)
        self.assertIsNone(service.config)

        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[path])

        self.assertDictEqual(get_current_config(service).config, {})

    @parametrize("path", BY_PATH)
    def test_config_host_group_adapted_to_new_spec(self, path: str) -> None:
        group = self.uc.add_config_host_group(owner=self.cluster, name="Own Values")
        group.hosts.add(self.host_1)
        self.uc.change_config(group, values_diff={"kept": "group-own"}, meta_diff={"/kept": {"isSynchronized": False}})

        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[path])

        group_config = get_current_config(group)
        self.assertDictEqual(group_config.config, {"kept": "group-own", "added": "cluster-added"})
        self.assertDictEqual(group_config.attr["group_keys"], {"kept": True, "added": False})

    @parametrize("path", BY_PATH)
    def test_config_host_group_removed_on_empty_spec(self, path: str) -> None:
        group = self.uc.add_config_host_group(owner=self.cluster, name="Own Values")
        group.hosts.add(self.host_1)
        self.uc.change_config(group, values_diff={"kept": "group-own"}, meta_diff={"/kept": {"isSynchronized": False}})

        run_upgrade(self, target=self.cluster, upgrade=self.upgrades_to_no_config_no_mm[path])

        self.assertFalse(ConfigHostGroup.objects.filter(id=group.pk).exists())

    @parametrize("path", BY_PATH)
    def test_hostcomponent_of_removed_components_deleted(self, path: str) -> None:
        self.uc.set_hostcomponent(
            cluster=self.cluster,
            entries=[
                (self.host_1, self.component_kept),
                (self.host_2, self.component_kept),
                (self.host_2, self.component_removed),
                (self.host_1, self.component_of_removed),
            ],
        )

        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[path])

        self.assertCountEqual(
            HostComponent.objects.filter(cluster=self.cluster).values_list("host_id", "component_id"),
            [(self.host_1.pk, self.component_kept.pk), (self.host_2.pk, self.component_kept.pk)],
        )

    @parametrize(
        "allow_mm,expected_mm",
        [
            param("same", MaintenanceMode.ON, id="allow_mm_same"),
            param("differs", MaintenanceMode.OFF, id="allow_mm_differs"),
        ],
    )
    def test_maintenance_mode_reset(self, allow_mm: str, expected_mm: MaintenanceMode) -> None:
        # upgrade can't be started with hosts in MM, so hosts get there while task is already queued
        # (like an earlier job of upgrade would do it)
        response = self.client.v2[self.cluster, "upgrades", self.task_upgrades_by_allow_mm[allow_mm], "run"].post()
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())
        task_id = response.json()["id"]
        task_runner = self.task_runner()
        task_runner.schedule_task(task_id=task_id)
        task_runner.queue_task(task_id=task_id)

        Host.objects.filter(cluster=self.cluster).update(maintenance_mode=MaintenanceMode.ON)

        task_runner.launch_task(task_id)

        self.assertEqual(TaskLog.objects.values_list("status", flat=True).get(id=task_id), "success")
        self.assertCountEqual(
            Host.objects.filter(cluster=self.cluster).values_list("maintenance_mode", flat=True),
            [expected_mm, expected_mm],
        )

    @parametrize("path", BY_PATH)
    def test_binds_of_dropped_imports_deleted(self, path: str) -> None:
        source = [{"source": {"id": self.exporter.pk, "type": "cluster"}}]
        for importer in (self.cluster, self.service_kept):
            response = self.client.v2[importer, "imports"].post(data=source)
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[path])

        # service's import is dropped in new version, cluster's one is kept
        self.assertListEqual(
            list(
                ClusterBind.objects.filter(cluster=self.cluster).values_list(
                    "service_id", "source_cluster_id", "source_service_id"
                )
            ),
            [(None, self.exporter.pk, None)],
        )

    @parametrize(
        "upgrade_name,expected_state",
        [
            param("api", "created", id="api_without_state"),
            param("task", "created", id="task_without_state"),
            param("api_with_state", "upgraded", id="api_with_state"),
            param("task_with_state", "upgraded", id="task_with_state"),
        ],
    )
    def test_state_on_success(self, upgrade_name: str, expected_state: str) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrades[upgrade_name])

        self.cluster.refresh_from_db(fields=["state"])
        self.assertEqual(self.cluster.state, expected_state)

    def test_api_upgrade_sends_prototype_and_state_update_event(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrades["api"])

        self.assertEqual(get_status_scenarios_manager().get_calls("send_prototype_and_state_update_event"), 1)

    def test_config_issue_on_new_required_param_without_default(self) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrades_to_required_param["api"])

        issue = get_config_issue(self.cluster)
        # own issue is distributed over cluster's hierarchy
        for related_object in (self.cluster, self.service_kept, self.component_kept):
            self.assertIn(issue, related_object.concerns.all())

    @parametrize("path", BY_PATH)
    def test_concern_notification_on_config_issue(self, path: str) -> None:
        run_upgrade(self, target=self.cluster, upgrade=self.upgrades_to_required_param[path])

        self.assertEqual(get_status_scenarios_manager().get_calls("notify_about_redistributed_concerns_from_maps"), 1)

    def test_unaccepted_service_license_fail(self) -> None:
        initial_prototype = self.cluster.prototype

        response = self.client.v2[self.cluster, "upgrades", self.upgrades_to_license["api"], "run"].post()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "LICENSE_ERROR")
        self.assertEqual(response.json()["desc"], 'License for prototype "service_kept" service 2.3 is not accepted')
        self.cluster.refresh_from_db(fields=["prototype"])
        self.assertEqual(self.cluster.prototype, initial_prototype)


class TestProviderBundleSwitch(ADCMDjangoAPISuiteNoBundles):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        provider_bundle_v1 = cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "provider_v1")
        provider_bundle_v2 = cls.uc.upload_bundle(SWITCH_REVERT_BUNDLES_DIR / "provider_v2")
        cls.upgrades = get_upgrades(provider_bundle_v2)
        cls.upgrades_to_required_param = get_upgrades(cls.uc.upload_bundle(BUNDLES_DIR / "provider_v2_required_param"))

        cls.provider = cls.uc.add_provider(bundle=provider_bundle_v1, name="Switched")
        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="h1")
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="h2")

        cls.cluster_bundle = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v1")

        cls.provider_prototype_v2 = Prototype.objects.get(bundle=provider_bundle_v2, type=ObjectType.PROVIDER)
        cls.host_prototype_v2 = Prototype.objects.get(bundle=provider_bundle_v2, type=ObjectType.HOST)

    @parametrize("path", BY_PATH)
    def test_provider_switch(self, path: str) -> None:
        run_upgrade(self, target=self.provider, upgrade=self.upgrades[path])

        self.provider.refresh_from_db()
        self.assertEqual(self.provider.prototype, self.provider_prototype_v2)
        self.assertCountEqual(
            Host.objects.filter(provider=self.provider).values_list("id", "prototype"),
            [(self.host_1.pk, self.host_prototype_v2.pk), (self.host_2.pk, self.host_prototype_v2.pk)],
        )

    @parametrize("path", BY_PATH)
    def test_config_adaptation(self, path: str) -> None:
        self.uc.change_config(self.provider, values_diff={"kept": "provider-changed", "removed": 100})
        self.uc.change_config(self.host_1, values_diff={"kept": "host-changed", "removed": 200})

        run_upgrade(self, target=self.provider, upgrade=self.upgrades[path])

        provider_config = get_current_config(self.provider)
        self.assertDictEqual(provider_config.config, {"kept": "provider-changed", "added": "provider-added"})
        self.assertEqual(provider_config.description, "upgrade")

        host_config = get_current_config(self.host_1)
        self.assertDictEqual(host_config.config, {"kept": "host-changed", "added": "host-added"})
        self.assertEqual(host_config.description, "upgrade")

        # not changed by user
        self.assertDictEqual(get_current_config(self.host_2).config, {"kept": "host-kept", "added": "host-added"})

    @parametrize(
        "upgrade_name,expected_state",
        [
            param("api", "created", id="api_without_state"),
            param("task", "created", id="task_without_state"),
            param("api_with_state", "upgraded", id="api_with_state"),
            param("task_with_state", "upgraded", id="task_with_state"),
        ],
    )
    def test_state_on_success(self, upgrade_name: str, expected_state: str) -> None:
        run_upgrade(self, target=self.provider, upgrade=self.upgrades[upgrade_name])

        self.provider.refresh_from_db(fields=["state"])
        self.assertEqual(self.provider.state, expected_state)

    def test_config_issue_on_new_required_param_without_default(self) -> None:
        run_upgrade(self, target=self.provider, upgrade=self.upgrades_to_required_param["api"])

        provider_issue = get_config_issue(self.provider)
        self.assertIn(provider_issue, self.provider.concerns.all())

        for host in (self.host_1, self.host_2):
            host_issue = get_config_issue(host)
            # provider's issue is distributed to its hosts
            self.assertCountEqual(
                host.concerns.filter(type=ConcernType.ISSUE, cause=ConcernCause.CONFIG), [provider_issue, host_issue]
            )

    def test_config_issue_of_host_in_cluster_fails_api_switch(self) -> None:
        # Pins legacy `KeyError` in provider's concern merge: `removed` map is a plain dict,
        # so redistribution in host's cluster that removes concerns breaks the switch.
        # Deferred to its own fix.
        cluster = self.uc.add_cluster(bundle=self.cluster_bundle, name="Hosts Consumer")
        service, *_ = self.uc.add_services_to_cluster(names=["service_kept"], cluster=cluster)
        component = Component.objects.get(service=service, prototype__name="component_kept")
        self.uc.add_host_to_cluster(cluster=cluster, host=self.host_1)
        self.uc.set_hostcomponent(cluster=cluster, entries=[(self.host_1, component)])
        initial_prototype = self.provider.prototype

        # API request doesn't handle this error, so it gets out of it
        with self.assertRaises(KeyError):
            run_upgrade(self, target=self.provider, upgrade=self.upgrades_to_required_param["api"])

        self.provider.refresh_from_db(fields=["prototype"])
        self.assertEqual(self.provider.prototype, initial_prototype)

    def test_config_issue_of_host_in_cluster_fails_task_switch(self) -> None:
        # Pins the same legacy `KeyError` bug as on API path (deferred to its own fix),
        # but internal script's executor catches it, so the job fails
        cluster = self.uc.add_cluster(bundle=self.cluster_bundle, name="Hosts Consumer")
        service, *_ = self.uc.add_services_to_cluster(names=["service_kept"], cluster=cluster)
        component = Component.objects.get(service=service, prototype__name="component_kept")
        self.uc.add_host_to_cluster(cluster=cluster, host=self.host_1)
        self.uc.set_hostcomponent(cluster=cluster, entries=[(self.host_1, component)])
        initial_prototype = self.provider.prototype

        response = self.client.v2[self.provider, "upgrades", self.upgrades_to_required_param["task"], "run"].post()
        self.assertEqual(response.status_code, HTTP_200_OK, response.content)
        task_id = response.json()["id"]

        self.task_runner().launch_task(task_id)

        self.assertEqual(TaskLog.objects.values_list("status", flat=True).get(id=task_id), "failed")
        self.provider.refresh_from_db(fields=["prototype"])
        self.assertEqual(self.provider.prototype, initial_prototype)

    @parametrize("path", BY_PATH)
    def test_concern_notification_on_config_issue(self, path: str) -> None:
        run_upgrade(self, target=self.provider, upgrade=self.upgrades_to_required_param[path])

        self.assertEqual(get_status_scenarios_manager().get_calls("notify_about_redistributed_concerns_from_maps"), 1)


class TestBundleSwitchPolicies(ADCMDjangoAPISuiteNoBundles):
    suite_setup = SETUP_WITH_RBAC

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cluster_bundle_v1 = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v1")
        cls.upgrade = get_upgrades(cls.uc.upload_bundle(BUNDLES_DIR / "cluster_v2"))["api"]

        cls.cluster = cls.uc.add_cluster(bundle=cluster_bundle_v1, name="Switched")
        cls.service_kept, *_ = cls.uc.add_services_to_cluster(names=["service_kept"], cluster=cls.cluster)

        cls.user_credentials = {"username": "cluster_admin", "password": "cluster_admin_pass"}
        user = cls.uc.create_user(**cls.user_credentials)
        cls.group = cls.uc.create_group(display_name="Cluster Admins", users=[user.pk])

    def test_policy_on_cluster_applied_to_added_component(self) -> None:
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

        added_component = Component.objects.get(service=self.service_kept, prototype__name="component_added")
        self.client.login(**self.user_credentials)
        response = self.client.v2[added_component, "configs"].get()
        self.assertEqual(response.status_code, HTTP_200_OK, response.json())
        self.assertEqual(response.json()["count"], 1)
