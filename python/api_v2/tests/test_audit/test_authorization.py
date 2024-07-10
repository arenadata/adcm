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

from datetime import timedelta

from audit.models import AuditSession
from rbac.models import User
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from api_v2.tests.base import BaseAPITestCase


class TestAuthorizationAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.username = self.password = "user"
        self.user = User.objects.create_superuser(self.username, "user@example.com", self.password)
        self.login_for_audit(username=self.username, password=self.password)
        last_login = AuditSession.objects.last()
        self.last_login_id = last_login.id
        current_datetime = last_login.login_time
        self.time_from = (current_datetime - timedelta(minutes=1)).isoformat()
        self.time_to = (current_datetime + timedelta(minutes=1)).isoformat()

    def login_for_audit(self, username="admin", password="admin"):
        response = self.client.v2["token"].post(
            data={"username": username, "password": password},
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    def test_logins_success(self):
        response = self.client.v2["audit-login"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["user"], {"name": self.username})
        self.assertDictEqual(response.json()["results"][0]["details"], {"username": self.username})

    def test_logins_time_filtering_success(self):
        response = self.client.v2["audit-login"].get(
            query={"time_from": self.time_from, "time_to": self.time_to},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["user"], {"name": self.username})

    def test_logins_time_filtering_empty_list_success(self):
        response = self.client.v2["audit-login"].get(
            query={"time_from": self.time_to, "time_to": self.time_from},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 0)

    def test_logins_retrieve_success(self):
        response = self.client.v2["audit-login", self.last_login_id].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["user"]["name"], self.username)
        self.assertDictEqual(response.json()["details"], {"username": self.username})

    def test_logins_retrieve_not_found_fail(self):
        response = self.client.v2["audit-login", self.last_login_id + 1].get()
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_logins_not_authorized_fail(self):
        self.client.logout()
        response = self.client.v2["audit-login"].get()
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_operations_not_authorized_fail(self):
        self.client.logout()
        response = self.client.v2["audit-login"].get()
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_operations_list_success(self):
        response = self.client.v2["audit-login"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
