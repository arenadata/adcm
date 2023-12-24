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
    Bundle,
    Cluster,
    JobLog,
    Prototype,
    TaskLog,
)
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.tests.base import BaseTestCase


class TestTaskAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        self.cluster = Cluster.objects.create(
            name="test_cluster",
            prototype=Prototype.objects.create(bundle=bundle, type="cluster"),
        )
        self.adcm = ADCM.objects.first()
        self.action = Action.objects.create(
            display_name="test_adcm_action",
            prototype=self.adcm.prototype,
            type=ActionType.JOB,
            state_available="any",
        )
        adcm_object_type = ContentType.objects.get(app_label="cm", model="adcm")
        self.task_1 = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=adcm_object_type,
            start_date=timezone.now(),
            finish_date=timezone.now() + timedelta(days=1),
            status="created",
        )
        self.task_2 = TaskLog.objects.create(
            object_id=self.adcm.pk,
            object_type=adcm_object_type,
            start_date=timezone.now() + timedelta(days=1),
            finish_date=timezone.now() + timedelta(days=2),
            action=self.action,
            status="failed",
            pid=self.task_1.pid + 1,
        )
        JobLog.objects.create(
            status="created",
            start_date=timezone.now(),
            finish_date=timezone.now() + timedelta(days=1),
            task=self.task_2,
        )

    def test_list(self):
        response: Response = self.client.get(path=reverse(viewname="v1:tasklog-list"))

        self.assertEqual(len(response.data["results"]), 2)

    def test_list_filter_action_id(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:tasklog-list"), data={"action_id": self.action.pk}
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.task_2.pk)

    def test_list_filter_pid(self):
        response: Response = self.client.get(path=reverse(viewname="v1:tasklog-list"), data={"pid": self.task_1.pid})

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["pid"], self.task_1.pid)

    def test_list_filter_status(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:tasklog-list"),
            data={"status": self.task_1.status},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["status"], self.task_1.status)

    def test_list_filter_start_date(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:tasklog-list"),
            data={"start_date": self.task_1.start_date.isoformat()},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.task_1.pk)

    def test_list_filter_finish_date(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:tasklog-list"),
            data={"finish_date": self.task_2.finish_date.isoformat()},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.task_2.pk)

    def test_list_ordering_status(self):
        response: Response = self.client.get(path=reverse(viewname="v1:tasklog-list"), data={"ordering": "status"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.task_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.task_2.pk)

    def test_list_ordering_status_reverse(self):
        response: Response = self.client.get(path=reverse(viewname="v1:tasklog-list"), data={"ordering": "-status"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.task_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.task_1.pk)

    def test_list_ordering_start_date(self):
        response: Response = self.client.get(path=reverse(viewname="v1:tasklog-list"), data={"ordering": "start_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.task_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.task_2.pk)

    def test_list_ordering_start_date_reverse(self):
        response: Response = self.client.get(path=reverse(viewname="v1:tasklog-list"), data={"ordering": "-start_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.task_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.task_1.pk)

    def test_list_ordering_finish_date(self):
        response: Response = self.client.get(path=reverse(viewname="v1:tasklog-list"), data={"ordering": "finish_date"})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.task_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.task_2.pk)

    def test_list_ordering_finish_date_reverse(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:tasklog-list"), data={"ordering": "-finish_date"}
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.task_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.task_1.pk)

    def test_retrieve(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:tasklog-detail", kwargs={"task_pk": self.task_2.pk}),
        )

        self.assertEqual(response.data["id"], self.task_2.pk)
        self.assertSetEqual(
            set(response.data["jobs"][0].keys()),
            {"display_name", "finish_date", "id", "terminatable", "start_date", "status", "url"},
        )

    def test_restart(self):
        with patch("api.job.views.restart_task"):
            response: Response = self.client.put(
                path=reverse(viewname="v1:tasklog-restart", kwargs={"task_pk": self.task_1.pk}),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_cancel(self):
        with patch("cm.models.TaskLog.cancel"):
            response: Response = self.client.put(
                path=reverse(viewname="v1:tasklog-cancel", kwargs={"task_pk": self.task_1.pk}),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_download(self):
        with patch("api.job.views.get_task_download_archive_file_handler"):
            response: Response = self.client.get(
                path=reverse(viewname="v1:tasklog-download", kwargs={"task_pk": self.task_1.pk}),
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_run(self):
        with patch("api.action.views.create", return_value=Response(status=HTTP_201_CREATED)):
            response: Response = self.client.post(
                path=reverse(
                    viewname="v1:run-task",
                    kwargs={"cluster_id": self.cluster.pk, "action_id": self.action.pk},
                ),
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
