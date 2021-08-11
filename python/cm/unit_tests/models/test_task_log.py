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

from django.test import TestCase

from cm.unit_tests import utils


class TaskLogLockTest(TestCase):
    """Tests for `cm.models.TaskLog` lock-related methods"""

    def setUp(self) -> None:
        utils.gen_adcm()

    def test_lock_affected__lock_is_single(self):
        cluster = utils.gen_cluster()
        task = utils.gen_task_log(cluster)
        task.lock = utils.gen_concern_item()
        task.save()

        task.lock_affected([cluster])
        self.assertFalse(cluster.is_locked)

    def test_lock_affected(self):
        cluster = utils.gen_cluster()
        task = utils.gen_task_log(cluster)

        task.lock_affected([cluster])
        self.assertTrue(cluster.is_locked)
        task.refresh_from_db()
        self.assertIsNotNone(task.lock)

    def test_unlock_affected(self):
        cluster = utils.gen_cluster()
        task = utils.gen_task_log(cluster)
        task.lock_affected([cluster])

        task.unlock_affected()
        self.assertFalse(cluster.is_locked)
        self.assertIsNone(task.lock)
