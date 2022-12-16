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

from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from cm.models import Bundle, Cluster, ConfigLog, Prototype
from rbac.models import Role, User

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

        self.cluster_admin_role = Role.objects.create(
            name="Cluster Administrator",
            display_name="Cluster Administrator",
        )
        Role.objects.create(name="Provider Administrator", display_name="Provider Administrator")
        Role.objects.create(name="Service Administrator", display_name="Service Administrator")

        self.test_bundle_filename = "test_bundle.tar"
        self.test_bundle_path = Path(
            settings.BASE_DIR,
            "python/audit/tests/files",
            self.test_bundle_filename,
        )

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

    def upload_and_load_bundle(self, path: Path) -> Bundle:
        with open(path, encoding=settings.ENCODING_UTF_8) as f:
            response: Response = self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": path.name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        return Bundle.objects.get(pk=response.data["id"])

    def upload_bundle_create_cluster_config_log(self, bundle_path: Path) -> tuple[Bundle, Cluster, ConfigLog]:
        bundle = self.upload_and_load_bundle(path=bundle_path)

        cluster_prototype = Prototype.objects.get(bundle_id=bundle.pk, type="cluster")
        cluster_response: Response = self.client.post(
            path=reverse("cluster"),
            data={"name": "test-cluster", "prototype_id": cluster_prototype.pk},
        )
        cluster = Cluster.objects.get(pk=cluster_response.data["id"])

        return bundle, cluster, ConfigLog.objects.get(obj_ref=cluster.config)
