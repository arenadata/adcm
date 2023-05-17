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

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from cm.models import ADCM, ConfigLog
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rbac.models import OriginType, User
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_409_CONFLICT,
)

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class BaseUserTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        adcm = ADCM.objects.first()
        self.config_log = ConfigLog.objects.filter(obj_ref=adcm.config).first()


class UserTestCase(BaseUserTestCase):
    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-list"),
            data={
                "username": "test_user_new",
                "password": self.get_random_str_num(
                    length=self.config_log.config["auth_policy"]["max_password_length"] - 1,
                ),
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_filter_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:rbac:user-list"), data={"type": OriginType.LOCAL}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)

        self.test_user.type = OriginType.LDAP
        self.test_user.save(update_fields=["type"])

        response: Response = self.client.get(
            path=reverse(viewname="v1:rbac:user-list"), data={"type": OriginType.LOCAL}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 4)

    def test_failed_login_attempts(self):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))

        self.config_log.config["auth_policy"]["login_attempt_limit"] = 2
        self.config_log.config["auth_policy"]["block_time"] = 1
        self.config_log.save(update_fields=["config"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": "wrong_password"},
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.test_user.failed_login_attempts, 1)
        self.assertIsNone(self.test_user.blocked_at)

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": "wrong_password"},
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(self.test_user.failed_login_attempts, 2)
        self.assertIsNotNone(self.test_user.blocked_at)

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": "wrong_password"},
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(self.test_user.failed_login_attempts, 2)
        self.assertIsNotNone(self.test_user.blocked_at)

        self.test_user.refresh_from_db()
        self.test_user.blocked_at = datetime.now(tz=ZoneInfo(settings.TIME_ZONE)) - timedelta(
            minutes=self.config_log.config["auth_policy"]["block_time"]
        )
        self.test_user.save(update_fields=["blocked_at"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": "wrong_password"},
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.test_user.failed_login_attempts, 1)
        self.assertIsNone(self.test_user.blocked_at)

        self.test_user.refresh_from_db()
        self.test_user.blocked_at = None
        self.test_user.save(update_fields=["blocked_at"])

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": self.test_user_password},
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.test_user.failed_login_attempts, 0)
        self.assertIsNone(self.test_user.blocked_at)

    def test_reset_failed_login_attempts_not_superuser_fail(self):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": "wrong_password"},
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.test_user.failed_login_attempts, 1)
        self.assertIsNone(self.test_user.blocked_at)

        self.no_rights_user.user_permissions.add(
            Permission.objects.get(codename="add_user", content_type=ContentType.objects.get_for_model(User)),
        )
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={
                "username": self.no_rights_user_username,
                "password": self.no_rights_user_password,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-reset-failed-login-attempts", kwargs={"pk": self.test_user.pk}),
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Only superuser can reset login attempts.")

        self.test_user.refresh_from_db()

        self.assertEqual(self.test_user.failed_login_attempts, 1)
        self.assertIsNone(self.test_user.blocked_at)

    def test_reset_failed_login_attempts_wrong_user_fail(self):
        user_pks = User.objects.all().values_list("pk", flat=True).order_by("-pk")
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-reset-failed-login-attempts", kwargs={"pk": user_pks[0] + 1}),
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], f"User with ID {user_pks[0] + 1} was not found.")

    def test_reset_failed_login_attempts_success(self):
        self.client.post(path=reverse(viewname="v1:rbac:logout"))

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:token"),
            data={"username": self.test_user_username, "password": "wrong_password"},
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.test_user.failed_login_attempts, 1)
        self.assertIsNone(self.test_user.blocked_at)

        self.login()

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-reset-failed-login-attempts", kwargs={"pk": self.test_user.pk}),
        )

        self.test_user.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(self.test_user.failed_login_attempts, 0)
        self.assertIsNone(self.test_user.blocked_at)

    def test_change_profile_ldap_user_via_me_endpoint_success(self):
        self.test_user.type = OriginType.LDAP
        self.test_user.save(update_fields=["type"])

        response: Response = self.client.patch(
            reverse(viewname="v1:rbac:me"),
            data={"profile": {"test_profile_key": "test_profile_value"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_change_profile_ldap_user_via_user_endpoint_success(self):
        self.test_user.type = OriginType.LDAP
        self.test_user.save(update_fields=["type"])

        response: Response = self.client.patch(
            reverse(viewname="v1:rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={"profile": {"test_profile_key": "test_profile_value"}},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)


class UserPasswordTestCase(BaseUserTestCase):
    def test_create_shorter_than_min_password_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-list"),
            data={
                "username": "test_user_new",
                "password": self.get_random_str_num(
                    length=self.config_log.config["auth_policy"]["min_password_length"] - 1,
                ),
            },
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["desc"], "This password is shorter than min password length")

    def test_create_longer_than_max_password_fail(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-list"),
            data={
                "username": "test_user_new",
                "password": self.get_random_str_num(
                    length=self.config_log.config["auth_policy"]["max_password_length"] + 1,
                ),
            },
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["desc"], "This password is longer than max password length")

    def test_update_longer_than_max_password_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={
                "password": self.get_random_str_num(
                    length=self.config_log.config["auth_policy"]["max_password_length"] + 1,
                ),
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["desc"], "This password is longer than max password length")

    def test_update_password_success(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={
                "password": self.get_random_str_num(
                    length=self.config_log.config["auth_policy"]["max_password_length"] - 1,
                ),
                "current_password": self.test_user_password,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_change_password_no_current_password_fail(self):
        self.test_user.is_superuser = False
        self.test_user.save(update_fields=["is_superuser"])

        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:me"),
            data={"password": "new_pass"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["desc"],
            'Field "current_password" should be filled and match user current password',
        )

    def test_change_password_success(self):
        new_pass = "new_very_long_pass"
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:me"),
            data={"password": new_pass, "current_password": self.test_user_password},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.post(
            path=reverse(viewname="v1:token"),
            data={"username": self.test_user_username, "password": new_pass},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_change_min_password_length_add_user_success(self):
        adcm = ADCM.objects.first()
        config_log = ConfigLog.objects.filter(obj_ref=adcm.config).first()
        config_log.config["auth_policy"]["min_password_length"] = 1
        config_log.config["global"]["adcm_url"] = "http://127.0.0.1:8000"

        response: Response = self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"adcm_pk": adcm.pk}),
            params={"view": "interface"},
            data={"config": config_log.config, "attr": config_log.attr},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:rbac:user-list"),
            data={
                "username": "test_config_username",
                "password": "test_pass",
                "first_name": "test_config_first_name",
                "last_name": "test_config_last_name",
                "email": "test@email.ru",
                "group": [],
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_change_password_ldap_user_via_me_endpoint_fail(self):
        self.test_user.type = OriginType.LDAP
        self.test_user.save(update_fields=["type"])

        new_pass = "new_pass"
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:me"),
            data={"password": new_pass, "current_password": self.test_user_password},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["desc"], 'You can change only "profile" for LDAP type user')

    def test_change_password_ldap_user_via_user_endpoint_fail(self):
        self.test_user.type = OriginType.LDAP
        self.test_user.save(update_fields=["type"])

        new_pass = "new_very_long_pass"
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={"password": new_pass},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["desc"], 'You can change only "profile" for LDAP type user')

    def test_admin_change_password_user_via_user_endpoint_success(self):
        new_pass = "new_very_long_pass"
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:user-detail", kwargs={"pk": self.test_user.pk}),
            data={"password": new_pass},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_update_shorter_than_min_password_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:me"),
            data={
                "password": self.get_random_str_num(
                    length=self.config_log.config["auth_policy"]["min_password_length"] - 1,
                ),
                "current_password": self.test_user_password,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["desc"], "This password is shorter than min password length")
