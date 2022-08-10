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
    AuditObjectType,
)
from cm.models import ADCM, Bundle, ConfigLog, ObjectConfig, Prototype
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from adcm.tests.base import BaseTestCase


class TestComponent(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=config, config="{}")
        self.adcm = ADCM.objects.create(prototype=prototype, name="ADCM", config=config)

    def check_adcm_updated(self, log: AuditLog, operation_result: str, user: User):
        assert log.audit_object.object_id == self.adcm.pk
        assert log.audit_object.object_name == self.adcm.name
        assert log.audit_object.object_type == AuditObjectType.ADCM
        assert not log.audit_object.is_deleted
        assert log.operation_name == "ADCM configuration updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_and_restore(self):
        self.client.post(
            path=f"/api/v1/adcm/{self.adcm.pk}/config/history/",
            data={"config": {}},
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_adcm_updated(
            log=log, operation_result=AuditLogOperationResult.Success, user=self.test_user
        )

        res: Response = self.client.patch(
            path=f"/api/v1/adcm/{self.adcm.pk}/config/history/1/restore/",
            content_type="application/json",
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_200_OK
        self.check_adcm_updated(
            log=log, operation_result=AuditLogOperationResult.Success, user=self.test_user
        )

    def test_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=f"/api/v1/adcm/{self.adcm.pk}/config/history/",
                data={"config": {}},
                content_type="application/json",
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_adcm_updated(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )
