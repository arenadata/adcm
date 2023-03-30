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

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from cm.models import JobLog, LogStorage
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase


class TestTaskAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.job = JobLog.objects.create(
            status="created",
            start_date=datetime.now(tz=ZoneInfo(settings.TIME_ZONE)),
            finish_date=datetime.now(tz=ZoneInfo(settings.TIME_ZONE)) + timedelta(days=1),
        )
        self.log_storage_1 = LogStorage.objects.create(
            name="log_storage_1",
            job=self.job,
            type="custom",
            format="txt",
        )
        self.log_storage_2 = LogStorage.objects.create(
            name="log_storage_2",
            job=self.job,
            type="check",
            format="json",
        )

    def test_list(self):
        response: Response = self.client.get(
            path=reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
        )

        self.assertEqual(len(response.data["results"]), 2)

    def test_list_filter_name(self):
        response: Response = self.client.get(
            reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
            {"name": self.log_storage_1.name},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.log_storage_1.pk)

    def test_list_filter_type(self):
        response: Response = self.client.get(
            reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
            {"type": self.log_storage_2.type},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.log_storage_2.pk)

    def test_list_filter_format(self):
        response: Response = self.client.get(
            reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
            {"format": self.log_storage_2.format},
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.log_storage_2.pk)

    def test_list_ordering_id(self):
        response: Response = self.client.get(
            reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
            {"ordering": "id"},
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.log_storage_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.log_storage_2.pk)

    def test_list_ordering_id_reverse(self):
        response: Response = self.client.get(
            reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
            {"ordering": "-id"},
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.log_storage_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.log_storage_1.pk)

    def test_list_ordering_name(self):
        response: Response = self.client.get(
            reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
            {"ordering": "name"},
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.log_storage_1.pk)
        self.assertEqual(response.data["results"][1]["id"], self.log_storage_2.pk)

    def test_list_ordering_name_reverse(self):
        response: Response = self.client.get(
            reverse("joblog-list", kwargs={"job_pk": self.job.pk}),
            {"ordering": "-name"},
        )

        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.log_storage_2.pk)
        self.assertEqual(response.data["results"][1]["id"], self.log_storage_1.pk)

    def test_retrieve(self):
        response: Response = self.client.get(
            reverse("joblog-detail", kwargs={"job_pk": self.job.pk, "log_pk": self.log_storage_1.pk}),
        )

        self.assertEqual(response.data["id"], self.log_storage_1.pk)

    def test_download(self):
        response: Response = self.client.get(
            reverse("joblog-download", kwargs={"job_pk": self.job.pk, "log_pk": self.log_storage_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
