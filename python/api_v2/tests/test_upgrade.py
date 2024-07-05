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

from pathlib import Path

from cm.models import (
    ADCM,
    ConfigLog,
    HostComponent,
    ObjectType,
    Prototype,
    ServiceComponent,
    Upgrade,
)
from cm.tests.mocks.task_runner import RunTaskMock
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.test import APITestCase

from api_v2.tests.base import BaseAPITestCase


class TestUpgrade(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()

        cluster_bundle_1_upgrade_path = self.test_bundles_dir / "cluster_one_upgrade"
        cluster_bundle_1_upgrade_other_constraints_path = (
            self.test_bundles_dir / "cluster_one_upgrade_other_constraints"
        )
        provider_bundle_upgrade_path = self.test_bundles_dir / "provider_upgrade"
        cluster_bundle_upgrade = self.add_bundle(source_dir=cluster_bundle_1_upgrade_path)
        cluster_bundle_upgrade_2 = self.add_bundle(source_dir=cluster_bundle_1_upgrade_other_constraints_path)
        provider_bundle_upgrade = self.add_bundle(source_dir=provider_bundle_upgrade_path)
        self.add_bundle(source_dir=self.test_bundles_dir / "cluster_two_upgrade_from_any")

        self.cluster_upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=cluster_bundle_upgrade,
        )
        self.cluster_upgrade_2 = Upgrade.objects.get(
            name="upgrade",
            bundle=cluster_bundle_upgrade_2,
        )
        self.provider_upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=provider_bundle_upgrade,
        )
        self.upgrade_cluster_via_action_simple = Upgrade.objects.get(
            name="upgrade_via_action_simple", bundle=cluster_bundle_upgrade
        )
        self.upgrade_host_via_action_simple = Upgrade.objects.get(
            name="upgrade_via_action_simple", bundle=provider_bundle_upgrade
        )
        self.upgrade_cluster_via_action_complex = Upgrade.objects.get(
            name="upgrade_via_action_complex", bundle=cluster_bundle_upgrade
        )
        self.upgrade_host_via_action_complex = Upgrade.objects.get(
            name="upgrade_via_action_complex", bundle=provider_bundle_upgrade
        )

        self.user = self.create_user()
        self.unauthorized_client = self.client_class()
        self.unauthorized_client.login(username="test_user_username", password="test_user_password")

    def test_cluster_list_upgrades_success(self):
        response: Response = self.client.v2[self.cluster_1, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 6)

    def test_upgrade_visibility_from_edition_any_success(self):
        response: Response = self.client.v2[self.cluster_2, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

        response_upgrades = [upgrade["name"] for upgrade in response.json()]
        self.assertListEqual(response_upgrades, ["Upgrade 99.0"])

    def test_cluster_upgrade_retrieve_success(self):
        response: Response = self.client.v2[self.cluster_1, "upgrades", self.cluster_upgrade].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {
                    "id",
                    "name",
                    "displayName",
                    "hostComponentMapRules",
                    "configuration",
                    "isAllowToTerminate",
                    "disclaimer",
                    "bundle",
                }
            )
        )

        self.assertEqual(upgrade_data["id"], self.cluster_upgrade.pk)
        self.assertEqual(len(upgrade_data["hostComponentMapRules"]), 0)
        self.assertIsNone(upgrade_data["configuration"])
        self.assertEqual(upgrade_data["disclaimer"], "")
        self.assertFalse(upgrade_data["isAllowToTerminate"])
        service_prototype = Prototype.objects.get(
            bundle=self.cluster_upgrade.bundle, type=ObjectType.SERVICE, name=self.service_1.prototype.name
        )
        self.assertDictEqual(
            upgrade_data["bundle"],
            {
                "id": self.cluster_upgrade.bundle.pk,
                "prototypeId": self.cluster_upgrade.bundle.prototype_set.filter(type="cluster").first().pk,
                "licenseStatus": "accepted",
                "unacceptedServicesPrototypes": [
                    {
                        "id": service_prototype.pk,
                        "name": service_prototype.name,
                        "displayName": service_prototype.display_name,
                        "version": service_prototype.version,
                        "license": {
                            "status": "unaccepted",
                            "text": "License\n",
                        },
                    }
                ],
            },
        )

    def test_cluster_upgrade_retrieve_complex_success(self):
        response: Response = self.client.v2[self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {"id", "hostComponentMapRules", "configuration", "isAllowToTerminate", "disclaimer"}
            )
        )

        self.assertEqual(upgrade_data["id"], self.upgrade_cluster_via_action_complex.pk)
        self.assertEqual(upgrade_data["disclaimer"], "Cool upgrade")
        self.assertFalse(upgrade_data["isAllowToTerminate"])

        self.assertSetEqual(
            {
                (entry["action"], entry["service"], entry["component"])
                for entry in upgrade_data["hostComponentMapRules"]
            },
            {("add", "service_1", "component_1"), ("remove", "service_1", "component_2")},
        )

    def test_cluster_upgrade_run_success(self):
        Prototype.objects.update(license="accepted")

        with RunTaskMock() as run_task:
            response: Response = self.client.v2[
                self.cluster_1, "upgrades", self.upgrade_cluster_via_action_simple, "run"
            ].post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        self.assertEqual(data["id"], run_task.target_task.id)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.cluster_1.refresh_from_db()
        self.assertEqual(
            self.cluster_1.prototype.version, self.upgrade_cluster_via_action_simple.action.prototype.version
        )

    def test_cluster_upgrade_run_complex_success(self):
        Prototype.objects.update(license="accepted")

        host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="one_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host)
        component_1 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_1")
        component_2 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_2")
        HostComponent.objects.create(cluster=self.cluster_1, service=self.service_1, component=component_2, host=host)

        with RunTaskMock() as run_task:
            response: Response = self.client.v2[
                self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"
            ].post(
                data={
                    "hostComponentMap": [{"hostId": host.pk, "componentId": component_1.pk}],
                    "configuration": {
                        "config": {"simple": "val", "grouped": {"simple": 5, "second": 4.3}, "after": ["x", "y"]},
                        "adcmMeta": {},
                    },
                    "isVerbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        self.assertEqual(data["id"], run_task.target_task.id)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.cluster_1.refresh_from_db()
        self.assertEqual(
            self.cluster_1.prototype.version, self.upgrade_cluster_via_action_simple.action.prototype.version
        )

    def test_adcm_5246_cluster_upgrade_other_constraints_run_success(self):
        Prototype.objects.update(license="accepted")

        host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="first_host")
        host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="second_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host_1)
        self.add_host_to_cluster(cluster=self.cluster_1, host=host_2)
        component_1 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_1")
        component_2 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_2")
        HostComponent.objects.create(cluster=self.cluster_1, service=self.service_1, component=component_2, host=host_1)
        HostComponent.objects.create(cluster=self.cluster_1, service=self.service_1, component=component_1, host=host_1)
        HostComponent.objects.create(cluster=self.cluster_1, service=self.service_1, component=component_1, host=host_2)

        with RunTaskMock() as run_task:
            response: Response = self.client.v2[
                self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"
            ].post(
                data={
                    "hostComponentMap": [
                        {"hostId": host_1.pk, "componentId": component_1.pk},
                        {"hostId": host_2.pk, "componentId": component_1.pk},
                    ],
                    "configuration": {
                        "config": {"simple": "val", "grouped": {"simple": 5, "second": 4.3}, "after": ["x", "y"]},
                        "adcmMeta": {},
                    },
                    "isVerbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        self.assertEqual(data["id"], run_task.target_task.id)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.cluster_1.refresh_from_db()
        self.assertEqual(
            self.cluster_1.prototype.version, self.upgrade_cluster_via_action_simple.action.prototype.version
        )

    def test_adcm_4856_cluster_upgrade_run_complex_no_component_fail(self):
        host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="one_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host)

        with RunTaskMock() as run_task:
            response: Response = self.client.v2[
                self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"
            ].post(
                data={
                    "hostComponentMap": [{"hostId": host.pk, "componentId": 1000}],
                    "configuration": {
                        "config": {"simple": "val", "grouped": {"simple": 5, "second": 4.3}, "after": ["x", "y"]},
                        "adcmMeta": {},
                    },
                    "isVerbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertDictEqual(response.json(), {"detail": "Components with ids 1000 do not exist"})
        self.assertIsNone(run_task.target_task)

    def test_adcm_4856_cluster_upgrade_run_complex_no_host_fail(self):
        component_1 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_1")

        with RunTaskMock() as run_task:
            response: Response = self.client.v2[
                self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"
            ].post(
                data={
                    "hostComponentMap": [{"hostId": 1000, "componentId": component_1.pk}],
                    "configuration": {
                        "config": {},
                        "adcmMeta": {},
                    },
                    "isVerbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertDictEqual(response.json(), {"detail": "Hosts with ids 1000 do not exist"})
        self.assertIsNone(run_task.target_task)

    def test_adcm_4856_cluster_upgrade_run_complex_duplicated_hc_success(self):
        # fixme was incorrect test, probably should fix a validation? see action run
        Prototype.objects.update(license="accepted")

        host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="one_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host)

        component_1 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_1")

        with RunTaskMock() as run_task:
            response: Response = self.client.v2[
                self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"
            ].post(
                data={
                    "hostComponentMap": [
                        {"hostId": host.pk, "componentId": component_1.pk},
                        {"hostId": host.pk, "componentId": component_1.pk},
                    ],
                    "configuration": {
                        "config": {"simple": "val", "grouped": {"simple": 5, "second": 4.3}, "after": ["x", "y"]},
                        "adcmMeta": {},
                    },
                    "isVerbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.cluster_1.refresh_from_db()
        self.assertEqual(
            self.cluster_1.prototype.version, self.upgrade_cluster_via_action_simple.action.prototype.version
        )

    def test_adcm_4856_cluster_upgrade_run_complex_several_entries_hc_success(self):
        Prototype.objects.update(license="accepted")

        host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="one_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host_1)

        host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="second_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host_2)

        component_1 = ServiceComponent.objects.get(service=self.service_1, prototype__name="component_1")

        with RunTaskMock() as run_task:
            response: Response = self.client.v2[
                self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"
            ].post(
                data={
                    "hostComponentMap": [
                        {"hostId": host_1.pk, "componentId": component_1.pk},
                        {"hostId": host_2.pk, "componentId": component_1.pk},
                    ],
                    "configuration": {
                        "config": {"simple": "val", "grouped": {"simple": 5, "second": 4.3}, "after": ["x", "y"]},
                        "adcmMeta": {},
                    },
                    "isVerbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.cluster_1.refresh_from_db()
        self.assertEqual(
            self.cluster_1.prototype.version, self.upgrade_cluster_via_action_simple.action.prototype.version
        )

    def test_provider_list_upgrades_success(self):
        response: Response = self.client.v2[self.provider, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)

    def test_provider_upgrade_retrieve_success(self):
        response: Response = self.client.v2[self.provider, "upgrades", self.provider_upgrade].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {"id", "hostComponentMapRules", "configuration", "isAllowToTerminate", "disclaimer"}
            )
        )
        self.assertEqual(upgrade_data["id"], self.provider_upgrade.pk)
        self.assertEqual(len(upgrade_data["hostComponentMapRules"]), 0)
        self.assertIsNone(upgrade_data["configuration"])
        self.assertEqual(upgrade_data["disclaimer"], "")
        self.assertFalse(upgrade_data["isAllowToTerminate"])

    def test_provider_upgrade_retrieve_complex_success(self):
        response: Response = self.client.v2[self.provider, "upgrades", self.upgrade_host_via_action_complex].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {"id", "hostComponentMapRules", "configuration", "isAllowToTerminate", "disclaimer"}
            )
        )

        self.assertEqual(upgrade_data["id"], self.upgrade_host_via_action_complex.pk)
        self.assertEqual(upgrade_data["disclaimer"], "Cool upgrade")
        self.assertFalse(upgrade_data["isAllowToTerminate"])

        self.assertEqual(len(upgrade_data["hostComponentMapRules"]), 0)

    def test_provider_upgrade_run_success(self):
        with RunTaskMock() as run_task:
            response = self.client.v2[self.provider, "upgrades", self.upgrade_host_via_action_simple, "run"].post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        self.assertEqual(data["id"], run_task.target_task.id)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.prototype.version, self.upgrade_host_via_action_simple.action.prototype.version)

    def test_provider_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.v2[self.provider, "upgrades", self.cluster_upgrade, "run"].post()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.v2[self.cluster_1, "upgrades", self.provider_upgrade, "run"].post()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_provider_upgrade_run_not_found_fail(self):
        response = self.client.v2[self.provider, "upgrades", self.get_non_existent_pk(Upgrade), "run"].post()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_run_not_found_fail(self):
        response = self.client.v2[self.cluster_1, "upgrades", self.get_non_existent_pk(Upgrade), "run"].post()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_retrieve_not_found_fail(self):
        response: Response = self.client.v2[self.cluster_1, "upgrades", self.get_non_existent_pk(Upgrade)].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_hostprovider_upgrade_retrieve_not_found_fail(self):
        response: Response = self.client.v2[self.provider, "upgrades", self.get_non_existent_pk(Upgrade)].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_hostcomponent_validation_fail(self):
        endpoint = self.client.v2[self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"]
        for hc_data in ([{"hostId": 1}], [{"componentId": 4}], [{}]):
            with self.subTest(f"Pass host_component_map as {hc_data}"):
                response: Response = endpoint.post(data={"hostComponentMap": hc_data})

                self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_cluster_list_unauthorized_fail(self) -> None:
        response: Response = self.unauthorized_client.v2[self.cluster_1, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_retrieve_unauthorized_fail(self):
        response: Response = self.unauthorized_client.v2[self.cluster_1, "upgrades", self.cluster_upgrade].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_hostprovider_list_unauthorized_fail(self) -> None:
        response: Response = self.unauthorized_client.v2[self.provider, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_hostprovider_retrieve_unauthorized_fail(self):
        response: Response = self.unauthorized_client.v2[self.provider, "upgrades", self.provider_upgrade].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_adcm_4703_retrieve_upgrade_with_variant_without_cluster_config_500(self) -> None:
        old_bundle = self.add_bundle(self.test_bundles_dir / "various_upgrades" / "no_config_upgrade_with_variant_old")
        new_bundle = self.add_bundle(self.test_bundles_dir / "various_upgrades" / "no_config_upgrade_with_variant_new")

        upgrade = Upgrade.objects.get(bundle=new_bundle, name="upgrade_via_action_complex")

        cluster = self.add_cluster(bundle=old_bundle, name="Cluster For Upgrade")
        self.assertIsNone(cluster.config)

        self.add_host_to_cluster(
            cluster=cluster, host=self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="first_host")
        )
        self.add_host_to_cluster(
            cluster=cluster, host=self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="second_host")
        )

        response = self.client.v2[cluster, "upgrades", upgrade].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        schema = response.json()["configuration"]["configSchema"]
        self.assertEqual(schema["properties"]["pick_host"]["enum"], ["first_host", "second_host", None])
        self.assertEqual(
            schema["properties"]["grouped"]["properties"]["pick_host"]["enum"], ["first_host", "second_host", None]
        )

    def test_list_cluster_upgrades_success(self):
        response = self.client.v2[self.cluster_1, "upgrades"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 6)

    def test_list_upgrades_permission_success(self):
        permission_cases = (
            (self.cluster_1, self.cluster_1, "Upgrade cluster bundle", 6),
            (self.cluster_1, [], "ADCM User", 6),
            (self.provider, [], "ADCM User", 3),
            (self.provider, self.provider, "Upgrade provider bundle", 3),
        )

        for api_object, role_object, role, upgrades_count in permission_cases:
            with self.subTest(msg=f"list upgrades on {role_object} with role {role}"):
                with self.grant_permissions(to=self.user, on=role_object, role_name=role):
                    response = self.unauthorized_client.v2[api_object, "upgrades"].get()
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(len(response.json()), upgrades_count)


class TestAdcmUpgrade(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        init_roles()
        init(adcm_conf_file=Path(__file__).parent / "bundles" / "adcm_configs" / "config.yaml")

    def setUp(self) -> None:
        super().setUp()
        self.original_adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(pk=self.original_adcm.config.current)
        config_log.config["job_log"]["log_rotation_on_fs"] = 120
        config_log.config["job_log"]["log_rotation_in_db"] = 50
        config_log.config["config_rotation"]["config_rotation_in_db"] = 10
        config_log.save(update_fields=["config"])

    def test_adcm_2_6_upgrade_success(self):
        init()
        new_adcm = ADCM.objects.first()
        old_adcm_version = float(self.original_adcm.prototype.version)
        new_adcm_version = float(new_adcm.prototype.version)
        config_log = ConfigLog.objects.get(obj_ref=new_adcm.config, id=new_adcm.config.current)
        self.assertNotIn("job_log", config_log.config)
        self.assertNotIn("config_rotation", config_log.config)
        self.assertEqual(config_log.config["audit_data_retention"]["log_rotation_in_db"], 50)
        self.assertEqual(config_log.config["audit_data_retention"]["log_rotation_on_fs"], 120)
        self.assertEqual(config_log.config["audit_data_retention"]["config_rotation_in_db"], 10)
        self.assertGreater(new_adcm_version, old_adcm_version)
