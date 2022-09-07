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

        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')
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
