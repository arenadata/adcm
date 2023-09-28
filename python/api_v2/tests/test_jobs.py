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

from cm.models import (
    ADCM,
    Action,
    ActionType,
    JobLog,
    JobStatus,
    LogStorage,
    SubAction,
    TaskLog,
)
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from adcm.tests.base import BaseTestCase


class TestJob(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )
        self.task = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now(),
            action=self.action,
        )
        self.job_1 = JobLog.objects.create(
            status=JobStatus.CREATED,
            start_date=timezone.now(),
            finish_date=timezone.now() + timedelta(days=1),
        )
        self.job_2 = JobLog.objects.create(
            status=JobStatus.RUNNING,
            start_date=timezone.now() + timedelta(days=1),
            finish_date=timezone.now() + timedelta(days=2),
            action=self.action,
            task=self.task,
            pid=9999,
            sub_action=SubAction.objects.create(
                action=self.action,
                allow_to_terminate=True,
            ),
        )
        self.log_1 = LogStorage.objects.create(
            job=self.job_1,
            name="ansible",
            type="stderr",
            format="txt",
        )

    def test_job_list_success(self):
        response: Response = self.client.get(path=reverse(viewname="v2:joblog-list"))
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_job_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:joblog-detail", kwargs={"pk": self.job_2.pk}),
        )
        self.assertEqual(response.data["id"], self.job_2.pk)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_job_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:joblog-detail", kwargs={"pk": self.job_2.pk + 10}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_job_log_list_success(self):
        response: Response = self.client.get(path=reverse(viewname="v2:log-list", kwargs={"job_pk": self.job_1.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_job_log_download_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:log-download", kwargs={"job_pk": self.job_1.pk, "log_pk": self.log_1.pk})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_job_log_not_found_download_fail(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:log-download", kwargs={"job_pk": self.job_1.pk, "log_pk": self.log_1.pk + 10})
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_job_terminate_success(self):
        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.post(
                path=reverse(viewname="v2:joblog-terminate", kwargs={"pk": self.job_2.pk}), data={}
            )
            kill_mock.assert_called()
        self.assertEqual(response.status_code, HTTP_200_OK)
