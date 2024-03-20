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


from audit.models import AuditLogOperationType, AuditObject
from cm.models import Bundle, Prototype
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestBundleAudit(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")
        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_audit_upload_success(self):
        new_bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "cluster_one")

        with open(settings.DOWNLOAD_DIR / new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = self.client.post(
                path=reverse(viewname="v2:bundle-list"),
                data={"file": f},
                format="multipart",
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.check_last_audit_record(
            operation_name="Bundle uploaded",
            operation_result="success",
            operation_type=AuditLogOperationType.CREATE,
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_audit_upload_fail(self):
        self.add_bundle(source_dir=self.test_bundles_dir / "cluster_one")
        new_bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "cluster_one")

        with open(settings.DOWNLOAD_DIR / new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = self.client.post(
                path=reverse(viewname="v2:bundle-list"),
                data={"file": f},
                format="multipart",
            )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.check_last_audit_record(
            operation_name="Bundle uploaded",
            operation_result="fail",
            operation_type=AuditLogOperationType.CREATE,
            audit_object__isnull=True,
            user__username="admin",
        )

    def test_audit_upload_denied(self):
        new_bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "cluster_one")
        self.client.login(**self.test_user_credentials)

        with open(settings.DOWNLOAD_DIR / new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = self.client.post(
                path=reverse(viewname="v2:bundle-list"),
                data={"file": f},
                format="multipart",
            )

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Bundle uploaded",
            operation_result="denied",
            operation_type=AuditLogOperationType.CREATE,
            audit_object__isnull=True,
            user__username="test_user_username",
        )

    def test_audit_delete_success(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_one")

        # audit object should exist before successful DELETE request
        # to have `is_deleted` updated
        # for now we've agreed that's ok tradeoff
        AuditObject.objects.get_or_create(
            object_id=bundle.pk,
            object_name=bundle.name,
            object_type="bundle",
            is_deleted=False,
        )

        response = self.client.delete(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": bundle.pk}))
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.check_last_audit_record(
            operation_name="Bundle deleted",
            operation_type="delete",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=bundle, is_deleted=True),
            user__username="admin",
        )

    def test_audit_delete_non_existent_fail(self):
        response = self.client.delete(
            path=reverse(viewname="v2:bundle-detail", kwargs={"pk": self.get_non_existent_pk(Bundle)})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Bundle deleted",
            operation_type="delete",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )

    def test_audit_delete_denied(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_one")
        self.client.login(**self.test_user_credentials)

        response = self.client.delete(path=reverse(viewname="v2:bundle-detail", kwargs={"pk": bundle.pk}))

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        self.check_last_audit_record(
            operation_name="Bundle deleted",
            operation_type="delete",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=bundle),
            user__username=self.test_user_credentials["username"],
        )

    def test_audit_accept_license_success(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_one")
        bundle_prototype = Prototype.objects.get(bundle=bundle, type="cluster")

        response = self.client.post(
            path=reverse(viewname="v2:prototype-accept-license", kwargs={"pk": bundle_prototype.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.check_last_audit_record(
            operation_name="Bundle license accepted",
            operation_type="update",
            operation_result="success",
            **self.prepare_audit_object_arguments(expected_object=bundle),
            user__username="admin",
        )

    def test_audit_accept_license_denied(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_one")
        bundle_prototype = Prototype.objects.get(bundle=bundle, type="cluster")
        self.client.login(**self.test_user_credentials)

        response = self.client.post(
            path=reverse(viewname="v2:prototype-accept-license", kwargs={"pk": bundle_prototype.pk})
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        self.check_last_audit_record(
            operation_name="Bundle license accepted",
            operation_type="update",
            operation_result="denied",
            **self.prepare_audit_object_arguments(expected_object=bundle),
            user__username="test_user_username",
        )

    def test_audit_accept_license_fail(self):
        response = self.client.post(path=reverse(viewname="v2:prototype-accept-license", kwargs={"pk": 1000}))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        self.check_last_audit_record(
            operation_name="Bundle license accepted",
            operation_type="update",
            operation_result="fail",
            **self.prepare_audit_object_arguments(expected_object=None),
            user__username="admin",
        )
