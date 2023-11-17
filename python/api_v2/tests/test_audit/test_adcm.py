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


from api_v2.tests.base import BaseAPITestCase
from cm.models import ADCM, Action
from rbac.services.user import create_user
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class TestADCMAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user_credentials_2 = {"username": "test_user_username_2", "password": "test_user_password"}
        self.test_user = create_user(**self.test_user_credentials)
        self.test_user_2 = create_user(**self.test_user_credentials_2)

        self.adcm = ADCM.objects.first()
        self.data = {
            "config": {
                "global": {"adcm_url": "http://127.0.0.1:8000", "verification_public_key": "\n"},
                "google_oauth": {"client_id": None, "secret": None},
                "yandex_oauth": {"client_id": None, "secret": None},
                "ansible_settings": {"forks": 5},
                "logrotate": {"size": "10M", "max_history": 10, "compress": False},
                "audit_data_retention": {
                    "log_rotation_on_fs": 365,
                    "log_rotation_in_db": 365,
                    "config_rotation_in_db": 0,
                    "retention_period": 1825,
                    "data_archiving": False,
                },
                "ldap_integration": {
                    "ldap_uri": "test_ldap_uri",
                    "ldap_user": "test_ldap_user",
                    "ldap_password": "test_ldap_password",
                    "user_search_base": "test_ldap_user_search_base",
                    "user_search_filter": "https://test_ldap.url",
                    "user_object_class": "user",
                    "user_name_attribute": "sAMAccountName",
                    "group_search_base": None,
                    "group_search_filter": None,
                    "group_object_class": "group",
                    "group_name_attribute": "cn",
                    "group_member_attribute_name": "member",
                    "sync_interval": 60,
                    "tls_ca_cert_file": None,
                },
                "statistics_collection": {"url": "statistics_url"},
                "auth_policy": {
                    "min_password_length": 12,
                    "max_password_length": 20,
                    "login_attempt_limit": 5,
                    "block_time": 5,
                },
            },
            "adcmMeta": {
                "/logrotate": {"isActive": False},
                "/ldap_integration": {"isActive": False},
                "/statistics_collection": {"isActive": False},
            },
            "description": "new ADCM config",
        }

        Action.objects.filter(name="test_ldap_connection")

    def test_adcm_config_change_success(self):
        response = self.client.post(path=reverse(viewname="v2:adcm-config-list"), data=self.data)
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_log(
            operation_name="ADCM configuration updated",
            operation_type="update",
            operation_result="success",
            audit_object__object_id=self.adcm.pk,
            audit_object__object_name=self.adcm.name,
            audit_object__object_type="adcm",
            audit_object__is_deleted=False,
            object_changes={},
            user__username="admin",
        )

    def test_adcm_config_change_fail(self):
        response = self.client.post(path=reverse(viewname="v2:adcm-config-list"), data={})
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.check_last_audit_log(
            operation_name="ADCM configuration updated",
            operation_type="update",
            operation_result="fail",
            user__username="admin",
        )

    def test_adcm_config_change_access_denied(self):
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:adcm-config-list"), data=self.data)
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_log(
            operation_name="ADCM configuration updated",
            operation_type="update",
            operation_result="denied",
            user__username=self.test_user_credentials["username"],
        )

    def test_adcm_profile_password_change_success(self):
        response = self.client.put(
            path=reverse(viewname="v2:profile"), data={"newPassword": "newtestpassword", "currentPassword": "admin"}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name="admin user changed password",
            operation_type="update",
            operation_result="success",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_adcm_put_user_can_change_own_profile_success(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.put(
            path=reverse(viewname="v2:profile"),
            data={"newPassword": "newtestpassword", "currentPassword": "test_user_password"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name=f"{self.test_user_credentials['username']} user changed password",
            operation_type="update",
            operation_result="success",
            audit_object__is_deleted=False,
            user__username=self.test_user_credentials["username"],
        )

    def test_adcm_patch_user_can_change_own_profile_success(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.patch(
            path=reverse(viewname="v2:profile"),
            data={"newPassword": "newtestpassword", "currentPassword": "test_user_password"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_log(
            operation_name=f"{self.test_user_credentials['username']} user changed password",
            operation_type="update",
            operation_result="success",
            audit_object__is_deleted=False,
            user__username=self.test_user_credentials["username"],
        )

    def test_adcm_run_action_fail(self):
        adcm_action_pk = Action.objects.filter(name="test_ldap_connection").first().pk

        response = self.client.post(path=reverse(viewname="v2:adcm-action-run", kwargs={"pk": adcm_action_pk}))

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.check_last_audit_log(
            operation_name="Test LDAP connection action launched",
            operation_type="update",
            operation_result="fail",
            audit_object__is_deleted=False,
            user__username="admin",
        )

    def test_adcm_run_action_denied(self):
        adcm_action_pk = Action.objects.filter(name="test_ldap_connection").first().pk
        self.client.login(**self.test_user_credentials)

        response = self.client.post(path=reverse(viewname="v2:adcm-action-run", kwargs={"pk": adcm_action_pk}))

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_last_audit_log(
            operation_name="Test LDAP connection action launched",
            operation_type="update",
            operation_result="denied",
            audit_object__is_deleted=False,
            user__username=self.test_user_credentials["username"],
        )
