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
from cm.models import ConcernType
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
