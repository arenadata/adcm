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

from adcm.tests.base import BaseTestCase


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

    def test_cancel(self):
        with patch("api.job.views.cancel_task"):
            self.client.put(path=f"/api/v1/task/{self.task.pk}/cancel/")

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.adcm.pk
        assert log.audit_object.object_name == self.adcm.name
        assert log.audit_object.object_type == AuditObjectType.ADCM
        assert not log.audit_object.is_deleted
        assert log.operation_name == "ADCM task cancelled"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_restart(self):
        with patch("api.job.views.restart_task"):
            self.client.put(path=f"/api/v1/task/{self.task.pk}/restart/")

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.adcm.pk
        assert log.audit_object.object_name == self.adcm.name
        assert log.audit_object.object_type == AuditObjectType.ADCM
        assert not log.audit_object.is_deleted
        assert log.operation_name == "ADCM task restarted"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
