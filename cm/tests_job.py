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
from cm import models


class TestJob(TestCase):
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-locals
    def setUp(self):
        log.debug = Mock()
        log.error = Mock()
        log.info = Mock()
        log.warning = Mock()

        self.bundle = models.Bundle.objects.create()
        self.prototype = models.Prototype.objects.create(bundle=self.bundle)
        self.object_config = models.ObjectConfig.objects.create(current=1, previous=1)
        self.adcm = models.ADCM.objects.create(prototype=self.prototype)
        self.cluster = models.Cluster.objects.create(prototype=self.prototype)
        self.cluster_object = models.ClusterObject.objects.create(
            prototype=self.prototype, cluster=self.cluster)
        self.action = models.Action.objects.create(prototype=self.prototype)

    @patch('cm.status_api.set_job_status')
    def test_set_job_status(self, mock_set_job_status):
        job = models.JobLog.objects.create(
            action_id=self.action.id, start_date=timezone.now(), finish_date=timezone.now())
        status = config.Job.RUNNING
        pid = 10

        job_module.set_job_status(job.id, status, pid)
        job = models.JobLog.objects.get(id=job.id)
        self.assertEqual(job.status, status)
        self.assertEqual(job.pid, pid)

        mock_set_job_status.assert_called_once_with(job.id, status)

    @patch('cm.status_api.set_task_status')
    def test_set_task_status(self, mock_set_task_status):
        status = config.Job.RUNNING
        task = models.TaskLog.objects.create(
            action_id=self.action.id, object_id=self.cluster.id,
            start_date=timezone.now(), finish_date=timezone.now())
        finish_date = task.finish_date

        job_module.set_task_status(task, status)

        self.assertEqual(models.TaskLog.objects.count(), 1)
        task = models.TaskLog.objects.get(id=1)
        self.assertEqual(task.id, task.id)
        self.assertEqual(task.action_id, task.action_id)
        self.assertEqual(task.object_id, task.object_id)
        self.assertEqual(task.pid, task.pid)
        self.assertEqual(task.selector, task.selector)
        self.assertEqual(task.status, status)
        self.assertEqual(task.config, task.config)
        self.assertEqual(task.hostcomponentmap, task.hostcomponentmap)
        self.assertEqual(task.start_date, task.start_date)
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
        self.action.state_on_success = 'create'
        self.action.state_on_fail = 'installed'
        self.action.save()

        job = models.JobLog(
            action_id=self.action.id, selector=f'{{"cluster": {self.cluster.id}}}',
            start_date=timezone.now(), finish_date=timezone.now())

        data = [
            (config.Job.SUCCESS, False, 'create'),
            (config.Job.FAILED, False, 'installed'),
            (config.Job.FAILED, True, 'installed'),
            (config.Job.ABORTED, False, None)
        ]

        for status, create_sub_action, test_state in data:
            with self.subTest(status=status, create_sub_action=create_sub_action,
                              test_state=test_state):

                if create_sub_action:
                    sub_action = models.SubAction.objects.create(
                        action=self.action, state_on_fail='installed')
                    job.sub_action_id = sub_action.id

                state = job_module.get_state(self.action, job, status)
                self.assertEqual(state, test_state)

    @patch('cm.api.push_obj')
    def test_set_action_state(self, mock_push_obj):
        state = ''
        task = models.TaskLog(action_id=self.action.id, object_id=self.cluster.id)
        job_module.set_action_state(self.action, task, self.cluster, state)
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
        pass

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
        self.prototype.type = 'cluster'

        obj, cluster = job_module.get_action_context(self.action, {'cluster': 1})
        self.assertEqual(obj, cluster)
        self.assertEqual(cluster, self.cluster)

    @patch('cm.job.prepare_job_config')
    @patch('cm.inventory.prepare_job_inventory')
    def test_prepare_job(self, mock_prepare_job_inventory, mock_prepare_job_config):
        job = models.JobLog.objects.create(
            action_id=self.action.id, start_date=timezone.now(), finish_date=timezone.now())
        job_module.prepare_job(self.action, None, {'cluster': 1}, job.id, self.cluster, '', {})

        mock_prepare_job_inventory.assert_called_once_with({'cluster': 1}, job.id, {})
        mock_prepare_job_config.assert_called_once_with(self.action, None, {'cluster': 1},
                                                        job.id, self.cluster, '')

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

        job = models.JobLog.objects.create(
            action_id=self.action.id, start_date=timezone.now(), finish_date=timezone.now())

        self.action.params = '{"ansible_tags": "create_users"}'
        self.action.save()
        sub_action = models.SubAction(action=self.action)
        selector = {'cluster': 1}
        conf = 'test'
        provider = models.HostProvider(prototype=self.prototype)
        host = models.Host(prototype=self.prototype, provider=provider)
        provider = models.HostProvider(prototype=self.prototype)

        data = [
            ('service', self.cluster_object),
            ('cluster', self.cluster),
            ('host', host),
            ('provider', provider),
            ('adcm', self.adcm),
        ]

        for prototype_type, obj in data:
            with self.subTest(provider_type=prototype_type, obj=obj):
                self.prototype.type = prototype_type
                self.prototype.save()

                job_module.prepare_job_config(
                    self.action, sub_action, selector, job.id, obj, conf)

                job_config = {
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
                        'status_api_token': mock_dump.call_args[0][0]['env']['status_api_token']},
                    'job': {
                        'id': 1,
                        'action': '',
                        'job_name': '',
                        'command': '',
                        'script': '',
                        'playbook': mock_dump.call_args[0][0]['job']['playbook'],
                        'params': {
                            'ansible_tags': 'create_users'
                        },
                        'cluster_id': 1,
                        'config': 'test'
                    }
                }
                if prototype_type == 'service':
                    job_config['job'].update(
                        {
                            'hostgroup': obj.prototype.name,
                            'service_id': obj.id,
                            'service_type_id': obj.prototype.id
                        })

                elif prototype_type == 'cluster':
                    job_config['job']['hostgroup'] = 'CLUSTER'
                elif prototype_type == 'host':
                    job_config['job'].update(
                        {
                            'hostgroup': 'HOST',
                            'hostname': obj.fqdn,
                            'host_id': obj.id,
                            'host_type_id': obj.prototype.id,
                            'provider_id': obj.provider.id
                        })
                elif prototype_type == 'provider':
                    job_config['job'].update(
                        {
                            'hostgroup': 'PROVIDER',
                            'provider_id': obj.id
                        })
                elif prototype_type == 'adcm':
                    job_config['job']['hostgroup'] = '127.0.0.1'

                mock_open.assert_called_with(
                    '{}/{}-config.json'.format(config.RUN_DIR, job.id), 'w')
                mock_dump.assert_called_with(job_config, fd, indent=3, sort_keys=True)
                mock_get_adcm_config.assert_called()
                mock_prepare_context.assert_called_with({'cluster': 1})
                mock_get_bundle_root.assert_called_with(self.action)
                mock_cook_script.assert_called_with(self.action, sub_action)

    def test_re_prepare_job(self):
        pass
