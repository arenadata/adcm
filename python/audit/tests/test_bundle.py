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
from cm.models import Bundle, Prototype
from django.urls import reverse
from rest_framework.response import Response

from adcm.tests.base import BaseTestCase


class TestBundle(BaseTestCase):
    def load_bundle(self):
        return self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": self.test_bundle_filename},
        )

    def upload_bundle(self):
        with open(self.test_bundle_path, encoding="utf-8") as f:
            self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

    def upload_bundle_and_check(self):
        self.upload_bundle()

        res: Response = self.load_bundle()
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == res.data["id"]
        assert log.audit_object.object_name == "hc_acl_in_service_noname"
        assert log.audit_object.object_type == AuditObjectType.Bundle
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Bundle loaded"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

        return res

    def test_upload_success(self):
        self.upload_bundle()

        log: AuditLog = AuditLog.objects.first()

        assert not log.audit_object
        assert log.operation_name == "Bundle uploaded"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_upload_fail(self):
        with open(self.test_bundle_path, encoding="utf-8") as f:
            self.client.post(
                path=reverse("upload-bundle"),
                data={"no_file": f},
            )

        log: AuditLog = AuditLog.objects.first()

        assert not log.audit_object
        assert log.operation_name == "Bundle uploaded"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_load(self):
        self.upload_bundle_and_check()
        self.load_bundle()

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert not log.audit_object
        assert log.operation_name == "Bundle loaded"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == AuditLogOperationResult.Fail
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_load_and_delete(self):
        res: Response = self.upload_bundle_and_check()

        Bundle.objects.get(pk=res.data["id"]).delete()
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.is_deleted

    def test_update(self):
        bundle_name = "test_bundle"
        bundle = Bundle.objects.create(name=bundle_name)
        Prototype.objects.create(bundle=bundle, type="cluster", name=bundle_name)

        with patch("api.stack.views.update_bundle"):
            self.client.put(
                path=f"/api/v1/stack/bundle/{bundle.pk}/update/",
                data={"name": "new_bundle_name"},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == bundle.pk
        assert log.audit_object.object_name == bundle.name
        assert log.audit_object.object_type == AuditObjectType.Bundle
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Bundle updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)
