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

from adcm.tests.base import BaseTestCase
from django.urls import reverse
from django.utils import timezone
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from rest_framework.test import APIClient

from audit.models import AuditSession, AuditSessionLoginResult


class TestAuthenticationAudit(BaseTestCase):
    def setUp(self) -> None:
        self.admin: User = User.objects.get(username="admin")
        self.disabled_user: User = User.objects.create_user(
            username="disabled_user",
            password="disabled_user",
            is_active=False,
        )

    def check_audit_session(self, user_id: int | None, login_result: AuditSessionLoginResult, username: str) -> None:
        log: AuditSession = AuditSession.objects.order_by("login_time").last()

        if log.user:
            self.assertEqual(log.user.username, User.objects.get(pk=user_id).username)
        else:
            self.assertEqual(log.user, user_id)
        self.assertEqual(log.login_result, login_result)
        self.assertDictEqual(log.login_details, {"username": username})

    def test_login_success(self):
        self.client.post(
            path=reverse(viewname="rest_framework:login"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.SUCCESS, self.admin.username)

    def test_login_wrong_password(self):
        self.client.post(
            path=reverse(viewname="rest_framework:login"),
            data={"username": self.admin.username, "password": "qwerty"},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

        self.client.post(path=reverse(viewname="rest_framework:login"), data={"username": self.admin.username})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

    def test_login_account_disabled(self):
        self.client.post(
            path=reverse(viewname="rest_framework:login"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.ACCOUNT_DISABLED,
            self.disabled_user.username,
        )

    def test_login_user_not_found(self):
        self.client.post(
            path=reverse(viewname="rest_framework:login"),
            data={"username": "unknown_user", "password": "unknown_user"},
        )
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(reverse("rest_framework:login"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "")

        self.client.post(reverse("rest_framework:login"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(reverse("rest_framework:login"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "1")

    def test_token_success(self):
        self.client.post(
            path=reverse(viewname="v1:token"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.SUCCESS, self.admin.username)

    def test_token_wrong_password(self):
        self.client.post(
            path=reverse(viewname="v1:token"), data={"username": self.admin.username, "password": "qwerty"}
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

        self.client.post(path=reverse(viewname="v1:token"), data={"username": self.admin.username})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

    def test_token_account_disabled(self):
        self.client.post(
            path=reverse(viewname="v1:token"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.ACCOUNT_DISABLED,
            self.disabled_user.username,
        )

    def test_token_user_not_found(self):
        self.client.post(
            path=reverse(viewname="v1:token"), data={"username": "unknown_user", "password": "unknown_user"}
        )
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(path=reverse(viewname="v1:token"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "")

        self.client.post(path=reverse(viewname="v1:token"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(path=reverse(viewname="v1:token"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "1")

    def test_rbac_token_success(self):
        self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.SUCCESS, self.admin.username)

    def test_rbac_token_wrong_password(self):
        self.client.post(
            path=reverse(viewname="v1:rbac:token"), data={"username": self.admin.username, "password": "qwerty"}
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

        self.client.post(path=reverse(viewname="v1:rbac:token"), data={"username": self.admin.username})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

    def test_rbac_token_account_disabled(self):
        self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.ACCOUNT_DISABLED,
            self.disabled_user.username,
        )

    def test_rbac_token_user_not_found(self):
        self.client.post(
            path=reverse(viewname="v1:rbac:token"), data={"username": "unknown_user", "password": "unknown_user"}
        )
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(path=reverse(viewname="v1:rbac:token"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "")

        self.client.post(path=reverse(viewname="v1:rbac:token"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(path=reverse(viewname="v1:rbac:token"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "1")


class TestLoginMiddleware(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.admin: User = User.objects.get(username="admin")

        self.disabled_user_creds = {"username": "disabled_user", "password": "disabled_user"}
        self.disabled_user: User = User.objects.create_user(**self.disabled_user_creds, is_active=False)

        self.brute_forcer_creds = {"username": "ettubrutus", "password": "ettubrutusettubrutus"}
        self.brute_user: User = User.objects.create_user(
            **self.brute_forcer_creds,
            failed_login_attempts=100,
            blocked_at=timezone.now() - timezone.timedelta(seconds=1),
            last_failed_login_at=timezone.now() - timezone.timedelta(seconds=1),
        )

        self.login_endpoints = (
            reverse(viewname="v2:login"),
            reverse(viewname="v2:token"),
            reverse(viewname="v1:token"),
            reverse(viewname="v1:rbac:token"),
        )

    def send_auth_request(self, endpoint: str, data: dict) -> tuple[APIClient, Response]:
        client = APIClient()
        response = client.post(path=endpoint, data=data)
        return client, response

    def send_profile_request(self, client: APIClient) -> Response:
        return client.get(path=reverse("v2:profile"))

    def test_login_success(self) -> None:
        data = {"username": "admin", "password": "admin"}
        for endpoint in self.login_endpoints:
            with self.subTest(endpoint):
                client, response = self.send_auth_request(endpoint=endpoint, data=data)

                self.assertEqual(response.status_code, HTTP_200_OK)

                self.admin.refresh_from_db()
                self.assertEqual(self.admin.failed_login_attempts, 0)

                self.assertEqual(self.send_profile_request(client=client).status_code, HTTP_200_OK)

    def test_login_blocked_manually_fail(self) -> None:
        data = self.disabled_user_creds
        for endpoint in self.login_endpoints:
            with self.subTest(endpoint):
                client, response = self.send_auth_request(endpoint=endpoint, data=data)

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
                self.assertEqual(self.send_profile_request(client=client).status_code, HTTP_401_UNAUTHORIZED)

    def test_login_blocked_brute_force_fail(self) -> None:
        data = self.brute_forcer_creds
        for endpoint in self.login_endpoints:
            with self.subTest(endpoint):
                client, response = self.send_auth_request(endpoint=endpoint, data=data)

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
                self.assertEqual(self.send_profile_request(client=client).status_code, HTTP_401_UNAUTHORIZED)
