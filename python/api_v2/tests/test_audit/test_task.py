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

from datetime import timedelta
from unittest.mock import patch

from cm.models import ADCM, Action, ActionType, JobLog, JobStatus, SubAction, TaskLog
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from api_v2.tests.base import BaseAPITestCase


class TestTaskAudit(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )
        self.task_for_job = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.action,
        )
        self.job = JobLog.objects.create(
            status=JobStatus.RUNNING,
            start_date=timezone.now() + timedelta(days=1),
            finish_date=timezone.now() + timedelta(days=2),
            action=self.action,
            task=self.task_for_job,
            pid=9999,
            sub_action=SubAction.objects.create(
                action=self.action,
                allow_to_terminate=True,
            ),
        )
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )

    def test_job_terminate_success(self):
        with patch("cm.models.os.kill"):
            response = self.client.post(
                path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": self.job.pk}), data={}
            )
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.check_last_audit_record(
                operation_name="Job terminated",
                operation_type="update",
                operation_result="success",
                audit_object__object_id=1,
                audit_object__object_name="ADCM",
                audit_object__object_type="adcm",
                audit_object__is_deleted=False,
                object_changes={},
                user__username="admin",
            )

    def test_job_terminate_not_found_fail(self):
        with patch("cm.models.os.kill"):
            response = self.client.post(path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": 100}), data={})
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name="Job terminated",
                operation_type="update",
                operation_result="fail",
                object_changes={},
                user__username="admin",
            )

    def test_job_terminate_denied(self):
        self.client.login(**self.test_user_credentials)
        with patch("cm.models.os.kill"):
            response = self.client.post(
                path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": self.job.pk}), data={}
            )
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name="Job terminated",
                operation_type="update",
                operation_result="denied",
                object_changes={},
                user__username=self.test_user.username,
            )

    def test_task_cancel_success(self):
        with patch("cm.models.TaskLog.cancel"):
            response = self.client.post(path=reverse(viewname="v2:tasklog-terminate", kwargs={"pk": self.task.pk}))
            self.assertEqual(response.status_code, HTTP_200_OK)

            self.check_last_audit_record(
                operation_name="Task cancelled",
                operation_type="update",
                operation_result="success",
                audit_object__object_id=1,
                audit_object__object_name="ADCM",
                audit_object__object_type="adcm",
                audit_object__is_deleted=False,
                object_changes={},
                user__username="admin",
            )

    def test_task_cancel_not_found_fail(self):
        with patch("cm.models.TaskLog.cancel"):
            response = self.client.post(path=reverse(viewname="v2:tasklog-terminate", kwargs={"pk": 1000}))
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name="Task cancelled",
                operation_type="update",
                operation_result="fail",
                object_changes={},
                user__username="admin",
            )

    def test_task_cancel_denied(self):
        self.client.login(**self.test_user_credentials)
        with patch("cm.models.TaskLog.cancel"):
            response = self.client.post(path=reverse(viewname="v2:tasklog-terminate", kwargs={"pk": self.task.pk}))
            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            self.check_last_audit_record(
                operation_name="Task cancelled",
                operation_type="update",
                operation_result="denied",
                object_changes={},
                user__username=self.test_user.username,
            )
