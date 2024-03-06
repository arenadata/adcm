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


from adcm.tests.base import BaseTestCase
from api.job.views import (
    get_task_download_archive_file_handler,
    get_task_download_archive_name,
)
from core.job.dto import TaskPayloadDTO
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from cm.issue import lock_affected_objects, unlock_affected_objects
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
from cm.services.job.prepare import prepare_task_for_action
from cm.tests.utils import (
    gen_adcm,
    gen_cluster,
    gen_concern_item,
    gen_job_log,
    gen_task_log,
)


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
        lock_affected_objects(task=task, objects=[cluster])

        self.assertFalse(cluster.locked)

    def test_lock_affected(self):
        cluster = gen_cluster()
        task = gen_task_log(cluster)
        gen_job_log(task)
        lock_affected_objects(task=task, objects=[cluster])

        self.assertTrue(cluster.locked)

        task.refresh_from_db()

        self.assertIsNotNone(task.lock)

    def test_unlock_affected(self):
        cluster = gen_cluster()
        task = gen_task_log(cluster)
        gen_job_log(task)
        lock_affected_objects(task=task, objects=[cluster])
        unlock_affected_objects(task=task)

        self.assertFalse(cluster.locked)
        self.assertIsNone(task.lock)

    # todo looks like useless test
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
            task=TaskLog.objects.create(
                task_object=cluster,
                action=Action.objects.create(
                    display_name="test_subaction_job_1",
                    prototype=cluster_2.prototype,
                    type="job",
                    state_available="any",
                ),
                start_date=timezone.now(),
                finish_date=timezone.now(),
            ),
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )
        JobLog.objects.create(
            task=TaskLog.objects.create(
                task_object=cluster,
                action=Action.objects.create(
                    display_name="test_subaction_job_2",
                    prototype=cluster_3.prototype,
                    type="job",
                    state_available="any",
                ),
                start_date=timezone.now(),
                finish_date=timezone.now(),
            ),
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )
        JobLog.objects.create(
            task=TaskLog.objects.create(
                task_object=cluster,
                action=Action.objects.create(
                    display_name="test_subaction_job_3",
                    prototype=cluster_4.prototype,
                    type="job",
                    state_available="any",
                ),
                start_date=timezone.now(),
                finish_date=timezone.now(),
            ),
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )
        job_no_files = JobLog.objects.create(
            task=TaskLog.objects.create(
                task_object=cluster,
                action=Action.objects.create(
                    display_name="test_subaction_job_4",
                    prototype=cluster_5.prototype,
                    type="job",
                    state_available="any",
                ),
                start_date=timezone.now(),
                finish_date=timezone.now(),
            ),
            start_date=timezone.now(),
            finish_date=timezone.now(),
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
            script_type="ansible",
            state_available="any",
            name="test_cluster_action",
        )
        SubAction.objects.create(
            name="test_subaction_1",
            action=action,
            script_type="ansible",
            display_name="Test   Dis%#play   NAME!",
        )
        SubAction.objects.create(name="test_subaction_2", action=action, script_type="ansible")
        object_ = CoreObjectDescriptor(id=cluster.pk, type=ADCMCoreType.CLUSTER)
        task = TaskLog.objects.get(
            id=prepare_task_for_action(
                target=object_,
                owner=object_,
                action=action.pk,
                payload=TaskPayloadDTO(),
            ).id
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
