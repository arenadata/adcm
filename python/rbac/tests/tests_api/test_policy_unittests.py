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

from django.test import Client, TestCase
from django.urls import reverse

from init_db import init as init_adcm
from rbac.models import Policy, Role, User
from rbac.upgrade.role import init_roles


class TestBase(TestCase):
    def setUp(self) -> None:
        init_adcm()
        init_roles()

        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        response = self.client.post(
            path=reverse("rbac:token"),
            data={"username": "admin", "password": "admin"},
            content_type="application/json",
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"
        self.admin = User.objects.get(username="admin")

        self.role = Role.objects.create(
            name="Test role", module_name="rbac.roles", class_name="ModelRole"
        )
        self.policy = Policy.objects.create(name="Test policy", role=self.role, built_in=False)
        self.policy.user.add(self.admin)


class TestPolicy(TestBase):
    def test_patch_empty_role_id(self):
        url = reverse("rbac:policy-detail", kwargs={"pk": self.policy.pk})
        data_valid = {
            "id": self.policy.pk,
            "name": self.policy.name,
            "description": self.policy.description,
            "built_in": self.policy.built_in,
            "role": {
                "id": self.role.pk,
            },
        }
        response = self.client.patch(url, data=data_valid, content_type="application/json")
        self.assertEqual(response.status_code, 200)

        response = self.client.patch(
            url, data={**data_valid, **{"role": {}}}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["role"], ["This field may not be empty."])
