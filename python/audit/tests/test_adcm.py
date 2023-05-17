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
from cm.models import ADCM, Action, ConfigLog, TaskLog
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestADCMAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.first()
        self.config_log = ConfigLog.objects.get(obj_ref=self.adcm.config)
        self.config_log.attr["ldap_integration"]["active"] = True
        self.config_log.save(update_fields=["attr"])
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type="job",
            state_available="any",
        )
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=datetime.now(tz=ZoneInfo(settings.TIME_ZONE)),
            finish_date=datetime.now(tz=ZoneInfo(settings.TIME_ZONE)),
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
        self.config_log.config["ldap_integration"]["ldap_uri"] = "test_ldap_uri"
        self.config_log.config["ldap_integration"]["ldap_user"] = "test_ldap_user"
        self.config_log.config["ldap_integration"]["ldap_password"] = "test_ldap_password"
        self.config_log.config["ldap_integration"]["user_search_base"] = "test_ldap_user_search_base"
        self.config_log.config["global"]["adcm_url"] = "https://test_ldap.url"
        self.config_log.config["auth_policy"]["min_password_length"] = 6
        self.config_log.save(update_fields=["config"])

        self.client.post(
            path=reverse(viewname="v1:config-history", kwargs={"adcm_pk": self.adcm.pk}),
            data={"config": self.config_log.config, "attr": self.config_log.attr},
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
                viewname="v1:config-history-version-restore",
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
                path=reverse(viewname="v1:config-history", kwargs={"adcm_pk": self.adcm.pk}),
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
