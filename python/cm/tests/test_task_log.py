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
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase
from cm.models import ADCM, ConcernType, JobLog, TaskLog
from cm.tests.utils import (
    gen_adcm,
    gen_cluster,
    gen_concern_item,
    gen_job_log,
    gen_task_log,
)


class TaskLogLockTest(BaseTestCase):
    """Tests for `cm.models.TaskLog` lock-related methods"""

    def setUp(self) -> None:
        super().setUp()

        gen_adcm()

    def test_lock_affected__lock_is_single(self):
        cluster = gen_cluster()
        task = gen_task_log(cluster)
        gen_job_log(task)
        task.lock = gen_concern_item(ConcernType.Lock)
        task.save()
        task.lock_affected([cluster])

        self.assertFalse(cluster.locked)

    def test_lock_affected(self):
        cluster = gen_cluster()
        task = gen_task_log(cluster)
        gen_job_log(task)
        task.lock_affected([cluster])

        self.assertTrue(cluster.locked)

        task.refresh_from_db()

        self.assertIsNotNone(task.lock)

    def test_unlock_affected(self):
        cluster = gen_cluster()
        task = gen_task_log(cluster)
        gen_job_log(task)
        task.lock_affected([cluster])
        task.unlock_affected()

        self.assertFalse(cluster.locked)
        self.assertIsNone(task.lock)

    @override_settings(
        RUN_DIR=settings.BASE_DIR / "python" / "cm" / "tests" / "files" / "task_log_download"
    )
    def test_download(self):
        adcm = ADCM.objects.first()
        task = TaskLog.objects.create(
            object_id=adcm.pk,
            object_type=ContentType.objects.get(app_label="cm", model="adcm"),
            start_date=datetime.now(tz=ZoneInfo("UTC")),
            finish_date=datetime.now(tz=ZoneInfo("UTC")),
        )
        JobLog.objects.create(
            task=task,
            start_date=datetime.now(tz=ZoneInfo("UTC")),
            finish_date=datetime.now(tz=ZoneInfo("UTC")),
        )
        JobLog.objects.create(
            task=task,
            start_date=datetime.now(tz=ZoneInfo("UTC")),
            finish_date=datetime.now(tz=ZoneInfo("UTC")),
        )
        JobLog.objects.create(
            task=task,
            start_date=datetime.now(tz=ZoneInfo("UTC")),
            finish_date=datetime.now(tz=ZoneInfo("UTC")),
        )
        response: Response = self.client.get(
            path=reverse("task-download", kwargs={"task_id": task.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Disposition"], 'attachment; filename="1.tar.gz"')
        self.assertEqual(response.headers["Content-Length"], "337")
