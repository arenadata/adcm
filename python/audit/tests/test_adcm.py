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
from zoneinfo import ZoneInfo

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.models import ADCM, Action, Bundle, ConfigLog, ObjectConfig, Prototype, TaskLog
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestADCMAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(bundle=bundle, type="adcm")
        config = ObjectConfig.objects.create(current=0, previous=0)
        self.config_log = ConfigLog.objects.create(
            obj_ref=config,
            config="{}",
            attr={"ldap_integration": {"active": True}},
        )
        config.current = self.config_log.pk
        config.save(update_fields=["current"])

        self.adcm_name = "ADCM"
        self.adcm = ADCM.objects.create(prototype=self.prototype, name=self.adcm_name, config=config)
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.prototype,
            type="job",
            state_available="any",
        )
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=datetime.now(tz=ZoneInfo("UTC")),
            finish_date=datetime.now(tz=ZoneInfo("UTC")),
            action=self.action,
        )
        self.adcm_conf_updated_str = "ADCM configuration updated"

    def check_adcm_updated(self, log: AuditLog, operation_name: str, operation_result: str, user: User | None = None):
        if log.audit_object:
            self.assertEqual(log.audit_object.object_id, self.adcm.pk)
            self.assertEqual(log.audit_object.object_name, self.adcm.name)
            self.assertEqual(log.audit_object.object_type, AuditObjectType.ADCM)
            self.assertFalse(log.audit_object.is_deleted)
        else:
            self.assertFalse(log.audit_object)

        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)

        if log.user:
            self.assertEqual(log.user.pk, user.pk)

        self.assertEqual(log.object_changes, {})

    def test_update_and_restore(self):
        self.client.post(
            path=reverse("config-history", kwargs={"adcm_pk": self.adcm.pk}),
            data={"config": {}},
            content_type=APPLICATION_JSON,
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_adcm_updated(
            log=log,
            operation_name=self.adcm_conf_updated_str,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

        response: Response = self.client.patch(
            path=reverse(
                "config-history-version-restore",
                kwargs={"adcm_pk": self.adcm.pk, "version": self.config_log.pk},
            ),
            content_type=APPLICATION_JSON,
        )

        new_log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertNotEqual(new_log.pk, log.pk)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_adcm_updated(
            log=new_log,
            operation_name=self.adcm_conf_updated_str,
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse("config-history", kwargs={"adcm_pk": self.adcm.pk}),
                data={"config": {}},
                content_type=APPLICATION_JSON,
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_adcm_updated(
            log=log,
            operation_name=self.adcm_conf_updated_str,
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )
