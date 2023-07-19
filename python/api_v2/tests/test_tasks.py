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

from cm.job import get_selector
from cm.models import ADCM, Action, ActionType, JobLog, TaskLog
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from adcm.tests.base import BaseTestCase


class TestTask(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )
        self.task_1 = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now() + timedelta(days=1),
            action=self.action,
        )
        self.task_2 = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=timezone.now(),
            finish_date=timezone.now() + timedelta(days=1),
            action=self.action,
            selector=get_selector(self.adcm, self.action),
        )
        self.job = JobLog.objects.create(
            status="failed",
            start_date=timezone.now() + timedelta(days=1),
            finish_date=timezone.now() + timedelta(days=2),
            action=self.action,
            task=self.task_1,
        )

    def test_task_list_success(self):
        response: Response = self.client.get(path=reverse(viewname="v2:tasklog-list"))
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_task_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:tasklog-detail", kwargs={"pk": self.task_2.pk}),
        )
        task_object = {
            "type": self.adcm.content_type.name,
            "id": self.adcm.pk,
            "name": self.adcm.name,
            "display_name": self.adcm.display_name,
        }
        self.assertEqual(response.data["id"], self.task_2.pk)
        self.assertEqual(response.data["object"], task_object)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_task_retrieve_not_found_fail(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:tasklog-detail", kwargs={"pk": self.task_2.pk + 10}),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_task_log_list_success(self):
        response: Response = self.client.get(path=reverse(viewname="v2:log-list", kwargs={"task_pk": self.task_1.pk}))
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_task_log_download_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:log-download", kwargs={"task_pk": self.task_1.pk})
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
