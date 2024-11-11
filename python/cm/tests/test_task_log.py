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

from cm.models import (
    Action,
    Bundle,
    Cluster,
    Prototype,
    SubAction,
    TaskLog,
)
from cm.services.job.action import prepare_task_for_action
from cm.tests.utils import (
    gen_adcm,
)


class TaskLogLockTest(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        gen_adcm()

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
                orm_owner=cluster,
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
