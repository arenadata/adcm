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
from cm.models import Bundle, Cluster, Prototype
from django.urls import reverse
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from adcm.tests.base import BaseTestCase


class TestBundle(BaseTestCase):
    # pylint: disable=too-many-public-methods

    def setUp(self) -> None:
        super().setUp()

        bundle_name = "test_bundle"
        self.bundle = Bundle.objects.create(
            name=bundle_name,
            license_path="test_bundle_license_path",
            license="unaccepted",
        )
        Prototype.objects.create(bundle=self.bundle, type="cluster", name=bundle_name)

    @staticmethod
    def check_log_upload(
        log: AuditLog, operation_result: AuditLogOperationResult, user: User
    ) -> None:
        assert not log.audit_object
        assert log.operation_name == "Bundle uploaded"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    @staticmethod
    def check_log_load_no_obj(
        log: AuditLog, operation_result: AuditLogOperationResult, user: User
    ) -> None:
        assert not log.audit_object
        assert log.operation_name == "Bundle loaded"
        assert log.operation_type == AuditLogOperationType.Create
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == user.pk
        assert isinstance(log.object_changes, dict)

    def check_log_denied(
        self, log: AuditLog, operation_name: str, operation_type: AuditLogOperationType
    ) -> None:
        assert log.audit_object.object_id == self.bundle.pk
        assert log.audit_object.object_name == self.bundle.name
        assert log.audit_object.object_type == AuditObjectType.Bundle
        assert not log.audit_object.is_deleted
        assert log.operation_name == operation_name
        assert log.operation_type == operation_type
        assert log.operation_result == AuditLogOperationResult.Denied
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.no_rights_user.pk
        assert isinstance(log.object_changes, dict)

    def check_log_deleted(self, log: AuditLog, operation_result: AuditLogOperationResult):
        assert log.audit_object.object_id == self.bundle.pk
        assert log.audit_object.object_name == self.bundle.name
        assert log.audit_object.object_type == AuditObjectType.Bundle
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Bundle deleted"
        assert log.operation_type == AuditLogOperationType.Delete
        assert log.operation_result == operation_result
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def load_bundle(self) -> Response:
        return self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": self.test_bundle_filename},
        )

    def upload_bundle(self) -> None:
        with open(self.test_bundle_path, encoding="utf-8") as f:
            self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

    def upload_bundle_and_check(self) -> Response:
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

        self.check_log_upload(
            log=log, operation_result=AuditLogOperationResult.Success, user=self.test_user
        )

    def test_upload_fail(self):
        with open(self.test_bundle_path, encoding="utf-8") as f:
            self.client.post(
                path=reverse("upload-bundle"),
                data={"no_file": f},
            )

        log: AuditLog = AuditLog.objects.first()

        self.check_log_upload(
            log=log, operation_result=AuditLogOperationResult.Fail, user=self.test_user
        )

    def test_upload_denied(self):
        with open(self.test_bundle_path, encoding="utf-8") as f:
            with self.no_rights_user_logged_in:
                res: Response = self.client.post(
                    path=reverse("upload-bundle"),
                    data={"no_file": f},
                )

        log: AuditLog = AuditLog.objects.first()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_upload(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )

    def test_load(self):
        self.upload_bundle_and_check()
        self.load_bundle()

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_load_no_obj(
            log=log, operation_result=AuditLogOperationResult.Fail, user=self.test_user
        )

    def test_load_failed(self):
        self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": "something wrong"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_load_no_obj(
            log=log, operation_result=AuditLogOperationResult.Fail, user=self.test_user
        )

        res: Response = self.client.post(
            path=reverse("load-bundle"),
            data={"bundle": "something wrong"},
        )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.assertEqual(res.status_code, HTTP_400_BAD_REQUEST)
        self.check_log_load_no_obj(
            log=log, operation_result=AuditLogOperationResult.Fail, user=self.test_user
        )

    def test_load_denied(self):
        self.upload_bundle_and_check()

        with self.no_rights_user_logged_in:
            res: Response = self.load_bundle()

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_load_no_obj(
            log=log, operation_result=AuditLogOperationResult.Denied, user=self.no_rights_user
        )

    def test_load_and_delete(self):
        res: Response = self.upload_bundle_and_check()

        Bundle.objects.get(pk=res.data["id"]).delete()
        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.is_deleted

    def test_update(self):
        with patch("api.stack.views.update_bundle"):
            self.client.put(
                path=reverse("bundle-update", kwargs={"bundle_id": self.bundle.pk}),
                data={"name": "new_bundle_name"},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.bundle.pk
        assert log.audit_object.object_name == self.bundle.name
        assert log.audit_object.object_type == AuditObjectType.Bundle
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Bundle updated"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_update_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.put(
                path=reverse("bundle-update", kwargs={"bundle_id": self.bundle.pk}),
                data={"name": "new_bundle_name"},
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_denied(
            log=log, operation_name="Bundle updated", operation_type=AuditLogOperationType.Update
        )

    def test_license_accepted(self):
        self.client.put(path=reverse("accept-license", kwargs={"bundle_id": self.bundle.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert log.audit_object.object_id == self.bundle.pk
        assert log.audit_object.object_name == self.bundle.name
        assert log.audit_object.object_type == AuditObjectType.Bundle
        assert not log.audit_object.is_deleted
        assert log.operation_name == "Bundle license accepted"
        assert log.operation_type == AuditLogOperationType.Update
        assert log.operation_result == AuditLogOperationResult.Success
        assert isinstance(log.operation_time, datetime)
        assert log.user.pk == self.test_user.pk
        assert isinstance(log.object_changes, dict)

    def test_license_accepted_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.put(
                path=reverse("accept-license", kwargs={"bundle_id": self.bundle.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_denied(
            log=log,
            operation_name="Bundle license accepted",
            operation_type=AuditLogOperationType.Update,
        )

    def test_delete(self):
        with patch("api.stack.views.delete_bundle"):
            self.client.delete(path=reverse("bundle-details", kwargs={"bundle_id": self.bundle.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_deleted(log=log, operation_result=AuditLogOperationResult.Success)

    def test_delete_denied(self):
        with self.no_rights_user_logged_in:
            res: Response = self.client.delete(
                path=reverse("bundle-details", kwargs={"bundle_id": self.bundle.pk})
            )

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        assert res.status_code == HTTP_403_FORBIDDEN
        self.check_log_denied(
            log=log, operation_name="Bundle deleted", operation_type=AuditLogOperationType.Delete
        )

    def test_delete_failed(self):
        Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="cluster"),
            name="test_cluster",
        )
        self.client.delete(path=reverse("bundle-details", kwargs={"bundle_id": self.bundle.pk}))

        log: AuditLog = AuditLog.objects.order_by("operation_time").last()

        self.check_log_deleted(log=log, operation_result=AuditLogOperationResult.Fail)
