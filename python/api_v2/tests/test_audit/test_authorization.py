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

from audit.models import AuditLog, AuditObject, AuditObjectType, AuditSession, AuditUser
from core.rbac.dto import UserUpdateDTO
from rbac.models import User
from rbac.services.user import perform_user_update_as_superuser
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
import pytz

from api_v2.tests.base import BaseAPITestCase


class TestAuthorizationAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.username = self.password = "user"
        self.user = User.objects.create_superuser(self.username, "user@example.com", self.password)

        user_2 = User.objects.create_superuser("second", "second_user@example.com", self.password)
        self.client.v2["token"].post(
            data={"username": user_2.username, "password": self.password},
        )
        self.client.v2["token"].post(
            data={"username": user_2.username, "password": "wrong_password"},
        )

        self.login_for_audit(username=self.username, password=self.password)
        last_login = AuditSession.objects.last()
        self.last_login_id = last_login.id
        current_datetime = last_login.login_time
        self.time_from = (current_datetime - timedelta(minutes=1)).isoformat()
        self.time_to = (current_datetime + timedelta(minutes=1)).isoformat()

        for i, audit_log in enumerate(AuditLog.objects.all()):
            audit_log.operation_time = str(current_datetime - timedelta(minutes=i))
            audit_log.save()

    def login_for_audit(self, username="admin", password="admin"):
        response = self.client.v2["token"].post(
            data={"username": username, "password": password},
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

    def test_old_token_after_update_adcm_5121_success(self):
        user = self.create_user(username="new_test_user", password="test_password!")
        self.login_for_audit(username="new_test_user", password="test_password!")
        response = self.client.v2["token"].post(
            data={"username": user.username, "password": "test_password!"},
        )
        token = response.json()["token"]

        perform_user_update_as_superuser(
            user_id=user.pk,
            update_data=UserUpdateDTO(
                first_name="test_user_first_name", last_name="test_user_last_name", email="test_user@mail.ru"
            ),
            new_password="newtestpassword",
            new_user_groups=None,
        )

        self.client.defaults["HTTP_AUTHORIZATION"] = f"Token {token}"
        response = self.client.v2["token"].post(
            data={"username": "new_test_user", "password": "newtestpassword"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_logins_success(self):
        response = self.client.v2["audit-login"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["user"], {"name": self.username})
        self.assertDictEqual(response.json()["results"][0]["details"], {"username": self.username})

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

    def test_filtering_success(self):
        audit_session = AuditSession.objects.last()
        filters = {
            "id": (audit_session.pk, None, 0),
            "login": (
                self.username,
                self.username[1:-3].upper(),
                "wrong",
            ),
            "loginResult": ("wrong password", None, "account disabled"),
            "timeFrom": (
                datetime.fromisoformat(self.time_from) + timedelta(minutes=1),
                None,
                datetime.fromisoformat(self.time_from) + timedelta(minutes=2),
            ),
        }
        exact_items_found, partial_items_found = 1, 1
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = self.client.v2["audit-login"].get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], exact_items_found)

                response = self.client.v2["audit-login"].get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

                if partial_value:
                    response = self.client.v2["audit-login"].get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], partial_items_found)

    def test_ordering_success(self):
        ordering_fields = (
            ("login_time", "loginTime"),
            ("login_time", "time"),
        )

        def get_response_results(response, ordering_field):
            if ordering_field == "login":
                return [item["user"]["name"] for item in response.json()["results"]]
            elif ordering_field in ("time", "loginTime"):
                return [
                    datetime.fromisoformat(item["time"][:-1]).replace(tzinfo=pytz.UTC)
                    for item in response.json()["results"]
                ]
            elif ordering_field == "loginResult":
                return [item["result"] for item in response.json()["results"]]
            return [item[ordering_field] for item in response.json()["results"]]

        for model_field, ordering_field in ordering_fields:
            with self.subTest(ordering_field=ordering_field):
                response = self.client.v2["audit-login"].get(query={"ordering": ordering_field})
                ordered_result = get_response_results(response, ordering_field)
                self.assertListEqual(
                    ordered_result,
                    list(AuditSession.objects.order_by(model_field).values_list(model_field, flat=True)),
                )

                response = self.client.v2["audit-login"].get(query={"ordering": f"-{ordering_field}"})
                ordered_result = get_response_results(response, ordering_field)
                self.assertListEqual(
                    ordered_result,
                    list(AuditSession.objects.order_by(f"-{model_field}").values_list(model_field, flat=True)),
                )


class TestOperationsAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.username = self.password = "user"
        self.user = User.objects.create_superuser(self.username, "user@example.com", self.password)
        User.objects.create_superuser("second_user", "second_user@example.com", self.password)
        User.objects.create_superuser("third_user", "third_user@example.com", self.password)
        current_datetime = datetime.now(pytz.utc)
        self.time_from = (current_datetime - timedelta(minutes=1)).isoformat()
        self.time_to = (current_datetime + timedelta(minutes=1)).isoformat()

        audit_user_1 = AuditUser.objects.filter(username=self.username).order_by("-pk").first()
        audit_user_2 = AuditUser.objects.filter(username="second_user").order_by("-pk").first()
        audit_user_3 = AuditUser.objects.filter(username="third_user").order_by("-pk").first()

        audit_object_1 = AuditObject.objects.create(
            object_id=1,
            object_name="cluster_test_object",
            object_type=AuditObjectType.CLUSTER,
            is_deleted=False,
        )
        audit_object_2 = AuditObject.objects.create(
            object_id=2,
            object_name="service_test_object",
            object_type=AuditObjectType.SERVICE,
            is_deleted=False,
        )
        audit_object_3 = AuditObject.objects.create(
            object_id=3,
            object_name="component_test_object",
            object_type=AuditObjectType.COMPONENT,
            is_deleted=False,
        )

        for (
            audit_object,
            audit_user,
            operation_name,
            operation_type,
            result,
            hours_delta,
        ) in [
            (
                audit_object_1,
                audit_user_1,
                "first operation",
                "create",
                "success",
                0,
            ),
            (
                audit_object_2,
                audit_user_2,
                "second operation",
                "update",
                "success",
                1,
            ),
            (
                audit_object_3,
                audit_user_3,
                "3 operation",
                "update",
                "fail",
                2,
            ),
        ]:
            audit_log = AuditLog.objects.create(
                audit_object=audit_object,
                operation_name=operation_name,
                operation_type=operation_type,
                operation_result=result,
                user=audit_user,
                object_changes={},
                address="127.0.0.1",
                agent="Test user-agent",
            )
            audit_log.operation_time = str(current_datetime - timedelta(hours=hours_delta))
            audit_log.save()

    def test_filtering_success(self):
        audit_log = AuditLog.objects.last()
        filters = {
            "id": (audit_log.pk, None, 0),
            "objectName": (
                audit_log.audit_object.object_name,
                audit_log.audit_object.object_name[1:-3].upper(),
                "wrong",
            ),
            "objectType": (audit_log.audit_object.object_type, None, "host"),
            "timeFrom": (self.time_from, None, datetime.fromisoformat(self.time_from) + timedelta(hours=1)),
            "timeTo": (
                datetime.fromisoformat(self.time_to) - timedelta(hours=2),
                None,
                datetime.fromisoformat(self.time_to) - timedelta(hours=3),
            ),
            "operationResult": (audit_log.operation_result, None, "denied"),
            "operationType": ("create", None, "delete"),
            "userName": ("second_user", audit_log.user.username[1:-3].upper(), "wrong"),
        }
        exact_items_found, partial_items_found = 1, 1
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = self.client.v2["audit-operation"].get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], exact_items_found)

                response = self.client.v2["audit-operation"].get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

                if partial_value:
                    response = self.client.v2["audit-operation"].get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], partial_items_found)

    def test_ordering_success(self):
        ordering_fields = {
            "operation_name": "name",
            "operation_result": "result",
            "operation_type": "type",
            "audit_object__object_name": "objectName",
            "audit_object__object_type": "objectType",
            "operation_time": "time",
            "user__username": "userName",
        }

        def get_response_results(response, ordering_field):
            if ordering_field in ["objectName", "objectType"]:
                return [item["object"][ordering_field[6::].lower()] for item in response.json()["results"]]
            elif ordering_field == "userName":
                return [item["user"]["name"] for item in response.json()["results"]]
            elif ordering_field == "time":
                return [
                    datetime.fromisoformat(item[ordering_field][:-1]).replace(tzinfo=pytz.UTC)
                    for item in response.json()["results"]
                ]
            return [item[ordering_field] for item in response.json()["results"]]

        for model_field, ordering_field in ordering_fields.items():
            with self.subTest(ordering_field=ordering_field):
                response = self.client.v2["audit-operation"].get(query={"ordering": ordering_field})
                ordered_result = get_response_results(response, ordering_field)
                self.assertListEqual(
                    ordered_result,
                    list(AuditLog.objects.order_by(model_field).values_list(model_field, flat=True)),
                )

                response = self.client.v2["audit-operation"].get(query={"ordering": f"-{ordering_field}"})
                ordered_result = get_response_results(response, ordering_field)
                self.assertListEqual(
                    ordered_result,
                    list(AuditLog.objects.order_by(f"-{model_field}").values_list(model_field, flat=True)),
                )
