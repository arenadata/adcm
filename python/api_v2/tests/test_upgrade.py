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


from api_v2.tests.base import BaseAPITestCase
from cm.models import ADCM, ConfigLog, Upgrade
from django.conf import settings
from django.urls import reverse
from init_db import init
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT
from rest_framework.test import APITestCase


class TestUpgrade(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        cluster_bundle_1_upgrade_path = (
            settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "cluster_one_upgrade"
        )
        provider_bundle_upgrade_path = (
            settings.BASE_DIR / "python" / "api_v2" / "tests" / "bundles" / "provider_upgrade"
        )
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
        self.upgrade_cluster_via_action = Upgrade.objects.get(name="upgrade_via_action", bundle=cluster_bundle_upgrade)
        self.upgrade_host_via_action = Upgrade.objects.get(name="upgrade_via_action", bundle=provider_bundle_upgrade)

    def test_cluster_list_upgrades_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_cluster_upgrade_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.cluster_upgrade.pk}
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_cluster_upgrade_run_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.upgrade_cluster_via_action.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_provider_list_upgrades_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:upgrade-list", kwargs={"hostprovider_pk": self.provider.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_provider_upgrade_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:upgrade-detail",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_upgrade.pk},
            ),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_provider_upgrade_run_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.upgrade_host_via_action.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_provider_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.cluster_upgrade.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_cluster_upgrade_run_violate_constraint_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.provider_upgrade.pk},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
                "is_verbose": True,
            },
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_provider_upgrade_run_not_found_fail(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:upgrade-run",
                kwargs={"hostprovider_pk": self.provider.pk, "pk": self.provider_upgrade.pk + 10},
            ),
            data={
                "host_component_map": [{}],
                "config": {},
                "attr": {},
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
                "host_component_map": [{}],
                "config": {},
                "attr": {},
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


class TestAdcmUpgrade(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        init_roles()
        init(
            adcm_conf_file=settings.BASE_DIR
            / "python"
            / "api_v2"
            / "tests"
            / "bundles"
            / "adcm_configs"
            / "config.yaml"
        )

    def setUp(self) -> None:
        super().setUp()
        self.original_adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(pk=self.original_adcm.config.current)
        config_log.config["job_log"]["log_rotation_on_fs"] = 120
        config_log.config["job_log"]["log_rotation_in_db"] = 50
        config_log.config["config_rotation"] = 10
        config_log.save()

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
