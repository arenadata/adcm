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
    TaskLog,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from api_v2.tests.base import BaseAPITestCase


class TestJob(BaseAPITestCase):
    TRUNCATED_LOG_MESSAGE = settings.STDOUT_STDERR_TRUNCATED_LOG_MESSAGE

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
            task=self.task,
            pid=9999,
            allow_to_terminate=True,
        )
        self.log_1 = LogStorage.objects.create(
            job=self.job_1,
            name="ansible",
            type="stderr",
            format="txt",
        )

        self.job_with_logs = JobLog.objects.create(
            status=JobStatus.FAILED,
            start_date=timezone.now() - timedelta(hours=2),
            finish_date=timezone.now(),
        )
        self.word_10_symbols = "logline908"
        self.ansible_stdout_many_lines = LogStorage.objects.create(
            job=self.job_with_logs,
            name="ansible",
            type="stdout",
            format="txt",
            body="\n".join(self.word_10_symbols for _ in range(200_000)),
        )
        self.long_line = "word" * 1000
        self.short_line = "word" * 4
        self.ansible_stderr_long_lines = LogStorage.objects.create(
            job=self.job_with_logs,
            name="ansible",
            type="stderr",
            format="txt",
            body=f"{self.long_line}\n{self.short_line}\n{self.long_line}\n"
            f"{self.short_line}\n{self.short_line}\n{self.long_line}\n",
        )
        many_lines_long_message = "\n".join(
            (
                *[self.word_10_symbols for _ in range(200_000)],
                "",
                self.long_line,
                self.short_line,
                self.long_line,
                "logline",
            )
        )
        self.custom_log_long_and_many_lines = LogStorage.objects.create(
            job=self.job_with_logs,
            name="anythingelse",
            type="custom",
            format="txt",
            body=many_lines_long_message,
        )
        self.another_stdout_long_and_many_lines = LogStorage.objects.create(
            job=self.job_with_logs,
            name="anotherone",
            type="stdout",
            format="txt",
            body=many_lines_long_message,
        )
        self.long_one_liner_log = LogStorage.objects.create(
            job=self.job_with_logs,
            name="anotherone",
            type="stderr",
            format="txt",
            body=many_lines_long_message.replace("\n", " "),
        )

    def test_job_list_success(self):
        response: Response = (self.client.v2 / "jobs").get()

        self.assertEqual(len(response.data["results"]), 3)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_job_retrieve_success(self):
        response: Response = self.client.v2[self.job_2].get()

        self.assertEqual(response.data["id"], self.job_2.pk)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_job_retrieve_not_found_fail(self):
        response: Response = (self.client.v2 / "jobs" / self.get_non_existent_pk(JobLog)).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_job_log_list_success(self):
        response: Response = self.client.v2[self.job_1, "logs"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_job_log_detail_success(self):
        expected_truncated_line = (
            f"{self.long_line[:settings.STDOUT_STDERR_LOG_LINE_CUT_LENGTH]}{self.TRUNCATED_LOG_MESSAGE}"
        )

        with self.subTest("Many lines [CUT]"):
            response = self.client.v2[self.ansible_stdout_many_lines].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            log = response.json()["content"].splitlines()
            self.assertEqual(log[0], self.TRUNCATED_LOG_MESSAGE)
            self.assertEqual(log[-1], self.TRUNCATED_LOG_MESSAGE)
            log_itself = log[1:-1]
            self.assertEqual(len(log_itself), settings.STDOUT_STDERR_LOG_CUT_LENGTH)
            self.assertTrue(all(line == self.word_10_symbols for line in log_itself))

        with self.subTest("Long lines, less than cutoff [UNCUT]"):
            response = self.client.v2[self.ansible_stderr_long_lines].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            log = response.json()["content"].splitlines()
            self.assertEqual(
                log,
                [
                    self.long_line,
                    self.short_line,
                    self.long_line,
                    self.short_line,
                    self.short_line,
                    self.long_line,
                ],
            )

        with self.subTest("Custom log [UNCUT]"):
            response = self.client.v2[self.custom_log_long_and_many_lines].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            log = response.json()["content"]
            self.assertEqual(log, self.custom_log_long_and_many_lines.body)

        with self.subTest("Long both ways non-ansible stdout [CUT]"):
            response = self.client.v2[self.another_stdout_long_and_many_lines].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            log = response.json()["content"].splitlines()
            self.assertEqual(log[0], self.TRUNCATED_LOG_MESSAGE)
            self.assertEqual(log[-1], self.TRUNCATED_LOG_MESSAGE)
            expected_last_lines = [
                "",
                expected_truncated_line,
                self.short_line,
                expected_truncated_line,
                "logline",
            ]
            self.assertEqual(log[-6:-1], expected_last_lines)
            main_log = log[1:-6]
            self.assertEqual(len(main_log), settings.STDOUT_STDERR_LOG_CUT_LENGTH - 5)
            self.assertTrue(all(line == self.word_10_symbols for line in main_log))

        with self.subTest("Long one line [CUT]"):
            response = self.client.v2[self.long_one_liner_log].get()
            self.assertEqual(response.status_code, HTTP_200_OK)
            log = response.json()["content"]
            self.assertEqual(
                log,
                f"{self.TRUNCATED_LOG_MESSAGE}\n"
                f"{self.long_one_liner_log.body[: settings.STDOUT_STDERR_LOG_LINE_CUT_LENGTH]}"
                f"{self.TRUNCATED_LOG_MESSAGE}\n"
                f"{self.TRUNCATED_LOG_MESSAGE}\n",
            )

    def test_adcm_5212_retrieve_log_null_body_cut_success(self) -> None:
        log_content = self.ansible_stdout_many_lines.body
        self.ansible_stdout_many_lines.body = None
        self.ansible_stdout_many_lines.save(update_fields=["body"])

        with patch("api_v2.log_storage.serializers.extract_log_content_from_fs", return_value=log_content):
            response = self.client.v2[self.ansible_stdout_many_lines].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        log = response.json()["content"].splitlines()
        self.assertEqual(log[0], self.TRUNCATED_LOG_MESSAGE)
        self.assertEqual(log[-1], self.TRUNCATED_LOG_MESSAGE)
        log_itself = log[1:-1]
        self.assertEqual(len(log_itself), settings.STDOUT_STDERR_LOG_CUT_LENGTH)
        self.assertTrue(all(line == self.word_10_symbols for line in log_itself))

    def test_job_log_download_success(self):
        response: Response = self.client.v2[self.log_1, "download"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_adcm_5212_job_log_download_full_success(self) -> None:
        response: HttpResponse = self.client.v2[self.ansible_stdout_many_lines, "download"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)

        log = response.content.decode("utf-8")
        self.assertNotIn(self.TRUNCATED_LOG_MESSAGE, log)
        self.assertEqual(self.ansible_stdout_many_lines.body, log)

    def test_job_log_not_found_download_fail(self):
        response: Response = self.client.v2[self.job_1, "logs", self.get_non_existent_pk(LogStorage), "download"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_job_terminate_success(self):
        with patch("cm.models.os.kill") as kill_mock:
            response: Response = self.client.v2[self.job_2, "terminate"].post(data={})

        self.assertEqual(response.status_code, HTTP_200_OK)
        kill_mock.assert_called()
