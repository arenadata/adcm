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

from cm.models import (
    Component,
    ConfigLog,
    Host,
    MaintenanceMode,
    ObjectType,
    Prototype,
    TaskLog,
    Upgrade,
)
from core.types import TaskID
from parameterized import parameterized
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from tests.suites import ADCMDjangoAPISuite

from api_v2.prototype.utils import accept_license

ANSIBLE_VAULT_HEADER = "$ANSIBLE_VAULT;1.1;AES256"


class TestUpgrade(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.service_1, *_ = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster_1)

        cluster_bundle_1_upgrade_path = cls.test_bundles_dir / "cluster_one_upgrade"
        cluster_bundle_1_upgrade_other_constraints_path = cls.test_bundles_dir / "cluster_one_upgrade_other_constraints"
        provider_bundle_upgrade_path = cls.test_bundles_dir / "provider_upgrade"
        cluster_bundle_upgrade = cls.uc.upload_bundle(src=cluster_bundle_1_upgrade_path)
        cluster_bundle_upgrade_2 = cls.uc.upload_bundle(src=cluster_bundle_1_upgrade_other_constraints_path)
        provider_bundle_upgrade = cls.uc.upload_bundle(src=provider_bundle_upgrade_path)
        cls.uc.upload_bundle(src=cls.test_bundles_dir / "cluster_two_upgrade_from_any")

        cls.cluster_upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=cluster_bundle_upgrade,
        )
        cls.cluster_upgrade_2 = Upgrade.objects.get(
            name="upgrade",
            bundle=cluster_bundle_upgrade_2,
        )
        cls.provider_upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=provider_bundle_upgrade,
        )
        cls.upgrade_cluster_via_action_simple = Upgrade.objects.get(
            name="upgrade_via_action_simple", bundle=cluster_bundle_upgrade
        )
        cls.upgrade_host_via_action_simple = Upgrade.objects.get(
            name="upgrade_via_action_simple", bundle=provider_bundle_upgrade
        )
        cls.upgrade_cluster_via_action_complex = Upgrade.objects.get(
            name="upgrade_via_action_complex", bundle=cluster_bundle_upgrade
        )
        cls.upgrade_host_via_action_complex = Upgrade.objects.get(
            name="upgrade_via_action_complex", bundle=provider_bundle_upgrade
        )

        cls.user = cls.uc.create_user()

    def setUp(self) -> None:
        super().setUp()

        self.unauthorized_client = self.client_class()
        self.unauthorized_client.login(username="test_user_username", password="test_user_password")

    def accept_license_of_first_service(self):
        accept_license(
            prototype=Prototype.objects.filter(
                bundle=self.upgrade_cluster_via_action_simple.bundle,
                type=ObjectType.SERVICE,
                name="service_1",
                version=self.upgrade_cluster_via_action_simple.bundle.version,
            ).get()
        )

    def assert_task_status_is(self, task_id: TaskID, status: str):
        task_status = TaskLog.objects.values_list("status", flat=True).get(id=task_id)
        self.assertEqual(task_status, status)

    def test_cluster_list_upgrades_success(self):
        response = self.client.v2[self.cluster_1, "upgrades"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 7)

        for upgrade in response.json():
            self.assertIn("bundle", upgrade)
            self.assertIn("description", upgrade)

    def test_upgrade_visibility_from_edition_any_success(self):
        response = self.client.v2[self.cluster_2, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

        response_upgrades = [upgrade["name"] for upgrade in response.json()]
        self.assertListEqual(response_upgrades, ["Upgrade 99.0"])

    def test_cluster_upgrade_retrieve_success(self):
        response = self.client.v2[self.cluster_1, "upgrades", self.cluster_upgrade].get()
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
                    "description",
                }
            )
        )

        self.assertEqual(upgrade_data["id"], self.cluster_upgrade.pk)
        self.assertEqual(len(upgrade_data["hostComponentMapRules"]), 0)
        self.assertIsNone(upgrade_data["configuration"])
        self.assertEqual(upgrade_data["disclaimer"], "")
        self.assertFalse(upgrade_data["isAllowToTerminate"])
        self.assertEqual(upgrade_data["description"], "This is upgrade!")

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

    def test_cluster_upgrade_run_success(self):
        self.accept_license_of_first_service()

        response = self.client.v2[self.cluster_1, "upgrades", self.upgrade_cluster_via_action_simple, "run"].post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))

        launched_task = self.task_runner.expect_task_launched(task_id=data["id"])

        self.task_runner.run_task(launched_task.id)
        self.assert_task_status_is(task_id=launched_task.id, status="success")
        self.cluster_1.refresh_from_db()
        self.assertEqual(
            self.cluster_1.prototype.version, self.upgrade_cluster_via_action_simple.action.prototype.version
        )

    def test_provider_list_upgrades_success(self):
        response = self.client.v2[self.provider, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)

        for upgrade in response.json():
            self.assertIn("bundle", upgrade)

    def test_provider_upgrade_retrieve_success(self):
        response = self.client.v2[self.provider, "upgrades", self.provider_upgrade].get()
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
        response = self.client.v2[self.provider, "upgrades", self.upgrade_host_via_action_complex].get()
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
        response = self.client.v2[self.provider, "upgrades", self.upgrade_host_via_action_simple, "run"].post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        launched_task = self.task_runner.expect_task_launched(data["id"])

        self.task_runner.run_task(launched_task.id)
        self.assert_task_status_is(launched_task.id, "success")
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.prototype.version, self.upgrade_host_via_action_simple.action.prototype.version)

    def test_provider_upgrade_run_violate_constraint_fail(self):
        response = self.client.v2[self.provider, "upgrades", self.cluster_upgrade, "run"].post()
        expected_response = {
            "code": "UPGRADE_NOT_FOUND",
            "desc": "upgrade is not found",
            "level": "error",
        }

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertDictEqual(response.json(), expected_response)

    def test_cluster_upgrade_run_violate_constraint_fail(self):
        response = self.client.v2[self.cluster_1, "upgrades", self.provider_upgrade, "run"].post()
        expected_response = {
            "code": "UPGRADE_NOT_FOUND",
            "desc": "upgrade is not found",
            "level": "error",
        }

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.assertDictEqual(response.json(), expected_response)

    def test_provider_upgrade_run_not_found_fail(self):
        response = self.client.v2[self.provider, "upgrades", self.get_non_existent_pk(Upgrade), "run"].post()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_run_not_found_fail(self):
        response = self.client.v2[self.cluster_1, "upgrades", self.get_non_existent_pk(Upgrade), "run"].post()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_retrieve_not_found_fail(self):
        response = self.client.v2[self.cluster_1, "upgrades", self.get_non_existent_pk(Upgrade)].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_provider_upgrade_retrieve_not_found_fail(self):
        response = self.client.v2[self.provider, "upgrades", self.get_non_existent_pk(Upgrade)].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_list_unauthorized_fail(self) -> None:
        response = self.unauthorized_client.v2[self.cluster_1, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_retrieve_unauthorized_fail(self):
        response = self.unauthorized_client.v2[self.cluster_1, "upgrades", self.cluster_upgrade].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_provider_list_unauthorized_fail(self) -> None:
        response = self.unauthorized_client.v2[self.provider, "upgrades"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_provider_retrieve_unauthorized_fail(self):
        response = self.unauthorized_client.v2[self.provider, "upgrades", self.provider_upgrade].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_adcm_4703_retrieve_upgrade_with_variant_without_cluster_config_500(self) -> None:
        old_bundle = self.uc.upload_bundle(
            self.test_bundles_dir / "various_upgrades" / "no_config_upgrade_with_variant_old"
        )
        new_bundle = self.uc.upload_bundle(
            self.test_bundles_dir / "various_upgrades" / "no_config_upgrade_with_variant_new"
        )

        upgrade = Upgrade.objects.get(bundle=new_bundle, name="upgrade_via_action_complex")

        cluster = self.uc.add_cluster(bundle=old_bundle, name="Cluster For Upgrade")
        self.assertIsNone(cluster.config)

        self.uc.add_host_to_cluster(cluster=cluster, host=self.uc.add_host(provider=self.provider, fqdn="first_host"))
        self.uc.add_host_to_cluster(cluster=cluster, host=self.uc.add_host(provider=self.provider, fqdn="second_host"))

        response = self.client.v2[cluster, "upgrades", upgrade].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        schema = response.json()["configuration"]["configSchema"]
        self.assertEqual(schema["properties"]["pick_host"]["oneOf"][0]["enum"], ["first_host", "second_host"])
        self.assertEqual(schema["properties"]["pick_host"]["oneOf"][1], {"type": "null"})
        self.assertEqual(
            schema["properties"]["grouped"]["properties"]["pick_host"]["oneOf"][0]["enum"],
            ["first_host", "second_host"],
        )
        self.assertEqual(schema["properties"]["grouped"]["properties"]["pick_host"]["oneOf"][1], {"type": "null"})

    def test_start_impossible_reason(self):
        host_1 = self.uc.add_host(provider=self.provider, fqdn="first_host", cluster=self.cluster_1)
        host_2 = self.uc.add_host(provider=self.provider, fqdn="second_host", cluster=self.cluster_1)
        component_2 = Component.objects.get(service=self.service_1, prototype__name="component_2")
        self.uc.set_hostcomponent(cluster=self.cluster_1, entries=((host_1, component_2), (host_2, component_2)))

        # list
        mm_response = self.client.v2[self.cluster_1, "hosts", host_1, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON}
        )
        self.assertEqual(mm_response.status_code, HTTP_200_OK)

        response = self.client.v2[self.cluster_1, "upgrades"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertSetEqual(
            {r["startImpossibleReason"] for r in response.json()},
            {'The Upgrade is not available. One or more hosts in "Maintenance mode"'},
        )

        mm_response = self.client.v2[self.cluster_1, "hosts", host_1, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.OFF}
        )
        self.assertEqual(mm_response.status_code, HTTP_200_OK)

        response = self.client.v2[self.cluster_1, "upgrades"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertSetEqual({r["startImpossibleReason"] for r in response.json()}, {None})

        # retrieve
        mm_response = self.client.v2[component_2, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON}
        )
        self.assertEqual(mm_response.status_code, HTTP_200_OK)

        response = self.client.v2[self.cluster_1, "upgrades", self.cluster_upgrade].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(
            response.json()["startImpossibleReason"],
            'The Upgrade is not available. One or more components in "Maintenance mode"',
        )

        mm_response = self.client.v2[component_2, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.OFF}
        )
        self.assertEqual(mm_response.status_code, HTTP_200_OK)

        response = self.client.v2[self.cluster_1, "upgrades", self.cluster_upgrade].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["startImpossibleReason"], None)

        # run
        mm_response = self.client.v2[self.service_1, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.ON}
        )
        self.assertEqual(mm_response.status_code, HTTP_200_OK)

        expected_response = {
            "code": "UPGRADE_ERROR",
            "desc": 'The Upgrade is not available. One or more services in "Maintenance mode"',
            "level": "error",
        }
        response = self.client.v2[self.cluster_1, "upgrades", self.upgrade_cluster_via_action_simple, "run"].post()
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

        mm_response = self.client.v2[self.service_1, "maintenance-mode"].post(
            data={"maintenance_mode": MaintenanceMode.OFF}
        )
        self.assertEqual(mm_response.status_code, HTTP_200_OK)

        response = self.client.v2[self.cluster_1, "upgrades", self.upgrade_cluster_via_action_simple, "run"].post()
        self.assertEqual(response.status_code, HTTP_200_OK)

        # list provider upgrades
        response = self.client.v2[self.provider, "upgrades"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertSetEqual({r["startImpossibleReason"] for r in response.json()}, {None})

        host = Host.objects.filter(provider=self.provider).first()
        mm_response = self.client.v2[host, "maintenance-mode"].post(data={"maintenance_mode": MaintenanceMode.ON})
        self.assertEqual(mm_response.status_code, HTTP_200_OK)

        response = self.client.v2[self.provider, "upgrades"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertSetEqual(
            {r["startImpossibleReason"] for r in response.json()},
            {'The Upgrade is not available. One or more hosts in "Maintenance mode"'},
        )

    def test_list_upgrades_permission_success(self):
        permission_cases = (
            (self.cluster_1, self.cluster_1, "Upgrade cluster bundle", 7),
            (self.cluster_1, [], "ADCM User", 7),
            (self.provider, [], "ADCM User", 3),
            (self.provider, self.provider, "Upgrade provider bundle", 3),
        )

        for api_object, role_object, role, upgrades_count in permission_cases:
            with self.subTest(msg=f"list upgrades on {role_object} with role {role}"):
                with self.grant_permissions(to=self.user, on=role_object, role_name=role):
                    response = self.unauthorized_client.v2[api_object, "upgrades"].get()
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(len(response.json()), upgrades_count)

    def test_upgrade_adcm_3899_success(self):
        accept_license(
            prototype=Prototype.objects.filter(
                bundle=self.upgrade_cluster_via_action_simple.bundle,
                type=ObjectType.SERVICE,
                name="service_1",
                version=self.upgrade_cluster_via_action_simple.bundle.version,
            ).first()
        )
        self.client.login(username="test_user_username", password="test_user_password")
        with self.grant_permissions(to=self.user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = self.client.v2[self.cluster_1, "upgrades", self.upgrade_cluster_via_action_simple, "run"].post()
            self.assertEqual(response.status_code, HTTP_200_OK)

            task_id = self.task_runner.expect_task_launched().id
            self.task_runner.run_task(task_id)
            self.assert_task_status_is(task_id, "success")

            response = (self.client.v2 / "jobs").get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()), 4)

        response = (self.client.v2 / "jobs").get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 4)

    @parameterized.expand(
        input=[
            ("incorrect value", "incorrect value"),
            ("Empty value", ""),
        ]
    )
    def test_upgrade_retrieve_complex_invalid_config_variant_value_fail(self, _, config_type_strict):
        checked_configuration = "variant_config_type_strict"
        response = self.client.v2[self.cluster_1, "upgrades", self.upgrade_cluster_via_action_complex, "run"].post(
            data={
                "configuration": {
                    "config": {
                        "simple": "val",
                        "file": "content",
                        "grouped": {
                            "simple": 5,
                            "second": 4.3,
                            "structure": {
                                "nested": {"attr": "foo", "op": "bar", "tech": "false"},
                                "quantity": 122,
                            },
                        },
                        "after": ["x", "y"],
                        checked_configuration: config_type_strict,
                    },
                    "adcmMeta": {},
                },
            },
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.task_runner.expect_task_not_launched()
        data = response.json()
        self.assertEqual(data["code"], "UPGRADE_OPERATION_ERROR")
        self.assertIn(f"/{checked_configuration}", data["desc"])
        self.assertIn("not in variant list", data["desc"])

    def test_adcm_7535_encrypt_secrets_from_new_defaults(self):
        old_bundle = self.uc.upload_bundle(self.test_bundles_dir / "adcm_7535_old")
        new_bundle = self.uc.upload_bundle(self.test_bundles_dir / "adcm_7535_new")
        cluster = self.uc.add_cluster(bundle=old_bundle, name="nice")
        upgrade = Upgrade.objects.get(bundle_id=new_bundle.pk)

        response = self.client.v2[cluster, "upgrades", upgrade, "run"].post(data={})
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        cluster.refresh_from_db()
        config = ConfigLog.objects.get(id=cluster.config.current)
        self.assertTrue(config.config["new"].startswith(ANSIBLE_VAULT_HEADER))
        self.assertTrue(config.config["exists"].startswith(ANSIBLE_VAULT_HEADER))

    def test_adcm_7676_create_config_host_group_without_config_correct_error(self):
        self.accept_license_of_first_service()

        service, *_ = self.uc.add_services_to_cluster(["service_with_miss_config_service"], cluster=self.cluster_1)
        response = self.client.v2[self.cluster_1, "upgrades", self.cluster_upgrade, "run"].post()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        component = Component.objects.get(service=service, prototype__name="will_miss_config")

        # have to give name, because absence of config will be known after serialization
        response = self.client.v2[component, "config-groups"].post(data={"name": "yoo"})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "GROUP_CONFIG_NO_CONFIG_ERROR")

    def test_apply_config_in_script(self):
        cluster = self.cluster_1
        self.accept_license_of_first_service()
        service = self.uc.add_services_to_cluster(["adcm_7807"], cluster=cluster)[0]
        upgrade = Upgrade.objects.get(name="with_scripts_adcm_7807")

        # upgrade
        response = self.client.v2[cluster, "upgrades", upgrade, "run"].post()
        self.assertEqual(response.status_code, HTTP_200_OK)
        # run upgrade action
        launched_task = self.task_runner.expect_task_launched()
        self.task_runner.run_task(launched_task.id)

        task_status = TaskLog.objects.values_list("status", flat=True).get(id=launched_task.id)
        self.assertEqual(task_status, "success")
        # config migrated
        config = ConfigLog.objects.get(id=service.config.current)
        expected_config = {"pick_me": {"b": {"b1": 100}}, "with_default": {"a": {"a1": "wow"}}}
        self.assertEqual(config.config, expected_config)
