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
from cm.models import Bundle, Cluster, ConfigLog, GroupConfig, ObjectConfig, Prototype
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestConfigLog(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.config = ObjectConfig.objects.create(current=1, previous=1)
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        cluster = Cluster.objects.create(prototype=prototype, config=self.config)
        ConfigLog.objects.create(obj_ref=self.config, config="{}")
        self.group_config = GroupConfig.objects.create(
            name="test_group_config",
            object_id=cluster.pk,
            object_type=ContentType.objects.get(app_label="cm", model="cluster"),
            config_id=self.config.pk,
        )

    def check_config_log(self, res: Response, log: AuditLog):
        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == str(ConfigLog.objects.get(pk=res.data["id"]))
        assert log.audit_object.object_type == AuditObjectType.Cluster
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Cluster config log updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_create(self):
        res: Response = self.client.post(
            path=reverse("config-log-list"),
            data={"obj_ref": self.config.pk, "config": "{}"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_config_log(res, log)

    def test_create_via_group_config(self):
        res: Response = self.client.post(
            path=f"/api/v1/group-config/{self.group_config.pk}/"
            f"config/{self.config.pk}/config-log/",
            data={"obj_ref": self.config.pk, "config": "{}"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_config_log(res, log)
