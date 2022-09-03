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
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND

from adcm.tests.base import BaseTestCase
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import ADCM, Bundle, Prototype, TaskLog
from rbac.models import User


class TestPolicy(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        self.adcm = ADCM.objects.create(prototype=prototype, name="ADCM")
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=datetime.now(),
            finish_date=datetime.now(),
        )

    def check_log(
        self,
        log: AuditLog,
        operation_name: str,
        operation_result: AuditLogOperationResult,
        user: User,
    ):
        assert log.audit_object.object_id == self.adcm.pk
        assert log.audit_object.object_name == self.adcm.name
        assert log.audit_object.object_type == AuditObjectType.ADCM
        assert not log.audit_object.is_deleted
        assert log.operation_name == operation_name
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def test_cancel(self):
        with patch("api.job.views.cancel_task"):
            self.client.put(path=f"/api/v1/task/{self.task.pk}/cancel/")

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Task cancelled",
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_cancel_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(path=f"/api/v1/task/{self.task.pk}/cancel/")

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert response.status_code == HTTP_404_NOT_FOUND
        self.check_log(
            log=log,
            operation_name="Task cancelled",
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_restart(self):
        with patch("api.job.views.restart_task"):
            self.client.put(path=f"/api/v1/task/{self.task.pk}/restart/")

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Task restarted",
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_restart_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(path=f"/api/v1/task/{self.task.pk}/restart/")

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert response.status_code == HTTP_404_NOT_FOUND
        self.check_log(
            log=log,
            operation_name="Task restarted",
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )
