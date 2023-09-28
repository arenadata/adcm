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
from django.urls import reverse
from rbac.models import User

from adcm.tests.base import BaseTestCase


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
