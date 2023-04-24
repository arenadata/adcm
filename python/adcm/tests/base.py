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

import random
import string
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree

from cm.models import ADCM, Bundle, Cluster, ConfigLog, Prototype
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from init_db import init
from rbac.models import User
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

APPLICATION_JSON = "application/json"


class BaseTestCase(TestCase):
    # pylint: disable=too-many-instance-attributes

    def setUp(self) -> None:
        self.test_user_username = "test_user"
        self.test_user_password = "test_user_password"

        self.test_user = User.objects.create_user(
            username=self.test_user_username,
            password=self.test_user_password,
            is_superuser=True,
        )

        self.no_rights_user_username = "no_rights_user"
        self.no_rights_user_password = "no_rights_user_password"
        self.no_rights_user = User.objects.create_user(
            username="no_rights_user",
            password="no_rights_user_password",
        )

        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.login()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        init_roles()
        init()

        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.get(obj_ref=adcm.config)
        config_log.config["auth_policy"]["max_password_length"] = 20
        config_log.save(update_fields=["config"])

    def tearDown(self) -> None:
        dirs_to_clear = (
            *Path(settings.BUNDLE_DIR).iterdir(),
            *Path(settings.DOWNLOAD_DIR).iterdir(),
            *Path(settings.FILE_DIR).iterdir(),
            *Path(settings.LOG_DIR).iterdir(),
            *Path(settings.RUN_DIR).iterdir(),
        )
        for item in dirs_to_clear:
            if item.is_dir():
                rmtree(item)
            else:
                if item.name != ".gitkeep":
                    item.unlink()

    def login(self):
        response: Response = self.client.post(
            path=reverse("rbac:token"),
            data={"username": self.test_user_username, "password": self.test_user_password},
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    @property
    @contextmanager
    def no_rights_user_logged_in(self):
        self.client.post(path=reverse("rbac:logout"))
        response: Response = self.client.post(
            path=reverse("rbac:token"),
            data={
                "username": self.no_rights_user_username,
                "password": self.no_rights_user_password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        yield

        self.login()

    @contextmanager
    def another_user_logged_in(self, username: str, password: str):
        self.client.post(path=reverse("rbac:logout"))
        response: Response = self.client.post(
            path=reverse("rbac:token"),
            data={
                "username": username,
                "password": password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        yield

        self.login()

    def another_user_log_in(self, username: str, password: str):
        self.client.post(path=reverse("rbac:logout"))
        response: Response = self.client.post(
            path=reverse("rbac:token"),
            data={
                "username": username,
                "password": password,
            },
            content_type=APPLICATION_JSON,
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    def upload_bundle(self, path: Path) -> None:
        with open(path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def load_bundle(self, path: Path) -> Bundle:
        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": path.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        return Bundle.objects.get(pk=response.data["id"])

    def upload_and_load_bundle(self, path: Path) -> Bundle:
        self.upload_bundle(path=path)

        return self.load_bundle(path=path)

    def upload_bundle_create_cluster_config_log(
        self, bundle_path: Path, cluster_name: str = "test-cluster"
    ) -> tuple[Bundle, Cluster, ConfigLog]:
        bundle = self.upload_and_load_bundle(path=bundle_path)

        cluster_prototype = Prototype.objects.get(bundle_id=bundle.pk, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse("cluster"),
            data={"name": cluster_name, "prototype_id": cluster_prototype.pk},
        )
        cluster = Cluster.objects.get(pk=cluster_response.data["id"])

        return bundle, cluster, ConfigLog.objects.get(obj_ref=cluster.config)

    @staticmethod
    def get_random_str_num(length: int) -> str:
        return "".join(random.sample(f"{string.ascii_letters}{string.digits}", length))
