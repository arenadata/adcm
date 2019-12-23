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

import json
import os
from unittest.mock import patch, Mock

from django.test import TestCase
from django.utils import timezone

import cm.config as config
import cm.job as job_module
from cm.logger import log
from cm.models import (JobLog, TaskLog, Bundle, Cluster, Prototype, ObjectConfig,
                       Action, ClusterObject, ADCM)


class TestJob(TestCase):
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
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
        self.adcm = ADCM.objects.create(**{
            'prototype': self.prototype,
            'name': 'ADCM',
            'config': self.object_config,
            'state': 'created',
            'stack': '',
            'issue': ''
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
        self.cluster_object = ClusterObject.objects.create(**{
            'cluster': self.cluster,
            'prototype': self.prototype,
            'config': self.object_config,
            'state': 'created',
            'stack': '',
            'issue': ''
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
            'selector': f'{{"cluster": {self.cluster.id}}}',
            'status': 'success',
            'config': '',
            'hostcomponentmap': '',
            'start_date': timezone.now(),
            'finish_date': timezone.now()
        })
        self.job = JobLog.objects.create(**{
            'task_id': self.task.id,
            'action_id': self.action.id,
            'sub_action_id': 0,
            'pid': 1,
            'selector': f'{{"cluster": {self.cluster.id}}}',
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

        mock_set_job_status.assert_called_once_with(job.task_id, status)

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

        mock_set_task_status.assert_called_once_with(task.id, status)

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

    def test_get_state(self):
        status = config.Job.SUCCESS
        state = job_module.get_state(self.action, self.job, status)
        self.assertEqual(state, self.action.state_on_success)

    @patch('cm.api.push_obj')
    def test_set_action_state(self, mock_push_obj):
        state = ''
        job_module.set_action_state(self.action, self.task, self.cluster, state)
        mock_push_obj.assert_called_once_with(self.cluster, state)

    @patch('cm.api.set_object_state')
    def test_unlock_obj(self, mock_set_object_state):
        self.cluster.stack = '["created"]'
        self.cluster.save()

        def set_object_state(obj, state):
            obj.state = state
            obj.save()

        mock_set_object_state.side_effect = set_object_state

        job_module.unlock_obj(self.cluster)

        self.assertEqual(self.cluster.stack, '[]')
        self.assertEqual(self.cluster.state, 'created')

    @patch('cm.job.unlock_obj')
    def test_unlock_objects(self, mock_unlock_obj):
        self.cluster.stack = '["created"]'
        self.cluster.save()
        self.cluster_object.stack = '["created"]'
        self.cluster_object.save()

        def unlock_obj(obj):
            stack = json.loads(obj.stack)
            state = stack.pop()
            obj.stack = json.dumps(stack)
            obj.state = state
            obj.save()

        mock_unlock_obj.side_effect = unlock_obj

        job_module.unlock_objects(self.cluster)

        self.assertEqual(self.cluster.stack, '[]')
        self.assertEqual(self.cluster.state, 'created')

    @patch('cm.api.save_hc')
    def test_restore_hc(self, mock_save_hc):
        # TODO: continue
        job_module.restore_hc(self.task, self.action, config.Job.SUCCESS)

    def test_finish_task(self):
        # IS CALLED: cm.job.set_action_state, cm.job.unlock_objects,
        # cm.job.restore_hc, cm.job.set_task_status
        pass

    @patch('cm.job.err')
    def test_check_selector(self, mock_err):
        selector = job_module.check_selector({'cluster': 1}, 'cluster')
        self.assertEqual(selector, 1)
        self.assertEqual(mock_err.call_count, 0)

    @patch('cm.job.err')
    def test_check_service_task(self, mock_err):
        service = job_module.check_service_task(self.cluster.id, self.action)
        self.assertEqual(self.cluster_object, service)
        self.assertEqual(mock_err.call_count, 0)

    @patch('cm.job.err')
    def test_check_cluster(self, mock_err):
        cluster = job_module.check_cluster(self.cluster.id)
        self.assertEqual(cluster, self.cluster)
        self.assertEqual(mock_err.call_count, 0)

    def test_get_action_context(self):
        obj, cluster = job_module.get_action_context(self.action, {'cluster': 1})
        self.assertEqual(obj, cluster)
        self.assertEqual(cluster, self.cluster)

    @patch('cm.job.prepare_job_config')
    @patch('cm.inventory.prepare_job_inventory')
    def test_prepare_job(self, mock_prepare_job_inventory, mock_prepare_job_config):
        job_module.prepare_job(self.action, None, {'cluster': 1}, self.job.id, self.cluster, '', {})

        mock_prepare_job_inventory.assert_called_once_with({'cluster': 1}, self.job.id, {})
        mock_prepare_job_config.assert_called_once_with(self.action, None, {'cluster': 1},
                                                        self.job.id, self.cluster, '')

    @patch('cm.job.get_obj_config')
    def test_get_adcm_config(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}

        conf = job_module.get_adcm_config()

        self.assertEqual(conf, {})
        mock_get_obj_config.assert_called_once_with(self.adcm)

    def test_prepare_context(self):
        context = job_module.prepare_context({'cluster': 1})

        self.assertDictEqual(context, {'type': 'cluster', 'cluster_id': 1})

    def test_get_bundle_root(self):
        path = job_module.get_bundle_root(self.action)

        self.assertEqual(path, config.BUNDLE_DIR)

    @patch('cm.job.get_bundle_root')
    def test_cook_script(self, mock_get_bundle_root):
        mock_get_bundle_root.return_value = config.BUNDLE_DIR

        path = job_module.cook_script(self.action, None)

        test_path = os.path.join(
            config.BUNDLE_DIR, self.action.prototype.bundle.hash, self.action.script)
        self.assertEqual(path, test_path)
        mock_get_bundle_root.assert_called_once_with(self.action)

    @patch('cm.job.cook_script')
    @patch('cm.job.get_bundle_root')
    @patch('cm.job.prepare_context')
    @patch('cm.job.get_adcm_config')
    @patch("json.dump")
    @patch("builtins.open")
    def test_prepare_job_config(self, mock_open, mock_dump, mock_get_adcm_config,
                                mock_prepare_context, mock_get_bundle_root, mock_cook_script):
        fd = Mock()
        mock_open.return_value = fd
        mock_get_adcm_config.return_value = {}
        mock_prepare_context.return_value = {'type': 'cluster', 'cluster_id': 1}
        mock_get_bundle_root.return_value = config.BUNDLE_DIR
        mock_cook_script.return_value = os.path.join(
            config.BUNDLE_DIR, self.action.prototype.bundle.hash, self.action.script)

        job_module.prepare_job_config(
            self.action, None, {'cluster': 1}, self.job.id, self.cluster, '')

        value = {
            'adcm': {
                'config': {}
            },
            'context': {
                'type': 'cluster',
                'cluster_id': 1
            },
            'env': {
                'run_dir': mock_dump.call_args[0][0]['env']['run_dir'],
                'log_dir': mock_dump.call_args[0][0]['env']['log_dir'],
                'stack_dir': mock_dump.call_args[0][0]['env']['stack_dir'],
                'status_api_token': mock_dump.call_args[0][0]['env']['status_api_token']
            },
            'job': {
                'id': 1,
                'action': 're-start',
                'job_name': 're-start',                
                'command': 're-start',
                'script': '',
                'playbook': mock_dump.call_args[0][0]['job']['playbook'],
                'cluster_id': 1,
                'hostgroup': 'CLUSTER'
            }
        }
        mock_open.assert_called_once_with(
            '{}/{}-config.json'.format(config.RUN_DIR, self.job.id), 'w')
        mock_dump.assert_called_once_with(value, fd, indent=3, sort_keys=True)
        mock_get_adcm_config.assert_called_once_with()
        mock_prepare_context.assert_called_once_with({'cluster': 1})
        mock_get_bundle_root.assert_called_once_with(self.action)
        mock_cook_script.assert_called_once_with(self.action, None)

    def test_re_prepare_job(self):
        pass
