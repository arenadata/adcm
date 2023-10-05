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
from unittest.mock import patch

from api_v2.tests.base import BaseAPITestCase
from cm.models import ADCM, ConfigLog, HostComponent, ServiceComponent, TaskLog, Upgrade
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.test import APIClient, APITestCase


class TestUpgrade(BaseAPITestCase):  # pylint:disable=too-many-public-methods
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle_1_upgrade_path = self.test_bundles_dir / "cluster_one_upgrade"
        provider_bundle_upgrade_path = self.test_bundles_dir / "provider_upgrade"
        cluster_bundle_upgrade = self.add_bundle(source_dir=cluster_bundle_1_upgrade_path)
        provider_bundle_upgrade = self.add_bundle(source_dir=provider_bundle_upgrade_path)

        self.cluster_upgrade = Upgrade.objects.get(
            name="upgrade",
            bundle=cluster_bundle_upgrade,
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

        self.create_user()
        self.unauthorized_client = APIClient()
        self.unauthorized_client.login(username="test_user_username", password="test_user_password")

    def test_cluster_list_upgrades_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)

    def test_cluster_upgrade_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {"id", "hostComponentMapRules", "configSchema", "isAllowToTerminate", "disclaimer"}
            )
        )

        self.assertEqual(upgrade_data["id"], self.cluster_upgrade.pk)
        self.assertEqual(len(upgrade_data["hostComponentMapRules"]), 0)
        self.assertEqual(upgrade_data["configSchema"], None)
        self.assertEqual(upgrade_data["disclaimer"], "")
        self.assertFalse(upgrade_data["isAllowToTerminate"])

    def test_cluster_upgrade_retrieve_complex_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade_cluster_via_action_complex.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {"id", "hostComponentMapRules", "configSchema", "isAllowToTerminate", "disclaimer"}
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
        tasklog = TaskLog.objects.create(
            object_id=self.cluster_1.pk,
            object_type=ContentType.objects.get(app_label="cm", model="cluster"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.upgrade_cluster_via_action_simple.action,
        )

        with patch("cm.upgrade.start_task", return_value=tasklog):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:upgrade-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade_cluster_via_action_simple.pk},
                ),
                data={
                    "host_component_map": [],
                    "config": {},
                    "is_verbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        self.assertEqual(data["id"], tasklog.id)

    def test_cluster_upgrade_run_complex_success(self):
        tasklog = TaskLog.objects.create(
            object_id=self.cluster_1.pk,
            object_type=ContentType.objects.get(app_label="cm", model="cluster"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.upgrade_cluster_via_action_simple.action,
        )

        host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="one_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host)
        service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        component_1 = ServiceComponent.objects.get(service=service_1, prototype__name="component_1")
        component_2 = ServiceComponent.objects.get(service=service_1, prototype__name="component_2")
        HostComponent.objects.create(cluster=self.cluster_1, service=service_1, component=component_2, host=host)

        with patch("cm.upgrade.start_task", return_value=tasklog):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:upgrade-run",
                    kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade_cluster_via_action_complex.pk},
                ),
                data={
                    "host_component_map": [{"hostId": host.pk, "componentId": component_1.pk}],
                    "config": {"simple": "val", "grouped": {"simple": 5, "second": 4.3}, "after": ["x", "y"]},
                    "is_verbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        self.assertEqual(data["id"], tasklog.id)

    def test_provider_list_upgrades_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"hostprovider_pk": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)

    def test_provider_upgrade_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_upgrade.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {"id", "hostComponentMapRules", "configSchema", "isAllowToTerminate", "disclaimer"}
            )
        )
        self.assertEqual(upgrade_data["id"], self.provider_upgrade.pk)
        self.assertEqual(len(upgrade_data["hostComponentMapRules"]), 0)
        self.assertEqual(upgrade_data["configSchema"], None)
        self.assertEqual(upgrade_data["disclaimer"], "")
        self.assertFalse(upgrade_data["isAllowToTerminate"])

    def test_provider_upgrade_retrieve_complex_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.upgrade_host_via_action_complex.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        upgrade_data = response.json()
        self.assertTrue(
            set(upgrade_data.keys()).issuperset(
                {"id", "hostComponentMapRules", "configSchema", "isAllowToTerminate", "disclaimer"}
            )
        )

        self.assertEqual(upgrade_data["id"], self.upgrade_host_via_action_complex.pk)
        self.assertEqual(upgrade_data["disclaimer"], "Cool upgrade")
        self.assertFalse(upgrade_data["isAllowToTerminate"])

        self.assertEqual(len(upgrade_data["hostComponentMapRules"]), 0)

    def test_provider_upgrade_run_success(self):
        tasklog = TaskLog.objects.create(
            object_id=self.provider.pk,
            object_type=ContentType.objects.get(app_label="cm", model="hostprovider"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.upgrade_host_via_action_simple.action,
        )

        with patch("cm.upgrade.start_task", return_value=tasklog):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v2:upgrade-run",
                    kwargs={"hostprovider_pk": self.provider.pk, "pk": self.upgrade_host_via_action_simple.pk},
                ),
                data={
                    "host_component_map": [],
                    "config": {},
                    "is_verbose": True,
                },
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        data = response.json()
        self.assertTrue(set(data.keys()).issuperset({"id", "childJobs", "startTime"}))
        self.assertEqual(data["id"], tasklog.id)

    def test_provider_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.cluster_upgrade.pk},
            ),
            data={
                "host_component_map": [],
                "config": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.provider_upgrade.pk},
            ),
            data={
                "host_component_map": [],
                "config": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_provider_upgrade_run_not_found_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_upgrade.pk + 10},
            ),
            data={
                "host_component_map": [],
                "config": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_run_not_found_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk + 10},
            ),
            data={
                "host_component_map": [],
                "config": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk + 10},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_hostprovider_upgrade_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.cluster_upgrade.pk + 10},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_upgrade_hostcomponent_validation_fail(self):
        for hc_data in ([{"hostId": 1}], [{"componentId": 4}], [{}]):
            with self.subTest(f"Pass host_component_map as {hc_data}"):
                response: Response = self.client.post(
                    path=reverse(
                        viewname="v2:upgrade-run",
                        kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade_cluster_via_action_complex.pk},
                    ),
                    data={
                        "host_component_map": hc_data,
                        "config": {"simple": "val", "grouped": {"simple": 5, "second": 4.3}, "after": ["x", "y"]},
                        "is_verbose": True,
                    },
                )

                self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_cluster_list_unauthorized_fail(self) -> None:
        response: Response = self.unauthorized_client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_cluster_retrieve_unauthorized_fail(self):
        response: Response = self.unauthorized_client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_hostprovider_list_unauthorized_fail(self) -> None:
        response: Response = self.unauthorized_client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"hostprovider_pk": self.provider.pk}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_hostprovider_retrieve_unauthorized_fail(self):
        response: Response = self.unauthorized_client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"hostprovider_pk": self.cluster_1.pk, "pk": self.provider_upgrade.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)


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
