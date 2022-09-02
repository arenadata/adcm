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

# pylint: disable=protected-access

import os
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

import cm
import cm.job as job_module
from cm import config, models
from cm.logger import logger
from cm.unit_tests import utils


class TestJob(TestCase):
    def setUp(self):
        logger.debug = Mock()
        logger.error = Mock()
        logger.info = Mock()
        logger.warning = Mock()

    def test_set_job_status(self):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        action = models.Action.objects.create(prototype=prototype)
        job = models.JobLog.objects.create(
            action=action, start_date=timezone.now(), finish_date=timezone.now()
        )
        status = config.Job.RUNNING
        pid = 10
        event = Mock()

        job_module.set_job_status(job.id, status, event, pid)

        job = models.JobLog.objects.get(id=job.id)
        self.assertEqual(job.status, status)
        self.assertEqual(job.pid, pid)

        event.set_job_status.assert_called_once_with(job.id, status)

    def test_set_task_status(self):
        event = Mock()
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        action = models.Action.objects.create(prototype=prototype)
        task = models.TaskLog.objects.create(
            action=action, object_id=1, start_date=timezone.now(), finish_date=timezone.now()
        )

        job_module.set_task_status(task, config.Job.RUNNING, event)

        self.assertEqual(task.status, config.Job.RUNNING)
        event.set_task_status.assert_called_once_with(task.id, config.Job.RUNNING)

    def test_get_state_single_job(self):
        bundle = utils.gen_bundle()
        cluster_proto = utils.gen_prototype(bundle, 'cluster')
        cluster = utils.gen_cluster(prototype=cluster_proto)
        action = utils.gen_action(prototype=cluster_proto)
        action.state_on_success = 'success'
        action.state_on_fail = 'fail'
        action.multi_state_on_success_set = ['success']
        action.multi_state_on_success_unset = ['success unset']
        action.multi_state_on_fail_set = ['fail']
        action.multi_state_on_fail_unset = ['fail unset']
        action.save()
        task = utils.gen_task_log(cluster, action)
        job = utils.gen_job_log(task)

        # status: expected state, expected multi_state set, expected multi_state unset
        test_data = [
            [config.Job.SUCCESS, 'success', ['success'], ['success unset']],
            [config.Job.FAILED, 'fail', ['fail'], ['fail unset']],
            [config.Job.ABORTED, None, [], []],
        ]
        for status, exp_state, exp_m_state_set, exp_m_state_unset in test_data:
            state, m_state_set, m_state_unset = job_module.get_state(action, job, status)
            self.assertEqual(state, exp_state)
            self.assertListEqual(m_state_set, exp_m_state_set)
            self.assertListEqual(m_state_unset, exp_m_state_unset)

    def test_get_state_multi_job(self):
        bundle = utils.gen_bundle()
        cluster_proto = utils.gen_prototype(bundle, 'cluster')
        cluster = utils.gen_cluster(prototype=cluster_proto)
        action = utils.gen_action(prototype=cluster_proto)
        action.state_on_success = 'success'
        action.state_on_fail = 'fail'
        action.multi_state_on_success_set = ['success']
        action.multi_state_on_success_unset = ['success unset']
        action.multi_state_on_fail_set = ['fail']
        action.multi_state_on_fail_unset = ['fail unset']
        action.save()
        task = utils.gen_task_log(cluster, action)
        job = utils.gen_job_log(task)
        job.sub_action = models.SubAction.objects.create(
            action=action, state_on_fail='sub_action fail'
        )

        # status: expected state, expected multi_state set, expected multi_state unset
        test_data = [
            [config.Job.SUCCESS, 'success', ['success'], ['success unset']],
            [config.Job.FAILED, 'sub_action fail', ['fail'], ['fail unset']],
            [config.Job.ABORTED, None, [], []],
        ]
        for status, exp_state, exp_m_state_set, exp_m_state_unset in test_data:
            state, m_state_set, m_state_unset = job_module.get_state(action, job, status)
            self.assertEqual(state, exp_state)
            self.assertListEqual(m_state_set, exp_m_state_set)
            self.assertListEqual(m_state_unset, exp_m_state_unset)

    def test_set_action_state(self):
        # pylint: disable=too-many-locals

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype)
        host_provider = models.HostProvider.objects.create(prototype=prototype)
        adcm = models.ADCM.objects.create(prototype=prototype)
        action = models.Action.objects.create(prototype=prototype)
        task = models.TaskLog.objects.create(
            action=action, object_id=1, start_date=timezone.now(), finish_date=timezone.now()
        )
        to_set = 'to set'
        to_unset = 'to unset'
        for obj in (adcm, cluster, cluster_object, host_provider, host):
            obj.set_multi_state(to_unset)

        data = [
            (cluster_object, 'running', to_set, to_unset),
            (cluster, 'removed', to_set, to_unset),
            (host, None, to_set, to_unset),
            (host_provider, 'stopped', to_set, to_unset),
            (adcm, 'initiated', to_set, to_unset),
        ]

        for obj, state, ms_to_set, ms_to_unset in data:
            with self.subTest(obj=obj, state=state):
                job_module.set_action_state(action, task, obj, state, [ms_to_set], [ms_to_unset])
                self.assertEqual(obj.state, state or 'created')
                self.assertIn(to_set, obj.multi_state)
                self.assertNotIn(to_unset, obj.multi_state)

    @patch('cm.job.api.save_hc')
    def test_restore_hc(self, mock_save_hc):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype, cluster=cluster)
        component = models.Prototype.objects.create(
            parent=prototype, type='component', bundle=bundle
        )
        service_component = models.ServiceComponent.objects.create(
            cluster=cluster, service=cluster_object, prototype=component
        )
        hostcomponentmap = [
            {
                'host_id': host.id,
                'service_id': cluster_object.id,
                'component_id': service_component.id,
            }
        ]
        action = models.Action.objects.create(
            prototype=prototype, hostcomponentmap=hostcomponentmap
        )
        task = models.TaskLog.objects.create(
            action=action,
            task_object=cluster,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            selector={'cluster': cluster.id},
            hostcomponentmap=hostcomponentmap,
        )

        job_module.restore_hc(task, action, config.Job.FAILED)
        mock_save_hc.assert_called_once_with(cluster, [(cluster_object, host, service_component)])

    @patch('cm.job.err')
    def test_check_service_task(self, mock_err):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        action = models.Action.objects.create(prototype=prototype)

        service = job_module.check_service_task(cluster.id, action)

        self.assertEqual(cluster_object, service)
        self.assertEqual(mock_err.call_count, 0)

    @patch('cm.job.err')
    def test_check_cluster(self, mock_err):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)

        test_cluster = job_module.check_cluster(cluster.id)

        self.assertEqual(cluster, test_cluster)
        self.assertEqual(mock_err.call_count, 0)

    @patch('cm.job.prepare_ansible_config')
    @patch('cm.job.prepare_job_config')
    @patch('cm.job.inventory.prepare_job_inventory')
    def test_prepare_job(
        self, mock_prepare_job_inventory, mock_prepare_job_config, mock_prepare_ansible_config
    ):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        action = models.Action.objects.create(prototype=prototype)
        job = models.JobLog.objects.create(
            action=action, start_date=timezone.now(), finish_date=timezone.now()
        )

        job_module.prepare_job(action, None, job.id, cluster, '', {}, None, False)

        mock_prepare_job_inventory.assert_called_once_with(cluster, job.id, action, {}, None)
        mock_prepare_job_config.assert_called_once_with(action, None, job.id, cluster, '', False)
        mock_prepare_ansible_config.assert_called_once_with(job.id, action, None)

    @patch('cm.job.get_obj_config')
    def test_get_adcm_config(self, mock_get_obj_config):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        adcm = models.ADCM.objects.create(prototype=prototype)
        mock_get_obj_config.return_value = {}

        conf = job_module.get_adcm_config()

        self.assertEqual(conf, {})
        mock_get_obj_config.assert_called_once_with(adcm)

    def test_prepare_context(self):
        bundle = models.Bundle.objects.create()
        proto1 = models.Prototype.objects.create(bundle=bundle, type='cluster')
        action1 = models.Action.objects.create(prototype=proto1)
        cm.api.add_cluster(proto1, 'Garbage')
        cluster = cm.api.add_cluster(proto1, 'Ontario')
        context = job_module.prepare_context(action1, cluster)
        self.assertDictEqual(context, {'type': 'cluster', 'cluster_id': cluster.id})

        proto2 = models.Prototype.objects.create(bundle=bundle, type='service')
        action2 = models.Action.objects.create(prototype=proto2)
        service = cm.api.add_service_to_cluster(cluster, proto2)
        context = job_module.prepare_context(action2, service)
        self.assertDictEqual(
            context, {'type': 'service', 'service_id': service.id, 'cluster_id': cluster.id}
        )

    def test_get_bundle_root(self):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        action = models.Action.objects.create(prototype=prototype)

        data = [('adcm', os.path.join(config.BASE_DIR, 'conf')), ('', config.BUNDLE_DIR)]

        for prototype_type, test_path in data:
            prototype.type = prototype_type
            prototype.save()

            path = job_module.get_bundle_root(action)

            self.assertEqual(path, test_path)

    @patch('cm.job.get_bundle_root')
    def test_cook_script(self, mock_get_bundle_root):
        bundle = models.Bundle.objects.create(hash='6525d392dc9d1fb3273fb4244e393672579d75f3')
        prototype = models.Prototype.objects.create(bundle=bundle)
        action = models.Action.objects.create(prototype=prototype)
        sub_action = models.SubAction.objects.create(action=action, script='ansible/sleep.yaml')
        mock_get_bundle_root.return_value = config.BUNDLE_DIR

        data = [
            (
                sub_action,
                'main.yaml',
                os.path.join(config.BUNDLE_DIR, action.prototype.bundle.hash, 'ansible/sleep.yaml'),
            ),
            (
                None,
                'main.yaml',
                os.path.join(config.BUNDLE_DIR, action.prototype.bundle.hash, 'main.yaml'),
            ),
            (
                None,
                './main.yaml',
                os.path.join(config.BUNDLE_DIR, action.prototype.bundle.hash, 'main.yaml'),
            ),
        ]

        for sa, script, test_path in data:
            with self.subTest(sub_action=sub_action, script=script):
                action.script = script
                action.save()

                path = job_module.cook_script(action, sa)

                self.assertEqual(path, test_path)
                mock_get_bundle_root.assert_called_once_with(action)
                mock_get_bundle_root.reset_mock()

    @patch('cm.job.cook_script')
    @patch('cm.job.get_bundle_root')
    @patch('cm.job.prepare_context')
    @patch('cm.job.get_adcm_config')
    @patch("json.dump")
    @patch("builtins.open")
    def test_prepare_job_config(
        self,
        mock_open,
        mock_dump,
        mock_get_adcm_config,
        mock_prepare_context,
        mock_get_bundle_root,
        mock_cook_script,
    ):
        # pylint: disable=too-many-locals

        bundle = models.Bundle.objects.create()
        proto1 = models.Prototype.objects.create(bundle=bundle, type='cluster')
        cluster = models.Cluster.objects.create(prototype=proto1)
        proto2 = models.Prototype.objects.create(bundle=bundle, type='service', name='Hive')
        service = cm.api.add_service_to_cluster(cluster, proto2)
        cluster_action = models.Action.objects.create(prototype=proto1)
        service_action = models.Action.objects.create(prototype=proto2)
        proto3 = models.Prototype.objects.create(bundle=bundle, type='adcm')
        adcm_action = models.Action.objects.create(prototype=proto3)
        adcm = models.ADCM.objects.create(prototype=proto3)

        fd = Mock()
        mock_open.return_value = fd
        mock_get_adcm_config.return_value = {}
        mock_prepare_context.return_value = {'type': 'cluster', 'cluster_id': 1}
        mock_get_bundle_root.return_value = config.BUNDLE_DIR
        mock_cook_script.return_value = os.path.join(
            config.BUNDLE_DIR, cluster_action.prototype.bundle.hash, cluster_action.script
        )

        job = models.JobLog.objects.create(
            action=cluster_action, start_date=timezone.now(), finish_date=timezone.now()
        )

        conf = 'test'
        proto4 = models.Prototype.objects.create(bundle=bundle, type='provider')
        provider_action = models.Action.objects.create(prototype=proto4)
        provider = models.HostProvider(prototype=proto4)
        proto5 = models.Prototype.objects.create(bundle=bundle, type='host')
        host_action = models.Action.objects.create(prototype=proto5)
        host = models.Host(prototype=proto5, provider=provider)

        data = [
            ('service', service, service_action),
            ('cluster', cluster, cluster_action),
            ('host', host, host_action),
            ('provider', provider, provider_action),
            ('adcm', adcm, adcm_action),
        ]

        for prototype_type, obj, action in data:
            with self.subTest(provider_type=prototype_type, obj=obj):
                job_module.prepare_job_config(action, None, job.id, obj, conf, False)

                job_config = {
                    'adcm': {'config': {}},
                    'context': {'type': 'cluster', 'cluster_id': 1},
                    'env': {
                        'run_dir': mock_dump.call_args[0][0]['env']['run_dir'],
                        'log_dir': mock_dump.call_args[0][0]['env']['log_dir'],
                        'tmp_dir': os.path.join(config.RUN_DIR, f'{job.id}', 'tmp'),
                        'stack_dir': mock_dump.call_args[0][0]['env']['stack_dir'],
                        'status_api_token': mock_dump.call_args[0][0]['env']['status_api_token'],
                    },
                    'job': {
                        'id': 1,
                        'action': action.name,
                        'job_name': '',
                        'command': '',
                        'script': '',
                        'verbose': False,
                        'playbook': mock_dump.call_args[0][0]['job']['playbook'],
                        'config': 'test',
                    },
                }
                if prototype_type == 'service':
                    job_config['job'].update(
                        {
                            'hostgroup': obj.prototype.name,
                            'service_id': obj.id,
                            'service_type_id': obj.prototype.id,
                            'cluster_id': cluster.id,
                        }
                    )

                elif prototype_type == 'cluster':
                    job_config['job']['cluster_id'] = cluster.id
                    job_config['job']['hostgroup'] = 'CLUSTER'
                elif prototype_type == 'host':
                    job_config['job'].update(
                        {
                            'hostgroup': 'HOST',
                            'hostname': obj.fqdn,
                            'host_id': obj.id,
                            'host_type_id': obj.prototype.id,
                            'provider_id': obj.provider.id,
                        }
                    )
                elif prototype_type == 'provider':
                    job_config['job'].update({'hostgroup': 'PROVIDER', 'provider_id': obj.id})
                elif prototype_type == 'adcm':
                    job_config['job']['hostgroup'] = '127.0.0.1'

                mock_open.assert_called_with(
                    f'{config.RUN_DIR}/{job.id}/config.json', 'w', encoding='utf_8'
                )
                mock_dump.assert_called_with(job_config, fd, indent=3, sort_keys=True)
                mock_get_adcm_config.assert_called()
                mock_prepare_context.assert_called_with(action, obj)
                mock_get_bundle_root.assert_called_with(action)
                mock_cook_script.assert_called_with(action, None)

    @patch('cm.job.cook_delta')
    @patch('cm.job.get_old_hc')
    @patch('cm.job.get_actual_hc')
    @patch('cm.job.prepare_job')
    def test_re_prepare_job(
        self, mock_prepare_job, mock_get_actual_hc, mock_get_old_hc, mock_cook_delta
    ):
        # pylint: disable=too-many-locals

        new_hc = Mock()
        mock_get_actual_hc.return_value = new_hc
        old_hc = Mock()
        mock_get_old_hc.return_value = old_hc
        delta = Mock()
        mock_cook_delta.return_value = delta

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle, type='cluster')
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype, cluster=cluster)
        component = models.Prototype.objects.create(
            parent=prototype, type='component', bundle=bundle
        )
        service_component = models.ServiceComponent.objects.create(
            cluster=cluster, service=cluster_object, prototype=component
        )
        action = models.Action.objects.create(
            prototype=prototype, hostcomponentmap=[{'service': '', 'component': '', 'action': ''}]
        )
        sub_action = models.SubAction.objects.create(action=action)
        hostcomponentmap = [
            {
                'host_id': host.id,
                'service_id': cluster_object.id,
                'component_id': service_component.id,
            }
        ]
        task = models.TaskLog.objects.create(
            action=action,
            task_object=cluster,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            hostcomponentmap=hostcomponentmap,
            config={"sleeptime": 1},
        )
        job = models.JobLog.objects.create(
            task=task,
            action=action,
            sub_action=sub_action,
            start_date=timezone.now(),
            finish_date=timezone.now(),
        )

        job_module.re_prepare_job(task, job)

        mock_get_actual_hc.assert_called_once_with(cluster)
        mock_get_old_hc.assert_called_once_with(task.hostcomponentmap)
        mock_cook_delta.assert_called_once_with(cluster, new_hc, action.hostcomponentmap, old_hc)
        mock_prepare_job.assert_called_once_with(
            action, sub_action, job.id, cluster, task.config, delta, None, False
        )
