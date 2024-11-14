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

from adcm.tests.base import BaseTestCase
from cm.models import Bundle, Cluster, ConfigHostGroup, ConfigLog, ObjectConfig, Prototype
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN

from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObjectType,
)


class TestConfigLogAudit(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.config = ObjectConfig.objects.create(current=0, previous=0)
        self.bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=self.bundle)
        self.cluster = Cluster.objects.create(prototype=prototype, config=self.config)
        config_log = ConfigLog.objects.create(obj_ref=self.config, config="{}")
        self.config.current = config_log.pk
        self.config.save(update_fields=["current"])

        self.host_group = ConfigHostGroup.objects.create(
            name="test_config_host_group",
            object_id=self.cluster.pk,
            object_type=ContentType.objects.get(app_label="cm", model="cluster"),
            config_id=self.config.pk,
        )

    def check_log(
        self,
        log: AuditLog,
        operation_name: str,
        operation_result: AuditLogOperationResult,
        user: User,
    ) -> None:
        self.assertEqual(log.audit_object.object_id, self.cluster.pk)
        self.assertEqual(log.audit_object.object_name, self.cluster.name)
        self.assertEqual(log.audit_object.object_type, AuditObjectType.CLUSTER)
        self.assertFalse(log.audit_object.is_deleted)
        self.assertEqual(log.operation_name, operation_name)
        self.assertEqual(log.operation_type, AuditLogOperationType.UPDATE)
        self.assertEqual(log.operation_result, operation_result)
        self.assertIsInstance(log.operation_time, datetime)
        self.assertEqual(log.user.username, user.username)
        self.assertEqual(log.object_changes, {})

    def test_create(self):
        self.client.post(
            path=reverse(viewname="v1:config-log-list"),
            data={"obj_ref": self.config.pk, "config": "{}"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Cluster configuration updated",
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_create_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=reverse(viewname="v1:config-log-list"),
                data={"obj_ref": self.config.pk, "config": "{}"},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_name="Cluster configuration updated",
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )

    def test_create_via_config_host_group(self):
        self.client.post(
            path=f"/api/v1/group-config/{self.host_group.pk}/" f"config/{self.config.pk}/config-log/",
            data={"obj_ref": self.config.pk, "config": "{}"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log(
            log=log,
            operation_name="Cluster configuration group updated",
            operation_result=AuditLogOperationResult.SUCCESS,
            user=self.test_user,
        )

    def test_create_via_config_host_group_denied(self):
        with self.no_rights_user_logged_in:
            response: Response = self.client.post(
                path=f"/api/v1/group-config/{self.host_group.pk}/" f"config/{self.config.pk}/config-log/",
                data={"obj_ref": self.config.pk, "config": "{}"},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_log(
            log=log,
            operation_name="Cluster configuration group updated",
            operation_result=AuditLogOperationResult.DENIED,
            user=self.no_rights_user,
        )
