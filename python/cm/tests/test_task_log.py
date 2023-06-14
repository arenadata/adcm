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


from api.job.views import (
    get_task_download_archive_file_handler,
    get_task_download_archive_name,
)
from cm.models import (
    Action,
    Bundle,
    Cluster,
    ConcernType,
    JobLog,
    LogStorage,
    Prototype,
    SubAction,
    TaskLog,
)
from cm.tests.utils import (
    gen_adcm,
    gen_cluster,
    gen_concern_item,
    gen_job_log,
    gen_task_log,
)
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from adcm.tests.base import BaseTestCase


class TaskLogLockTest(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        gen_adcm()

    def test_lock_affected__lock_is_single(self):
        cluster = gen_cluster()
        task = gen_task_log(cluster)
        gen_job_log(task)
        task.lock = gen_concern_item(ConcernType.LOCK)
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

    @override_settings(RUN_DIR=settings.BASE_DIR / "python" / "cm" / "tests" / "files" / "task_log_download")
    def test_download(self):
        bundle = Bundle.objects.create()
        cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="cluster",
                name="test_cluster_prototype",
            ),
            name="test_cluster",
        )
        action = Action.objects.create(
            display_name="test_cluster_action",
            prototype=cluster.prototype,
            type="task",
            state_available="any",
        )
        task = TaskLog.objects.create(
            task_object=cluster,
            action=action,
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )
        cluster_2 = Cluster.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="cluster",
                name="test_cluster_prototype_2",
            ),
            name="test_cluster_2",
        )
        cluster_3 = Cluster.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="cluster",
                name="test_cluster_prototype_3",
            ),
            name="test_cluster_3",
        )
        cluster_4 = Cluster.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="cluster",
                name="test_cluster_prototype_4",
            ),
            name="test_cluster_4",
        )
        cluster_5 = Cluster.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="cluster",
                name="test_cluster_prototype_5",
            ),
            name="test_cluster_5",
        )
        JobLog.objects.create(
            task=task,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            sub_action=SubAction.objects.create(
                action=Action.objects.create(
                    display_name="test_subaction_job_1",
                    prototype=cluster_2.prototype,
                    type="job",
                    state_available="any",
                ),
            ),
        )
        JobLog.objects.create(
            task=task,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            sub_action=SubAction.objects.create(
                action=Action.objects.create(
                    display_name="test_subaction_job_2",
                    prototype=cluster_3.prototype,
                    type="job",
                    state_available="any",
                ),
            ),
        )
        JobLog.objects.create(
            task=task,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            sub_action=SubAction.objects.create(
                action=Action.objects.create(
                    display_name="test_subaction_job_3",
                    prototype=cluster_4.prototype,
                    type="job",
                    state_available="any",
                ),
            ),
        )
        job_no_files = JobLog.objects.create(
            task=task,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            sub_action=SubAction.objects.create(
                action=Action.objects.create(
                    display_name="test_subaction_job_4",
                    prototype=cluster_5.prototype,
                    type="job",
                    state_available="any",
                ),
            ),
        )
        LogStorage.objects.create(job=job_no_files, body="stdout db", type="stdout", format="txt")
        LogStorage.objects.create(job=job_no_files, body="stderr db", type="stderr", format="txt")

        response: Response = self.client.get(
            path=reverse(viewname="v1:tasklog-download", kwargs={"task_pk": task.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    @override_settings(RUN_DIR=settings.BASE_DIR / "python" / "cm" / "tests" / "files" / "task_log_download")
    def test_download_negative(self):
        bundle = Bundle.objects.create()
        cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="cluster",
                name="Test cluster prototype",
            ),
            name="Test cluster",
        )
        action = Action.objects.create(
            display_name="Test cluster action",
            prototype=cluster.prototype,
            type="task",
            state_available="any",
            name="test_cluster_action",
        )
        task = TaskLog.objects.create(
            task_object=cluster,
            action=action,
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )
        JobLog.objects.create(
            task=task,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            sub_action=SubAction.objects.create(
                name="test_subaction_1",
                action=action,
                display_name="Test   Dis%#play   NAME!",
            ),
        )
        JobLog.objects.create(
            task=task,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            sub_action=SubAction.objects.create(name="test_subaction_2", action=action),
        )
        file_handler = get_task_download_archive_file_handler(task)
        file_handler.seek(0)

        self.assertEqual(
            f"test-cluster_test-cluster-prototype_test-cluster-action_{task.pk}.tar.gz",
            get_task_download_archive_name(task),
        )

        cluster.delete()
        bundle.delete()
        task.refresh_from_db()
        file_handler = get_task_download_archive_file_handler(task)
        file_handler.seek(0)

        self.assertEqual(f"{task.pk}.tar.gz", get_task_download_archive_name(task))
