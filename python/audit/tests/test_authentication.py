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

from django.urls import reverse

from adcm.tests.base import BaseTestCase
from audit.models import AuditSession, AuditSessionLoginResult
from cm.models import ADCM, Bundle, ConfigLog, ObjectConfig, Prototype
from rbac.models import User


class TestAuthenticationAudit(BaseTestCase):
    def setUp(self) -> None:
        bundle: Bundle = Bundle.objects.create(
            name="ADCM",
            version="1.0",
        )
        prototype: Prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        object_config: ObjectConfig = ObjectConfig.objects.create(current=0, previous=0)
        config_log = ConfigLog.objects.create(
            obj_ref=object_config, config={}, attr={"ldap_integration": {"active": False}}
        )
        object_config.current = config_log.pk
        object_config.save(update_fields=["current"])

        ADCM.objects.create(prototype=prototype, config=object_config)
        self.admin: User = User.objects.create_superuser(username="admin", email="admin@arenadata.io", password="admin")
        self.disabled_user: User = User.objects.create_user(
            username="disabled_user", password="disabled_user", is_active=False
        )

    def check_audit_session(self, user_id: int | None, login_result: AuditSessionLoginResult, username: str) -> None:
        log: AuditSession = AuditSession.objects.order_by("login_time").last()

        self.assertEqual(log.user_id, user_id)
        self.assertEqual(log.login_result, login_result)
        self.assertDictEqual(log.login_details, {"username": username})

    def test_login_success(self):
        self.client.post(
            reverse("rest_framework:login"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.SUCCESS, self.admin.username)

    def test_login_wrong_password(self):
        self.client.post(
            reverse("rest_framework:login"),
            data={"username": self.admin.username, "password": "qwerty"},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

        self.client.post(reverse("rest_framework:login"), data={"username": self.admin.username})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

    def test_login_account_disabled(self):
        self.client.post(
            reverse("rest_framework:login"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.ACCOUNT_DISABLED,
            self.disabled_user.username,
        )

    def test_login_user_not_found(self):
        self.client.post(
            reverse("rest_framework:login"),
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
            reverse("token"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.SUCCESS, self.admin.username)

    def test_token_wrong_password(self):
        self.client.post(reverse("token"), data={"username": self.admin.username, "password": "qwerty"})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

        self.client.post(reverse("token"), data={"username": self.admin.username})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

    def test_token_account_disabled(self):
        self.client.post(
            reverse("token"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.ACCOUNT_DISABLED,
            self.disabled_user.username,
        )

    def test_token_user_not_found(self):
        self.client.post(reverse("token"), data={"username": "unknown_user", "password": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(reverse("token"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "")

        self.client.post(reverse("token"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(reverse("token"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "1")

    def test_rbac_token_success(self):
        self.client.post(
            reverse("rbac:token"),
            data={"username": self.admin.username, "password": self.admin.username},
        )
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.SUCCESS, self.admin.username)

    def test_rbac_token_wrong_password(self):
        self.client.post(reverse("rbac:token"), data={"username": self.admin.username, "password": "qwerty"})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

        self.client.post(reverse("rbac:token"), data={"username": self.admin.username})
        self.check_audit_session(self.admin.id, AuditSessionLoginResult.WRONG_PASSWORD, self.admin.username)

    def test_rbac_token_account_disabled(self):
        self.client.post(
            reverse("rbac:token"),
            data={"username": self.disabled_user.username, "password": self.disabled_user.username},
        )
        self.check_audit_session(
            self.disabled_user.id,
            AuditSessionLoginResult.ACCOUNT_DISABLED,
            self.disabled_user.username,
        )

    def test_rbac_token_user_not_found(self):
        self.client.post(reverse("rbac:token"), data={"username": "unknown_user", "password": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(reverse("rbac:token"), data={})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "")

        self.client.post(reverse("rbac:token"), data={"username": "unknown_user"})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "unknown_user")

        self.client.post(reverse("rbac:token"), data={"username": 1})
        self.check_audit_session(None, AuditSessionLoginResult.USER_NOT_FOUND, "1")
