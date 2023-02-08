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

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import ADCM, Bundle, Prototype, TaskLog
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND

from adcm.tests.base import BaseTestCase


class TestTaskAudit(BaseTestCase):
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
        self.task_restarted_str = "Task restarted"

    def check_log(
        self,
        log: AuditLog,
        operation_name: str,
        operation_result: AuditLogOperationResult,
        user: User,
        obj: ADCM | None,
    ):
        if obj:
            self.assertEqual(log.audit_object.object_id, obj.pk)
            self.assertEqual(log.audit_object.object_name, obj.name)
            self.assertEqual(log.audit_object.object_type, AuditObjectType.ADCM)
            self.assertFalse(log.audit_object.is_deleted)
        else:
            self.assertFalse(obj)

        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.pk, user.pk)
        self.assertEqual(log.object_changes, {})

    def test_cancel(self):
        with patch("api.job.views.cancel_task"):
            self.client.put(path=reverse("tasklog-cancel", kwargs={"task_pk": self.task.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Task cancelled",
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            obj=self.adcm,
        )

    def test_cancel_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(
                path=reverse("tasklog-cancel", kwargs={"task_pk": self.task.pk}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            operation_name="Task cancelled",
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
            obj=self.adcm,
        )

    def test_restart(self):
        with patch("api.job.views.restart_task"):
            self.client.put(path=reverse("tasklog-restart", kwargs={"task_pk": self.task.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name=self.task_restarted_str,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
            obj=self.adcm,
        )

    def test_restart_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.put(
                path=reverse("tasklog-restart", kwargs={"task_pk": self.task.pk}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            operation_name=self.task_restarted_str,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
            obj=self.adcm,
        )

    def test_restart_failed(self):
        task_pks = TaskLog.objects.all().values_list("pk", flat=True).order_by("-pk")
        with patch("api.job.views.restart_task"):
            response: Response = self.client.put(
                path=reverse("tasklog-restart", kwargs={"task_pk": task_pks[0] + 1}),
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
        self.check_log(
            log=log,
            operation_name=self.task_restarted_str,
            operation_result=AuditLogOperationResult.FAIL,
            user=self.test_user,
            obj=None,
        )
