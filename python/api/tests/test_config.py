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

from cm.adcm_config import ansible_decrypt
from cm.models import ConfigLog
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

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
        self.assertEqual(config_log.config["secretfile"], secretfile_value)

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
        self.assertEqual(ansible_decrypt(config_log.config["secretfile"]), secretfile_value)

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
