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
from cm.models import Bundle, Cluster, ConfigLog, ObjectConfig, Prototype
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestGroupConfig(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.config = ObjectConfig.objects.create(current=1, previous=1)
        ConfigLog.objects.create(obj_ref=self.config, config="{}")
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        self.cluster = Cluster.objects.create(prototype=prototype, config=self.config)
        self.name = "test_group_config"

    def create_group_config(self) -> Response:
        return self.client.post(
            path=reverse("group-config-list"),
            data={
                "name": self.name,
                "object_id": self.cluster.pk,
                "object_type": "cluster",
                "config_id": self.config.id,
            },
        )

    def test_create(self):
        res: Response = self.create_group_config()

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == self.name
        assert log.audit_object.object_type == AuditObjectType.Cluster.label
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Cluster group config created"
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create_config_log(self):
        group_config_data: Response = self.create_group_config()
        res: Response = self.client.post(
            path=f"/api/v1/group-config/{group_config_data.data['id']}/"
            f"config/{self.config.pk}/config-log/",
            data={"obj_ref": self.config.pk, "config": "{}"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == str(ConfigLog.objects.get(pk=res.data["id"]))
        assert log.audit_object.object_type == AuditObjectType.Cluster.label
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Cluster config log created"
        assert log.operation_type == AuditLogOperationType.Create.value
        assert log.operation_result == AuditLogOperationResult.Success.value
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
