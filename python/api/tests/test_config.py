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

from copy import deepcopy
from pathlib import Path

from cm.adcm_config.ansible import ansible_decrypt
from cm.models import ADCM, ConfigLog
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestConfigPasswordAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        _, self.cluster, self.config_log = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(settings.BASE_DIR, "python/api/tests/files/bundle_test_password.tar"),
        )

    def test_post_same_password_success(self):
        password_value = self.config_log.config["password"]

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"password": password_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["password"], password_value)

    def test_post_new_password_success(self):
        password_value = "new_test_password"

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"password": password_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ansible_decrypt(config_log.config["password"]), password_value)

    def test_post_wrong_password_fail(self):
        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"password": self.config_log.config["password"][:-1]}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(config_log.config["password"], self.config_log.config["password"])


class TestConfigSecrettextAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        _, self.cluster, self.config_log = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(settings.BASE_DIR, "python/api/tests/files/bundle_test_secrettext.tar"),
        )

    def test_post_same_secrettext_success(self):
        secrettext_value = self.config_log.config["secrettext"]

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secrettext": secrettext_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(config_log.config["secrettext"], secrettext_value)

    def test_post_new_secrettext_success(self):
        secrettext_value = "secrettext"

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secrettext": secrettext_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ansible_decrypt(config_log.config["secrettext"]), secrettext_value)

    def test_post_wrong_secrettext_fail(self):
        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secrettext": self.config_log.config["secrettext"][:-1]}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(config_log.config["secrettext"], self.config_log.config["secrettext"])


class TestConfigSecretfileAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        _, self.cluster, self.config_log = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(settings.BASE_DIR, "python/api/tests/files/bundle_test_secretfile.tar"),
        )

    def test_post_same_secretfile_success(self):
        secretfile_value = self.config_log.config["secretfile"]

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secretfile": secretfile_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ansible_decrypt(msg=config_log.config["secretfile"]), ansible_decrypt(msg=secretfile_value))

    def test_post_new_secretfile_success(self):
        secretfile_value = "new_test_secretfile_data"

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secretfile": secretfile_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ansible_decrypt(msg=config_log.config["secretfile"]), secretfile_value)

    def test_post_wrong_secretfile_fail(self):
        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secretfile": self.config_log.config["secretfile"][:-1]}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(config_log.config["secretfile"], self.config_log.config["secretfile"])


class TestConfigSecretmapAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        _, self.cluster, self.config_log = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(settings.BASE_DIR, "python/api/tests/files/bundle_test_secretmap.tar"),
        )

    def test_post_same_secretmap_success(self):
        secretmap_value = self.config_log.config["secretmap"]

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secretmap": secretmap_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictEqual(config_log.config["secretmap"], secretmap_value)

    def test_post_new_secretmap_success(self):
        secretmap_value = {"key": "new_test_secretmap_value"}

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secretmap": secretmap_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ansible_decrypt(config_log.config["secretmap"]["key"]), secretmap_value["key"])

    def test_post_wrong_secretmap_fail(self):
        secretmap_value = deepcopy(self.config_log.config["secretmap"])
        secretmap_value["key"] = secretmap_value["key"][:-1]

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secretmap": secretmap_value}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(config_log.config["secretmap"], self.config_log.config["secretmap"])

    def test_post_null_secretmap_success(self):
        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": self.cluster.pk}),
            params={"view": "interface"},
            data={"config": {"secretmap": None}},
            content_type=APPLICATION_JSON,
        )

        self.cluster.refresh_from_db()
        config_log = ConfigLog.objects.get(pk=self.cluster.config.current)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertIsNone(config_log.config["secretmap"])


class TestADCMConfigMinMaxPassLengthAPI(BaseTestCase):
    def test_min_pass_length_greater_than_max_fail(self):
        adcm = ADCM.objects.first()

        config_log = ConfigLog.objects.get(obj_ref=adcm.config)
        config_log.config["auth_policy"]["max_password_length"] = 1
        config_log.config["auth_policy"]["min_password_length"] = 2
        config_log.config["global"]["adcm_url"] = "http://127.0.0.1:8000"
        config_log.save(update_fields=["config"])

        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"adcm_pk": adcm.pk}),
            params={"view": "interface"},
            data={"config": config_log.config, "attr": config_log.attr},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["desc"],
            '"min_password_length" must be less or equal than "max_password_length"',
        )


class ADCMSettingsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.first()
        self.another_user_log_in(username=self.no_rights_user_username, password=self.no_rights_user_password)

    def test_retrieve_config_current_success(self):
        response: Response = self.client.get(path=reverse(viewname="config-current", kwargs={"adcm_pk": self.adcm.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.adcm.config.current)

    def test_retrieve_config_history_success(self):
        response: Response = self.client.get(path=reverse(viewname="config-history", kwargs={"adcm_pk": self.adcm.pk}))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_retrieve_config_history_by_history_version_success(self):
        config_log = ConfigLog.objects.get(obj_ref=self.adcm.config)
        config_log.config["global"]["adcm_url"] = "http://127.0.0.1:8000"
        config_log.save(update_fields=["config"])

        self.login()
        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"adcm_pk": self.adcm.pk}),
            data={"config": config_log.config, "attr": config_log.attr},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.adcm.refresh_from_db()

        self.another_user_log_in(username=self.no_rights_user_username, password=self.no_rights_user_password)
        response: Response = self.client.get(
            path=reverse(
                viewname="config-history-version",
                kwargs={"adcm_pk": self.adcm.pk, "version": self.adcm.config.previous},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.adcm.config.previous)

    def test_retrieve_config_previous_success(self):
        config_log = ConfigLog.objects.get(obj_ref=self.adcm.config)
        config_log.config["global"]["adcm_url"] = "http://127.0.0.1:8000"
        config_log.save(update_fields=["config"])

        self.login()
        response: Response = self.client.post(
            path=reverse(viewname="config-history", kwargs={"adcm_pk": self.adcm.pk}),
            data={"config": config_log.config, "attr": config_log.attr},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.another_user_log_in(username=self.no_rights_user_username, password=self.no_rights_user_password)
        response: Response = self.client.get(path=reverse("config-previous", kwargs={"adcm_pk": self.adcm.pk}))

        self.adcm.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.adcm.config.previous)

    def test_retrieve_config_by_pk_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="object-config", kwargs={"adcm_pk": self.adcm.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_list_config_log_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="config-log-list"),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_list_config_log_by_pk_success(self):
        config_log = ConfigLog.objects.get(obj_ref=self.adcm.config)
        response: Response = self.client.get(
            path=reverse(viewname="config-log-detail", kwargs={"pk": config_log.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())
