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

from datetime import datetime

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditSession,
    AuditSessionLoginResult,
)
from django.urls import reverse
from django.utils import timezone as tz
from init_db import init as init_adcm
from rbac.upgrade.role import init_roles
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestAuditViews(BaseTestCase):
    # pylint: disable=too-many-instance-attributes

    def setUp(self) -> None:
        super().setUp()

        init_adcm()
        init_roles()

        self.object_name_first = "object_name_first"
        self.object_name_second = "object_name_second"
        self.audit_object_first = AuditObject.objects.create(
            object_id=0,
            object_name=self.object_name_first,
            object_type=AuditObjectType.CLUSTER,
            is_deleted=False,
        )
        self.audit_object_second = AuditObject.objects.create(
            object_id=1,
            object_name=self.object_name_second,
            object_type=AuditObjectType.COMPONENT,
            is_deleted=True,
        )

        date_fmt = "%Y-%m-%dT%H:%M:%SZ"
        self.operation_name_first = "operation_name_first"
        self.operation_name_second = "operation_name_second"
        self.date_first_filter = "2001-01-01"
        self.date_first = f"{self.date_first_filter}T01:01:01Z"
        self.date_second_filter = "2010-10-10"
        self.date_second = f"{self.date_second_filter}T10:10:10Z"
        self.object_changes_first = {"test": {"object_changes": "first"}}
        self.object_changes_second = {"test": {"object_changes": "second"}}

        self.audit_log_first = AuditLog.objects.create(
            audit_object=self.audit_object_first,
            operation_name=self.operation_name_first,
            operation_type=AuditLogOperationType.CREATE,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            object_changes=self.object_changes_first,
        )
        AuditLog.objects.filter(pk=self.audit_log_first.pk).update(
            operation_time=tz.make_aware(datetime.strptime(self.date_first, date_fmt))
        )
        self.audit_log_second = AuditLog.objects.create(
            audit_object=self.audit_object_second,
            operation_name=self.operation_name_second,
            operation_type=AuditLogOperationType.UPDATE,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.no_rights_user,
            object_changes=self.object_changes_second,
        )
        AuditLog.objects.filter(pk=self.audit_log_second.pk).update(
            operation_time=tz.make_aware(datetime.strptime(self.date_second, date_fmt))
        )

        self.login_details_first = {"login": {"details": "first"}}
        self.login_details_second = {"login": {"details": "second"}}

        self.audit_session_first = AuditSession.objects.create(
            user=self.test_user,
            login_result=AuditSessionLoginResult.SUCCESS,
            login_details=self.login_details_first,
        )
        self.audit_session_second = AuditSession.objects.create(
            user=self.no_rights_user,
            login_result=AuditSessionLoginResult.WRONG_PASSWORD,
            login_details=self.login_details_second,
        )
        AuditSession.objects.filter(pk=self.audit_session_second.pk).update(
            login_time=tz.make_aware(datetime.strptime(self.date_second, date_fmt))
        )

    def test_audit_operations_visibility_superuser(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(path=reverse("audit:auditlog-list"), content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], AuditLog.objects.count())

    def test_audit_operations_visibility_regular_user(self):
        with self.another_user_logged_in(username=self.no_rights_user_username, password=self.no_rights_user_password):
            response: Response = self.client.get(path=reverse("audit:auditlog-list"), content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["code"], "AUDIT_OPERATIONS_FORBIDDEN")

    def test_audit_logins_visibility_superuser(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(path=reverse("audit:auditsession-list"), content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertGreater(response.json()["count"], 2)

    def test_audit_logins_visibility_regular_user(self):
        with self.another_user_logged_in(username=self.no_rights_user_username, password=self.no_rights_user_password):
            response: Response = self.client.get(path=reverse("audit:auditsession-list"), content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["code"], "AUDIT_LOGINS_FORBIDDEN")

    def test_filter_audit_operations_by_object_type(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditlog-list"),
                data={"object_type": self.audit_log_first.audit_object.object_type},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_operations_by_object_name(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditlog-list"),
                data={"object_name": self.audit_log_first.audit_object.object_name},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_operations_by_operation_type(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditlog-list"),
                data={"operation_type": self.audit_log_first.operation_type},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_operations_by_operation_name(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditlog-list"),
                data={"operation_name": self.audit_log_first.operation_name},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_operations_by_operation_date(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditlog-list"),
                data={"operation_date": self.date_first_filter},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_operations_by_username(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditlog-list"),
                data={"username": self.audit_log_first.user.username},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_logins_by_username(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditsession-list"),
                data={"username": self.audit_session_second.user.username},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_logins_by_login_result(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditsession-list"),
                data={"login_result": self.audit_session_second.login_result},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_audit_logins_by_login_date(self):
        with self.another_user_logged_in(username="admin", password="admin"):
            response: Response = self.client.get(
                path=reverse("audit:auditsession-list"),
                data={"login_date": self.date_second_filter},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
