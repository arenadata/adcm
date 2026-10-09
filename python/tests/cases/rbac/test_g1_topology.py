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

"""G1: non-RBAC triggers of the RBAC write side: topology, object lifecycle, upgrade, bundles, import"""

from unittest.mock import patch

from ansible_plugin.executors.add_host import ADCMAddHostPluginExecutor
from ansible_plugin.executors.add_host_to_cluster import ADCMAddHostToClusterPluginExecutor
from ansible_plugin.executors.delete_service import ADCMDeleteServicePluginExecutor
from ansible_plugin.executors.hostcomponent import ADCMHostComponentPluginExecutor
from ansible_plugin.executors.remove_host_from_cluster import ADCMRemoveHostFromClusterPluginExecutor
from cm.legacy.services.transition.dump import dump
from cm.legacy.services.transition.load import load
from cm.models import Bundle, ConfigHostGroup, ObjectType, Prototype, Upgrade
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from tests.cases.rbac.setup import A1_MAPPING, BUNDLES_DIR, RBACWriteSideSuite
from tests.dependencies import RBACScenariosOverride, get_default_overridden_providers
from tests.use_cases import prepare_bundle_file


class TestG1Topology(RBACWriteSideSuite):
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
