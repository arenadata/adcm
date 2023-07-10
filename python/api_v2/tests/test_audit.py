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
# pylint: disable=too-many-lines

from datetime import timedelta

from api_v2.tests.base import BaseAPITestCase
from audit.models import AuditSession
from rbac.models import User
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND


class TestAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.username = self.password = "user"
        self.user = User.objects.create_user(self.username, "user@example.com", self.password)
        self.login_for_audit(username=self.username, password=self.password)
        last_login = AuditSession.objects.last()
        self.last_login_id = last_login.id
        current_datetime = last_login.login_time
        self.time_from = (current_datetime - timedelta(minutes=1)).isoformat()
        self.time_to = (current_datetime + timedelta(minutes=1)).isoformat()

    def login_for_audit(self, username="admin", password="admin"):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": username, "password": password},
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    def test_logins_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-list"),
        )
        self.assertEqual(response.json()["results"][0]["login_details"], {"username": self.username})
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_logins_time_filtering_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-list"),
            data={"time_to": self.time_to, "time_from": self.time_from},
        )
        self.assertEqual(response.json()["results"][0]["login_details"], {"username": self.username})
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_logins_time_filtering_empty_list_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-list"),
            data={"time_to": self.time_from, "time_from": self.time_to},
        )
        self.assertEqual(len(response.json()["results"]), 0)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_logins_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-detail", kwargs={"pk": self.last_login_id})
        )
        self.assertEqual(response.json()["login_details"]["username"], self.username)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_logins_retrieve_not_found_fail(self):
        response = self.client.get(
            path=reverse(viewname="v2:audit:auditsession-detail", kwargs={"pk": self.last_login_id + 1})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_logins_not_authorized_fail(self):
        self.client.logout()
        response = self.client.get(path=reverse(viewname="v2:audit:auditsession-list"))
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_operations_not_authorized_fail(self):
        self.client.logout()
        response = self.client.get(path=reverse(viewname="v2:audit:auditlog-list"))
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_operations_list_success(self):
        response = self.client.get(path=reverse(viewname="v2:audit:auditlog-list"))
        self.assertEqual(response.status_code, HTTP_200_OK)
