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

from django.test import TestCase
from django.urls import reverse

from audit.models import AuditSession, AuditSessionLoginResult
from cm.models import ADCM, Bundle, ConfigLog, ObjectConfig, Prototype
from rbac.models import User


class TestAuthentication(TestCase):
    def setUp(self) -> None:
        bundle: Bundle = Bundle.objects.create(
            name="ADCM",
            version="1.0",
        )
        prototype: Prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        object_config: ObjectConfig = ObjectConfig.objects.create(current=1, previous=0)
        ConfigLog.objects.create(
            obj_ref=object_config, config={}, attr={"ldap_integration": {"active": False}}
        )
        ADCM.objects.create(prototype=prototype, config=object_config)
        self.admin: User = User.objects.create_superuser(
            username="admin", email="admin@arenadata.io", password="admin"
        )
        self.disabled_user: User = User.objects.create_user(
            username="disabled_user", password="disabled_user", is_active=False
        )

    def check_audit_session(
        self, user_id: int | None, login_result: AuditSessionLoginResult, username: str
    ) -> None:
        log: AuditSession = AuditSession.objects.order_by("login_time").last()

        self.assertEqual(log.user_id, user_id)
        self.assertEqual(log.login_result, login_result)
        self.assertDictEqual(log.login_details, {"username": username})

    def test_login_success(self):
        self.client.post(
            reverse("rest_framework:login"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.Success, self.admin.username
        )

    def test_login_wrong_password(self):
        self.client.post(
            reverse("rest_framework:login"),
            data={"username": self.admin.username, "password": "qwerty"},
        )
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.WrongPassword, self.admin.username
        )

        self.client.post(reverse("rest_framework:login"), data={"username": self.admin.username})
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.WrongPassword, self.admin.username
        )

    def test_login_account_disabled(self):
        self.client.post(
            reverse("rest_framework:login"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.AccountDisabled,
            self.disabled_user.username,
        )

    def test_login_user_not_found(self):
        self.client.post(
            reverse("rest_framework:login"),
            data={"username": "unknown_user", "password": "unknown_user"},
        )
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "unknown_user")

        self.client.post(reverse("rest_framework:login"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "")

        self.client.post(reverse("rest_framework:login"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "unknown_user")

        self.client.post(reverse("rest_framework:login"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "1")

    def test_token_success(self):
        self.client.post(
            reverse("token"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.Success, self.admin.username
        )

    def test_token_wrong_password(self):
        self.client.post(
            reverse("token"), data={"username": self.admin.username, "password": "qwerty"}
        )
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.WrongPassword, self.admin.username
        )

        self.client.post(reverse("token"), data={"username": self.admin.username})
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.WrongPassword, self.admin.username
        )

    def test_token_account_disabled(self):
        self.client.post(
            reverse("token"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.AccountDisabled,
            self.disabled_user.username,
        )

    def test_token_user_not_found(self):
        self.client.post(
            reverse("token"), data={"username": "unknown_user", "password": "unknown_user"}
        )
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "unknown_user")

        self.client.post(reverse("token"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "")

        self.client.post(reverse("token"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "unknown_user")

        self.client.post(reverse("token"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "1")

    def test_rbac_token_success(self):
        self.client.post(
            reverse("rbac:token"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.Success, self.admin.username
        )

    def test_rbac_token_wrong_password(self):
        self.client.post(
            reverse("rbac:token"), data={"username": self.admin.username, "password": "qwerty"}
        )
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.WrongPassword, self.admin.username
        )

        self.client.post(reverse("rbac:token"), data={"username": self.admin.username})
        self.check_audit_session(
            self.admin.id, AuditSessionLoginResult.WrongPassword, self.admin.username
        )

    def test_rbac_token_account_disabled(self):
        self.client.post(
            reverse("rbac:token"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.AccountDisabled,
            self.disabled_user.username,
        )

    def test_rbac_token_user_not_found(self):
        self.client.post(
            reverse("rbac:token"), data={"username": "unknown_user", "password": "unknown_user"}
        )
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "unknown_user")

        self.client.post(reverse("rbac:token"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "")

        self.client.post(reverse("rbac:token"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "unknown_user")

        self.client.post(reverse("rbac:token"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.UserNotFound, "1")
