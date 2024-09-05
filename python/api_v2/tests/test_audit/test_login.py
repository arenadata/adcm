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

from audit.models import AuditSession, AuditSessionLoginResult
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from api_v2.tests.base import BaseAPITestCase


class TestLoginAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.client.logout()
        self.target_url_paths = [(self.client.v2 / "token").path, (self.client.v2 / "login").path]

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_login_success(self):
        for url_path in self.target_url_paths:
            with self.subTest(msg=f"Login success for `{url_path}`"):
                response: Response = self.client.post(path=url_path, data=self.test_user_credentials)

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.check_last_audit_record(
                    model=AuditSession,
                    user__username=self.test_user_credentials["username"],
                    login_result=AuditSessionLoginResult.SUCCESS.value,
                    login_details={"username": self.test_user_credentials["username"]},
                ).delete()

    def test_login_wrong_password(self):
        for url_path in self.target_url_paths:
            with self.subTest(msg=f"Login wrong password for `{url_path}`"):
                response: Response = self.client.post(
                    path=url_path, data={**self.test_user_credentials, **{"password": "wrong"}}
                )

                self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
                self.check_last_audit_record(
                    model=AuditSession,
                    user__username=self.test_user_credentials["username"],
                    login_result=AuditSessionLoginResult.WRONG_PASSWORD.value,
                    login_details={"username": self.test_user_credentials["username"]},
                ).delete()

    def test_login_account_disabled(self):
        self.test_user.is_active = False
        self.test_user.save(update_fields=["is_active"])

        for url_path in self.target_url_paths:
            with self.subTest(msg=f"Login account disabled for `{url_path}`"):
                response: Response = self.client.post(path=url_path, data=self.test_user_credentials)

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
                self.check_last_audit_record(
                    model=AuditSession,
                    user__username=self.test_user_credentials["username"],
                    login_result=AuditSessionLoginResult.ACCOUNT_DISABLED.value,
                    login_details={"username": self.test_user_credentials["username"]},
                ).delete()

    def test_login_user_not_found(self):
        new_username = "non-existent-usern@me"

        for url_path in self.target_url_paths:
            with self.subTest(msg=f"Login user not found for `{url_path}`"):
                response: Response = self.client.post(
                    path=url_path, data={**self.test_user_credentials, **{"username": new_username}}
                )

                self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
                self.check_last_audit_record(
                    model=AuditSession,
                    user__isnull=True,
                    login_result=AuditSessionLoginResult.USER_NOT_FOUND.value,
                    login_details={"username": new_username},
                ).delete()
