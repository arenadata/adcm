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
Scenarios of the RBAC write-side equivalence suite (ADCM-8502).

All scenarios live in one suite, so the shared setup is built once.
G1: non-RBAC triggers of the RBAC write side.
"""

from datetime import timedelta
from typing import Final
from unittest.mock import patch

from ansible_collections.arenadata.adcm.plugins.lookup.adcm_config import PluginResult, call_adcm_config_lookup
from ansible_plugin.executors.add_host import ADCMAddHostPluginExecutor
from ansible_plugin.executors.add_host_to_cluster import ADCMAddHostToClusterPluginExecutor
from ansible_plugin.executors.check import ADCMCheckPluginExecutor
from ansible_plugin.executors.config import ADCMConfigPluginExecutor
from ansible_plugin.executors.custom_log import ADCMCustomLogPluginExecutor
from ansible_plugin.executors.delete_service import ADCMDeleteServicePluginExecutor
from ansible_plugin.executors.hostcomponent import ADCMHostComponentPluginExecutor
from ansible_plugin.executors.remove_host_from_cluster import ADCMRemoveHostFromClusterPluginExecutor
from cm.impl.job.repo import JobRepo
from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from cm.legacy.services.job.run import create_related_configs
from cm.legacy.services.transition.dump import dump
from cm.legacy.services.transition.load import load
from cm.models import (
    ADCM,
    Action,
    ActionHostGroup,
    Bundle,
    ConfigHostGroup,
    ObjectType,
    Process,
    Prototype,
    Upgrade,
)
from core.config import ConfigRepoI
from django.core.management import call_command
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from tests.cases.rbac.setup import A1_MAPPING, BUNDLES_DIR, RBACWriteSideSuite
from tests.dependencies import RBACScenariosOverride, get_default_overridden_providers
from tests.use_cases import prepare_bundle_file

CUSTOM_LOG_EXECUTOR: Final = ADCMCustomLogPluginExecutor[lambda _, path: str(path)]


class TestRBACWriteSide(RBACWriteSideSuite):
    # G1.01

    def test_g1_01_create_host_free(self) -> None:
        with self.act():
            response = (self.client.v2 / "hosts").post(
                data={"hostproviderId": self.provider_p1.pk, "name": "g1-01-free"}
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_01_create_host_in_cluster(self) -> None:
        with self.act():
            response = (self.client.v2 / "hosts").post(
                data={
                    "hostproviderId": self.provider_p1.pk,
                    "name": "g1-01-in-cluster",
                    "clusterId": self.cluster_a1.pk,
                }
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    # G1.02

    def test_g1_02_create_host_plugin(self) -> None:
        with self.act():
            self.run_plugin(executor_type=ADCMAddHostPluginExecutor, arguments={"fqdn": "g1-02"}, job=self.p1_job)

    # G1.03

    def test_g1_03_duplicate_host_free(self) -> None:
        with self.act():
            response = self.client.v2[self.hosts["h-free"], "duplicates"].post(data={"name": "h-free"})
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_03_duplicate_host_in_cluster(self) -> None:
        with self.act():
            response = self.client.v2[self.hosts["h-free"], "duplicates"].post(
                data={"name": "h-free", "clusterId": self.cluster_a1.pk}
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    # G1.04

    def test_g1_04_add_host_to_cluster_one(self) -> None:
        with self.act():
            response = self.client.v2[self.cluster_a1, "hosts"].post(data=[{"hostId": self.hosts["h-free"].pk}])
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_04_add_host_to_cluster_many(self) -> None:
        with self.act():
            response = self.client.v2[self.cluster_a1, "hosts"].post(
                data=[{"hostId": self.hosts["h-free"].pk}, {"hostId": self.hosts["h-free-p2"].pk}]
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_04_add_host_to_cluster_plugin(self) -> None:
        # `h-free` has a duplicate with the same fqdn, so host is passed by id
        with self.act():
            self.run_plugin(
                executor_type=ADCMAddHostToClusterPluginExecutor,
                arguments={"host_id": self.hosts["h-free"].pk},
                job=self.a1_job,
            )

    # G1.05

    def test_g1_05_remove_host_from_cluster(self) -> None:
        with self.act():
            response = self.client.v2[self.cluster_a1, "hosts", self.hosts["h-unmapped"]].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    def test_g1_05_remove_host_from_cluster_plugin(self) -> None:
        with self.act():
            self.run_plugin(
                executor_type=ADCMRemoveHostFromClusterPluginExecutor,
                arguments={"fqdn": "h-unmapped"},
                job=self.a1_job,
            )

    # G1.06

    def test_g1_06_add_service(self) -> None:
        prototype = Prototype.objects.get(
            bundle_id=self.cluster_a1.prototype.bundle_id, type=ObjectType.SERVICE, name="svc_spare"
        )

        with self.act():
            response = self.client.v2[self.cluster_a1, "services"].post(data=[{"prototypeId": prototype.pk}])
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_06_add_service_service_manage(self) -> None:
        with self.act():
            self.run_action_via_api(owner=self.cluster_a1, action_name="add_spare", payload={})

    # G1.07

    def test_g1_07_delete_service(self) -> None:
        with self.act():
            response = self.client.v2[self.service("A1", "svc_3")].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    def test_g1_07_delete_service_plugin(self) -> None:
        # `svc_1` is mapped and has tasks: re-apply goes with `keep_objects`
        with self.act():
            self.run_plugin(
                executor_type=ADCMDeleteServicePluginExecutor, arguments={"service": "svc_1"}, job=self.a1_job
            )

    # G1.08

    def test_g1_08_create_chg(self) -> None:
        with self.act():
            response = self.client.v2[self.cluster_a1, "config-groups"].post(data={"name": "chg-g1-08"})
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_08_delete_chg(self) -> None:
        config_host_group = ConfigHostGroup.objects.get(name="chg-cluster")

        with self.act():
            response = self.client.v2[config_host_group].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    def test_g1_08_add_chg_host(self) -> None:
        config_host_group = ConfigHostGroup.objects.get(name="chg-cluster")

        with self.act():
            response = self.client.v2[config_host_group, "hosts"].post(data={"hostId": self.hosts["h-multi"].pk})
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_08_remove_chg_host(self) -> None:
        config_host_group = ConfigHostGroup.objects.get(name="chg-cluster")

        with self.act():
            response = self.client.v2[config_host_group, "hosts", self.hosts["h-one"]].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    # G1.09

    def test_g1_09_mapping_add(self) -> None:
        mapping = self.mapping_payload(cluster="A1", entries=(*A1_MAPPING, ("h-unmapped", "svc_1", "comp_2")))

        with self.act():
            response = self.client.v2[self.cluster_a1, "mapping"].post(data=mapping)
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_09_mapping_remove(self) -> None:
        mapping = self.mapping_payload(cluster="A1", entries=(entry for entry in A1_MAPPING if entry[0] != "h-one"))

        with self.act():
            response = self.client.v2[self.cluster_a1, "mapping"].post(data=mapping)
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_09_mapping_move(self) -> None:
        mapping = self.mapping_payload(
            cluster="A1",
            entries=(
                *(entry for entry in A1_MAPPING if entry[0] != "h-one"),
                ("h-one", "svc_1", "comp_2"),
            ),
        )

        with self.act():
            response = self.client.v2[self.cluster_a1, "mapping"].post(data=mapping)
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_09_mapping_plugin(self) -> None:
        with self.act():
            self.run_plugin(
                executor_type=ADCMHostComponentPluginExecutor,
                arguments={
                    "operations": [{"action": "add", "service": "svc_1", "component": "comp_2", "host": "h-unmapped"}]
                },
                job=self.a1_job,
            )

    def test_g1_09_mapping_hc_finalize(self) -> None:
        mapping = self.mapping_payload(cluster="A1", entries=(*A1_MAPPING, ("h-unmapped", "svc_1", "comp_2")))

        with self.act():
            self.run_action_via_api(
                owner=self.cluster_a1, action_name="hc_finalize", payload={"hostComponentMap": mapping}
            )

    def test_g1_09_mapping_hc_apply(self) -> None:
        mapping = self.mapping_payload(cluster="A1", entries=(*A1_MAPPING, ("h-unmapped", "svc_1", "comp_2")))

        with self.act():
            self.run_action_via_api(
                owner=self.cluster_a1, action_name="hc_apply", payload={"hostComponentMap": mapping}
            )

    # G1.10

    def test_g1_10_upgrade_cluster(self) -> None:
        upgrade = Upgrade.objects.get(bundle__name="rbac_cluster_a", bundle__version="2.0", name="plain")

        with self.act():
            response = self.client.v2[self.cluster_a1, "upgrades", upgrade, "run"].post()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    def test_g1_10_upgrade_provider(self) -> None:
        upgrade = Upgrade.objects.get(bundle__name="rbac_provider", bundle__version="2.0", name="plain")

        with self.act():
            response = self.client.v2[self.provider_p1, "upgrades", upgrade, "run"].post()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    # G1.11

    def test_g1_11_upgrade_switch(self) -> None:
        upgrade = Upgrade.objects.get(bundle__name="rbac_cluster_a", bundle__version="2.0", name="switch")

        with self.act():
            self.run_upgrade_via_api(owner=self.cluster_a1, upgrade=upgrade)

    def test_g1_11_upgrade_revert(self) -> None:
        upgrade = Upgrade.objects.get(bundle__name="rbac_cluster_a", bundle__version="2.0", name="plain")

        with self.act():
            self.run_upgrade_via_api(owner=self.cluster_a1, upgrade=upgrade)
            self.cluster_a1.refresh_from_db(fields=["prototype"])
            self.run_action_via_api(owner=self.cluster_a1, action_name="revert_upgrade", payload={})

    # G1.12

    def test_g1_12_config_cluster(self) -> None:
        with self.act():
            response = self.client.v2[self.cluster_a1, "configs"].post(
                data={"config": {"value": "g1-12"}, "adcmMeta": {}, "description": "g1-12"}
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_12_config_host(self) -> None:
        with self.act():
            response = self.client.v2[self.hosts["h-one"], "configs"].post(
                data={"config": {"value": "g1-12"}, "adcmMeta": {}, "description": "g1-12"}
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_12_config_chg(self) -> None:
        config_host_group = ConfigHostGroup.objects.get(name="chg-cluster")

        with self.act():
            response = self.client.v2[config_host_group, "configs"].post(
                data={
                    "config": {"value": "g1-12"},
                    "adcmMeta": {"/value": {"isSynchronized": False}},
                    "description": "g1-12",
                }
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_12_config_plugin(self) -> None:
        task = JobRepo().get_task(id=self.a1_job.task_id)  # pyright: ignore[reportAttributeAccessIssue]

        with self.act():
            create_related_configs(job_id=self.a1_job.pk, owner=task.owner, config_repo=self.container.get(ConfigRepoI))
            self.run_plugin(
                executor_type=ADCMConfigPluginExecutor,
                arguments={"type": "cluster", "key": "value", "value": "g1-12"},
                job=self.a1_job,
            )

    def test_g1_12_config_lookup(self) -> None:
        task = JobRepo().get_task(id=self.a1_job.task_id)  # pyright: ignore[reportAttributeAccessIssue]
        variables = {"job": {"id": self.a1_job.pk, "action": "common"}, "cluster": {"id": self.cluster_a1.pk}}

        with self.act():
            create_related_configs(job_id=self.a1_job.pk, owner=task.owner, config_repo=self.container.get(ConfigRepoI))
            result = call_adcm_config_lookup(terms=["cluster", "value", "g1-12"], variables=variables, kwargs={})
            self.assertEqual(result, PluginResult("g1-12", True))

    # G1.13

    def test_g1_13_launch_cluster(self) -> None:
        action = Action.objects.get(prototype=self.cluster_a1.prototype, name="common")

        with self.act():
            response = self.client.v2[self.cluster_a1, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_13_launch_service(self) -> None:
        service = self.service("A1", "svc_1")
        action = Action.objects.get(prototype=service.prototype, name="common")

        with self.act():
            response = self.client.v2[service, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_13_launch_component(self) -> None:
        component = self.component("A1", "svc_1", "comp_1")
        action = Action.objects.get(prototype=component.prototype, name="common")

        with self.act():
            response = self.client.v2[component, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_13_launch_provider(self) -> None:
        action = Action.objects.get(prototype=self.provider_p1.prototype, name="common")

        with self.act():
            response = self.client.v2[self.provider_p1, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_13_launch_host(self) -> None:
        host = self.hosts["h-one"]
        action = Action.objects.get(prototype=host.prototype, name="common")

        with self.act():
            response = self.client.v2[host, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    # G1.14

    def test_g1_14_host_action_cluster(self) -> None:
        action = Action.objects.get(prototype=self.cluster_a1.prototype, name="on_host")

        with self.act():
            response = self.client.v2[self.hosts["h-one"], "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_14_host_action_service(self) -> None:
        action = Action.objects.get(prototype=self.service("A1", "svc_1").prototype, name="on_host")

        with self.act():
            response = self.client.v2[self.hosts["h-one"], "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_14_host_action_component(self) -> None:
        action = Action.objects.get(prototype=self.component("A1", "svc_1", "comp_1").prototype, name="on_host")

        with self.act():
            response = self.client.v2[self.hosts["h-one"], "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_14_ahg_cluster(self) -> None:
        group = ActionHostGroup.objects.get(name="ahg-cluster")
        action = Action.objects.get(prototype=self.cluster_a1.prototype, name="in_ahg")

        with self.act():
            response = self.client.v2[group, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_14_ahg_service(self) -> None:
        group = ActionHostGroup.objects.get(name="ahg-service")
        action = Action.objects.get(prototype=self.service("A1", "svc_1").prototype, name="in_ahg")

        with self.act():
            response = self.client.v2[group, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_14_ahg_component(self) -> None:
        group = ActionHostGroup.objects.get(name="ahg-component")
        action = Action.objects.get(prototype=self.component("A1", "svc_1", "comp_1").prototype, name="in_ahg")

        with self.act():
            response = self.client.v2[group, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    def test_g1_14_adcm_action(self) -> None:
        # C9: ADCM-owned task gets no E4 grant
        adcm = ADCM.objects.get()
        action = Action.objects.get(prototype=adcm.prototype, name="test_ldap_connection")

        with self.act():
            response = self.client.v2[adcm, "actions", action, "run"].post(data={})
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    # G1.15

    def test_g1_15_wizard(self) -> None:
        action = Action.objects.get(prototype=self.cluster_w1.prototype, name="wizard")

        with self.act():
            response = self.client.v2[self.cluster_w1, "actions", action, "processes"].post(data={})
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)
            process = Process.objects.get(id=response.json()["id"])

            response = self.client.v2[self.cluster_w1, "actions", action, "processes", process, "operation"].post(
                data={
                    "method": ProcessOperationType.SUBMIT,
                    "params": {"processSyncKey": process.sync_key, "stepId": process.current_step.pk},
                }
            )
            self.assertEqual(response.status_code, HTTP_200_OK, response.content)

    # G1.16

    def test_g1_16_custom_log(self) -> None:
        with self.act():
            self.run_plugin(
                executor_type=CUSTOM_LOG_EXECUTOR,
                arguments={"name": "g1-16", "format": "txt", "content": "g1-16"},
                job=self.a1_job,
            )

    def test_g1_16_check_log_first(self) -> None:
        with self.act():
            self.run_plugin(
                executor_type=ADCMCheckPluginExecutor,
                arguments={"title": "g1-16", "result": True, "success_msg": "ok", "fail_msg": "fail"},
                job=self.p1_job,
            )

    def test_g1_16_check_log_next(self) -> None:
        # `a1_job` already has a check log
        with self.act():
            self.run_plugin(
                executor_type=ADCMCheckPluginExecutor,
                arguments={"title": "g1-16", "result": True, "success_msg": "ok", "fail_msg": "fail"},
                job=self.a1_job,
            )

    # G1.17

    def test_g1_17_upload_bundle(self) -> None:
        archive = prepare_bundle_file(source_dir=BUNDLES_DIR / "cluster_f", target_dir=self.directories.temp)

        with self.act(), archive.open("rb") as bundle_file:
            response = (self.client.v2 / "bundles").post(data={"file": bundle_file}, format_="multipart")
            self.assertEqual(response.status_code, HTTP_201_CREATED, response.content)

    def test_g1_17_delete_bundle(self) -> None:
        bundle = Bundle.objects.get(name="rbac_cluster_a", version="2.0")

        with self.act():
            response = self.client.v2[bundle].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    # G1.18

    def test_g1_18_delete_cluster(self) -> None:
        with self.act():
            response = self.client.v2[self.cluster_a2].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    def test_g1_18_delete_provider(self) -> None:
        with self.act():
            response = self.client.v2[self.provider_p3].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    def test_g1_18_delete_host(self) -> None:
        with self.act():
            response = self.client.v2[self.hosts["h-free"]].delete()
            self.assertEqual(response.status_code, HTTP_204_NO_CONTENT, response.content)

    # G1.19

    def test_g1_19_logrotate(self) -> None:
        # every finished setup task is older than the default threshold (365 days)
        later = timezone.now() + timedelta(days=366)

        with self.act(), patch("django.utils.timezone.now", return_value=later):
            call_command("logrotate", "--target=all")

    # G1.20

    def test_g1_20_import_cluster(self) -> None:
        payload = dump(cluster_id=self.cluster_a1.pk)

        payload.cluster.name = "A1-imported"
        for host in payload.hosts:
            host.name = f"imp-{host.name}"
        for entry in payload.cluster.mapping:
            entry.host = f"imp-{entry.host}"
        host_groups = [*payload.cluster.config_host_groups, *payload.cluster.action_host_groups]
        for service in payload.cluster.services.values():
            host_groups.extend((*service.config_host_groups, *service.action_host_groups))
            for component in service.components.values():
                host_groups.extend((*component.config_host_groups, *component.action_host_groups))
        for group in host_groups:
            group.hosts = [f"imp-{host}" for host in group.hosts]

        # `load` builds its own container: it has to be the suite's "with-rbac" one
        with_rbac_providers = [
            provider
            for provider in get_default_overridden_providers()
            if not isinstance(provider, RBACScenariosOverride)
        ]

        # `load` crashes on `develop`: `create_host` builds `StatusScenarios()` without `cluster_service`,
        # and behind it `create_cluster` calls `set_host_component_mapping` without `cluster_service`.
        # Once `load` is fixed, this assertion goes and the call moves into `self.act()` with a golden.
        with (
            patch("cm.legacy.services.transition.load.get_main_providers", return_value=with_rbac_providers),
            self.assertRaisesRegex(TypeError, "cluster_service"),
        ):
            load(data=payload, report=lambda _: None)
