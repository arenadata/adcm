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

from unittest.mock import patch, Mock

from django.test import TestCase
from django.utils import timezone

import cm.config as config
import cm.job as job_module
from cm.logger import log
from cm.models import (JobLog, TaskLog, Bundle, Cluster, Prototype, ObjectConfig, Action)


class TestJob(TestCase):

    def setUp(self):
        log.debug = Mock()
        log.error = Mock()
        log.info = Mock()
        log.warning = Mock()

        self.bundle = Bundle.objects.create(**{
            'name': 'ADB',
            'version': '2.5',
            'version_order': 4,
            'edition': 'community',
            'license': 'absent',
            'license_path': None,
            'license_hash': None,
            'hash': '2232f33c6259d44c23046fce4382f16c450f8ba5',
            'description': '',
            'date': timezone.now()
        })
        self.prototype = Prototype.objects.create(**{
            'bundle': self.bundle,
            'type': 'cluster',
            'name': 'ADB',
            'display_name': 'ADB',
            'version': '2.5',
            'version_order': 11,
            'required': False,
            'shared': False,
            'adcm_min_version': None,
            'monitoring': 'active',
            'description': ''
        })
        self.object_config = ObjectConfig.objects.create(**{
            'current': 1,
            'previous': 1
        })
        self.cluster = Cluster.objects.create(**{
            'prototype': self.prototype,
            'name': 'Fear Limpopo',
            'description': '',
            'config': self.object_config,
            'state': 'installed',
            'stack': '[]',
            'issue': '{}'
        })
        self.action = Action.objects.create(**{
            'prototype': self.prototype,
            'name': 're-start',
            'display_name': 're-start',
            'description': '',
            'type': 'task',
            'button': None,
            'script': '',
            'script_type': '',
            'state_on_success': 'installed',
            'state_on_fail': 'created',
            'state_available': '["created", "installed"]',
            'params': '',
            'log_files': '',
            'hostcomponentmap': '',
        })
        self.task = TaskLog.objects.create(**{
            'action_id': self.action.id,
            'object_id': self.cluster.id,
            'pid': 1,
            'selector': '{"cluster": 1}',
            'status': 'success',
            'config': '',
            'hostcomponentmap': '',
            'start_date': timezone.now(),
            'finish_date': timezone.now()
        })
        self.job = JobLog.objects.create(**{
            'task_id': self.task.id,
            'action_id': self.action.id,
            'pid': 1,
            'selector': '{"cluster": 1}',
            'status': 'success',
            'start_date': timezone.now(),
            'finish_date': timezone.now()
        })

    @patch('cm.status_api.set_job_status')
    def test_set_job_status(self, mock_set_job_status):
        job_id = 1
        status = config.Job.RUNNING
        pid = 10

        job_module.set_job_status(job_id, status, pid)

        self.assertEqual(JobLog.objects.count(), 1)
        job = JobLog.objects.get(id=1)
        self.assertEqual(job.id, job_id)
        self.assertEqual(job.task_id, self.job.task_id)
        self.assertEqual(job.action_id, self.job.action_id)
        self.assertEqual(job.sub_action_id, self.job.sub_action_id)
        self.assertEqual(job.pid, pid)
        self.assertEqual(job.selector, self.job.selector)
        self.assertEqual(job.log_files, self.job.log_files)
        self.assertEqual(job.status, status)
        self.assertEqual(job.start_date, self.job.start_date)
        self.assertTrue(job.finish_date != self.job.finish_date)

        self.assertEqual(mock_set_job_status.call_count, 1)
        self.assertEqual(mock_set_job_status.call_args.args, (job.task_id, status))

    @patch('cm.status_api.set_task_status')
    def test_set_task_status(self, mock_set_task_status):
        status = config.Job.RUNNING
        finish_date = self.task.finish_date

        job_module.set_task_status(self.task, status)

        self.assertEqual(TaskLog.objects.count(), 1)
        task = TaskLog.objects.get(id=1)
        self.assertEqual(task.id, self.task.id)
        self.assertEqual(task.action_id, self.task.action_id)
        self.assertEqual(task.object_id, self.task.object_id)
        self.assertEqual(task.pid, self.task.pid)
        self.assertEqual(task.selector, self.task.selector)
        self.assertEqual(task.status, status)
        self.assertEqual(task.config, self.task.config)
        self.assertEqual(task.hostcomponentmap, self.task.hostcomponentmap)
        self.assertEqual(task.start_date, self.task.start_date)
        self.assertTrue(task.finish_date != finish_date)

        self.assertEqual(mock_set_task_status.call_count, 1)
        self.assertEqual(mock_set_task_status.call_args.args, (task.id, status))

    def test_get_task_obj(self):
        task_obj = job_module.get_task_obj('cluster', 1)

        self.assertEqual(task_obj.id, self.cluster.id)
        self.assertEqual(task_obj.prototype_id, self.cluster.prototype_id)
        self.assertEqual(task_obj.name, self.cluster.name)
        self.assertEqual(task_obj.description, self.cluster.description)
        self.assertEqual(task_obj.config_id, self.cluster.config_id)
        self.assertEqual(task_obj.state, self.cluster.state)
        self.assertEqual(task_obj.stack, self.cluster.stack)
        self.assertEqual(task_obj.issue, self.cluster.issue)

    def test_set_action_state(self):
        # IS CALLED: cm.job.get_task_obj and cm.api.push_obj
        status = 'failed'
        action, cluster = job_module.set_action_state(self.task, self.job, status)
        self.assertEqual(cluster.id, self.cluster.id)
        self.assertEqual(cluster.prototype_id, self.cluster.prototype_id)
        self.assertEqual(cluster.name, self.cluster.name)
        self.assertEqual(cluster.description, self.cluster.description)
        self.assertEqual(cluster.config, self.cluster.config)
        self.assertEqual(cluster.state, self.cluster.state)
        self.assertTrue(cluster.stack != self.cluster.stack)
        self.assertEqual(cluster.issue, self.cluster.issue)

        self.assertEqual(f'["{self.action.state_on_fail}"]', cluster.stack)

    def test_unlock_obj(self):
        # IS CALLED: cm.api.set_object_state
        self.cluster.stack = '["created"]'
        self.cluster.save()

        job_module.unlock_obj(self.cluster)

        self.assertEqual(self.cluster.stack, '[]')

    def test_unlock_objects(self):
        # IS CALLED: cm.job.unlock_obj
        self.cluster.stack = '["created"]'
        self.cluster.save()

        job_module.unlock_obj(self.cluster)

        self.assertEqual(self.cluster.stack, '[]')

    # TODO: added test for restore_hc from finish_task
