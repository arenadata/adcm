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
from cm.models import ADCM, Action, Bundle, ConfigLog, ObjectConfig, Prototype
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestComponent(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        config = ObjectConfig.objects.create(current=1, previous=0)
        ConfigLog.objects.create(
            obj_ref=config, config="{}", attr={"ldap_integration": {"active": True}}
        )
        self.adcm = ADCM.objects.create(prototype=self.prototype, name="ADCM", config=config)

    def check_adcm_updated(
        self, log: AuditLog, operation_name: str, operation_result: str, user: User
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

    def test_update_and_restore(self):
        self.client.post(
            path=reverse("config-history", kwargs={"adcm_id": self.adcm.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_adcm_updated(
            log=log,
            operation_name="ADCM configuration updated",
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

        res: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"adcm_id": self.adcm.pk, "version": 1},
            ),
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_200_OK
        self.check_adcm_updated(
            log=log,
            operation_name="ADCM configuration updated",
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )

    def test_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.post(
                path=reverse("config-history", kwargs={"adcm_id": self.adcm.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_adcm_updated(
            log=log,
            operation_name="ADCM configuration updated",
            operation_result=AuditLogOperationResult.Denied,
            user=self.no_rights_user,
        )

    def test_action(self):
        action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.prototype,
            type="job",
            state_available="any",
        )

        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            self.client.post(
                path=reverse("run-task", kwargs={"adcm_id": self.adcm.pk, "action_id": action.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_adcm_updated(
            log=log,
            operation_name=f"{action.display_name} action launched",
            operation_result=AuditLogOperationResult.Success,
            user=self.test_user,
        )
