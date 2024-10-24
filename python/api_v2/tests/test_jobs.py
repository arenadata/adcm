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
from unittest.mock import patch

from cm.models import (
    Action,
    JobLog,
    LogStorage,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from django.conf import settings
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND
import pytz

from api_v2.tests.base import BaseAPITestCase


class TestJob(BaseAPITestCase):
    TRUNCATED_LOG_MESSAGE = settings.STDOUT_STDERR_TRUNCATED_LOG_MESSAGE

    def setUp(self) -> None:
        super().setUp()

        self.cluster_1_action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")
        self.service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1)[0]
        self.service_action = Action.objects.get(prototype=self.service.prototype, name="action")
        self.host = self.add_host(provider=self.provider, fqdn="host-1", cluster=self.cluster_1)
        component_prototype = Prototype.objects.get(
            bundle=self.bundle_1, type=ObjectType.COMPONENT, name="component_1", parent=self.service.prototype
        )
        self.component = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service, prototype=component_prototype
        )
        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host, self.component)])
        self.component_action = Action.objects.get(prototype=self.component.prototype, name="action_1_comp_1")

    def test_job_list_success(self):
        self.simulate_finished_task(object_=self.cluster_1, action=self.cluster_1_action)

        response = (self.client.v2 / "jobs").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_job_retrieve_success(self):
        _, job = self.simulate_finished_task(object_=self.service, action=self.service_action)

        response = self.client.v2[job].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["id"], job.pk)

    def test_job_retrieve_not_found_fail(self):
        self.simulate_finished_task(object_=self.component, action=self.component_action)

        response = (self.client.v2 / "jobs" / self.get_non_existent_pk(JobLog)).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_job_log_list_success(self):
        _, job = self.simulate_finished_task(object_=self.cluster_1, action=self.cluster_1_action)

        response = self.client.v2[job, "logs"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_job_log_detail_success(self):
        _, job = self.simulate_finished_task(object_=self.service, action=self.service_action)
        log = job.logstorage_set.filter(type="stdout").last()

        self.long_line = "word" * 1000
        self.short_line = "word" * 4

        with self.subTest("Many lines [CUT]"):
            log.body = "\n".join("logline908" for _ in range(200_000))
            log.save(update_fields=["body"])

            response = self.client.v2[log].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            content = response.json()["content"].splitlines()
            self.assertEqual(content[0], self.TRUNCATED_LOG_MESSAGE)
            self.assertEqual(content[-1], self.TRUNCATED_LOG_MESSAGE)
            log_itself = content[1:-1]
            self.assertEqual(len(log_itself), settings.STDOUT_STDERR_LOG_CUT_LENGTH)
            self.assertTrue(all(line == "logline908" for line in log_itself))

        with self.subTest("Long lines, less than cutoff [UNCUT]"):
            log.body = (
                f"{self.long_line}\n{self.short_line}\n{self.long_line}\n"
                f"{self.short_line}\n{self.short_line}\n{self.long_line}\n"
            )
            log.save(update_fields=["body"])

            response = self.client.v2[log].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            content = response.json()["content"].splitlines()
            self.assertEqual(
                content,
                [
                    self.long_line,
                    self.short_line,
                    self.long_line,
                    self.short_line,
                    self.short_line,
                    self.long_line,
                ],
            )

        with self.subTest("Long one line [CUT]"):
            many_lines_long_message = "\n".join(
                (
                    *["logline908" for _ in range(200_000)],
                    "",
                    self.long_line,
                    self.short_line,
                    self.long_line,
                    "logline",
                )
            )
            long_one_liner_log = many_lines_long_message.replace("\n", " ")
            log.body = long_one_liner_log
            log.save(update_fields=["body"])

            response = self.client.v2[log].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            content = response.json()["content"]
            self.assertEqual(
                content,
                f"{self.TRUNCATED_LOG_MESSAGE}\n"
                f"{long_one_liner_log[: settings.STDOUT_STDERR_LOG_LINE_CUT_LENGTH]}"
                f"{self.TRUNCATED_LOG_MESSAGE}\n"
                f"{self.TRUNCATED_LOG_MESSAGE}\n",
            )

    def test_adcm_5212_retrieve_log_null_body_cut_success(self) -> None:
        _, job = self.simulate_finished_task(object_=self.component, action=self.component_action)
        log = job.logstorage_set.filter(type="stdout").last()
        log_content = "\n".join("logline908" for _ in range(200_000))

        with patch("api_v2.log_storage.serializers.extract_log_content_from_fs", return_value=log_content):
            response = self.client.v2[log].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        content = response.json()["content"].splitlines()
        self.assertEqual(content[0], self.TRUNCATED_LOG_MESSAGE)
        self.assertEqual(content[-1], self.TRUNCATED_LOG_MESSAGE)
        log_itself = content[1:-1]
        self.assertEqual(len(log_itself), settings.STDOUT_STDERR_LOG_CUT_LENGTH)
        self.assertTrue(all(line == "logline908" for line in log_itself))

    def test_job_log_download_success(self):
        _, job = self.simulate_finished_task(object_=self.cluster_1, action=self.cluster_1_action)
        log = job.logstorage_set.filter(type="stdout").last()

        response = self.client.v2[log, "download"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_adcm_5212_job_log_download_full_success(self) -> None:
        _, job = self.simulate_finished_task(object_=self.service, action=self.service_action)
        log = job.logstorage_set.filter(type="stdout").last()
        body = "\n".join("logline908" for _ in range(200_000))
        log.body = body
        log.save(update_fields=["body"])

        response = self.client.v2[log, "download"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

        content = response.content.decode("utf-8")
        self.assertNotIn(self.TRUNCATED_LOG_MESSAGE, content)
        self.assertEqual(body, content)

    def test_job_log_not_found_download_fail(self):
        _, job = self.simulate_finished_task(object_=self.component, action=self.component_action)

        response = self.client.v2[job, "logs", self.get_non_existent_pk(LogStorage), "download"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_job_terminate_success(self):
        _, job = self.simulate_running_task(object_=self.cluster_1, action=self.cluster_1_action)

        with patch("cm.models.os.kill") as kill_mock:
            response = self.client.v2[job, "terminate"].post(data={})

        self.assertEqual(response.status_code, HTTP_200_OK)
        kill_mock.assert_called()

    def test_filtering_success(self):
        self.simulate_finished_task(object_=self.cluster_1, action=self.cluster_1_action)
        self.simulate_finished_task(object_=self.component, action=self.component_action)
        self.simulate_finished_task(object_=self.service, action=self.service_action)

        for i, job in enumerate(JobLog.objects.all()):
            job.start_date = timezone.now() - timedelta(days=3 + i)
            job.finish_date = timezone.now() - timedelta(days=i)
            if job.action == self.cluster_1_action:
                job.status = "failed"
                job.pid = 5555
            job.save()

        job = JobLog.objects.get(pid=5555)

        filters = {
            "id": (job.pk, None, 0),
            "status": (job.status, None, "broken"),
        }
        exact_items_found, partial_items_found = 1, 1
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = (self.client.v2 / "jobs").get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], exact_items_found)

                response = (self.client.v2 / "jobs").get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

                if partial_value:
                    response = (self.client.v2 / "jobs").get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], partial_items_found)

    def test_ordering_success(self):
        self.simulate_finished_task(object_=self.cluster_1, action=self.cluster_1_action)
        self.simulate_finished_task(object_=self.component, action=self.component_action)
        self.simulate_finished_task(object_=self.service, action=self.service_action)

        statuses = ["created", "failed", "running"]
        for i, job in enumerate(JobLog.objects.all()):
            job.start_date = timezone.now() - timedelta(days=3 + i)
            job.finish_date = timezone.now() - timedelta(days=i)
            job.status = statuses[i]
            job.pid = 5555 + i
            job.save()

        ordering_fields = {
            "id": "id",
            "status": "status",
            "start_date": "startTime",
            "finish_date": "endTime",
        }

        def get_response_results(response, ordering_field):
            if ordering_field in ("startTime", "endTime"):
                keyword = "startTime" if ordering_field == "startTime" else "endTime"
                return [
                    datetime.fromisoformat(item[keyword][:-1]).replace(tzinfo=pytz.UTC)
                    for item in response.json()["results"]
                ]
            return [item[ordering_field] for item in response.json()["results"]]

        for model_field, ordering_field in ordering_fields.items():
            with self.subTest(ordering_field=ordering_field):
                response = (self.client.v2 / "jobs").get(query={"ordering": ordering_field})
                self.assertListEqual(
                    get_response_results(response, ordering_field),
                    list(JobLog.objects.order_by(model_field).values_list(model_field, flat=True)),
                )

                response = (self.client.v2 / "jobs").get(query={"ordering": f"-{ordering_field}"})
                self.assertListEqual(
                    get_response_results(response, ordering_field),
                    list(JobLog.objects.order_by(f"-{model_field}").values_list(model_field, flat=True)),
                )
