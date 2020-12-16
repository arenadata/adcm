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
import os
from unittest.mock import patch, Mock, call

from django.test import TestCase
from django.utils import timezone

import cm.config as config
import cm.job as job_module
from cm import models
from cm.logger import log


class TestJob(TestCase):
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-locals
    def setUp(self):
        log.debug = Mock()
        log.error = Mock()
        log.info = Mock()
        log.warning = Mock()

    def test_set_job_status(self):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        action = models.Action.objects.create(prototype=prototype)
        job = models.JobLog.objects.create(
            action_id=action.id, start_date=timezone.now(), finish_date=timezone.now())
        status = config.Job.RUNNING
        pid = 10
        event = Mock()

        job_module. set_job_status(job.id, status, event, pid)

        job = models.JobLog.objects.get(id=job.id)
        self.assertEqual(job.status, status)
        self.assertEqual(job.pid, pid)

        event.set_job_status.assert_called_once_with(job.id, status)

    def test_set_task_status(self):
        event = Mock()
        task = models.TaskLog.objects.create(
            action_id=1, object_id=1,
            start_date=timezone.now(), finish_date=timezone.now())

        job_module.set_task_status(task, config.Job.RUNNING, event)

        self.assertEqual(task.status, config.Job.RUNNING)
        event.set_task_status.assert_called_once_with(task.id, config.Job.RUNNING)

    def test_get_task_obj(self):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype)
        host_provider = models.HostProvider.objects.create(prototype=prototype)
        adcm = models.ADCM.objects.create(prototype=prototype)

        data = [
            ('service', cluster_object.id, cluster_object),
            ('host', host.id, host),
            ('host', 2, None),
            ('cluster', cluster.id, cluster),
            ('provider', host_provider.id, host_provider),
            ('adcm', adcm.id, adcm),
            ('action', 1, None),

        ]

        for context, obj_id, test_obj in data:
            with self.subTest(context=context, obj_id=obj_id):

                obj = job_module.get_task_obj(context, obj_id)

                self.assertEqual(obj, test_obj)

    def test_get_state(self):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        action = models.Action.objects.create(
            prototype=prototype, state_on_success='create', state_on_fail='installed')

        job = models.JobLog(
            action_id=action.id, selector={'cluster': cluster.id},
            start_date=timezone.now(), finish_date=timezone.now())

        data = [
            (config.Job.SUCCESS, False, 'create'),
            (config.Job.SUCCESS, False, None),
            (config.Job.FAILED, False, 'installed'),
            (config.Job.FAILED, False, None),
            (config.Job.FAILED, True, 'installed'),
            (config.Job.ABORTED, False, None)
        ]

        for status, create_sub_action, test_state in data:
            with self.subTest(status=status, create_sub_action=create_sub_action,
                              test_state=test_state):

                if create_sub_action:
                    sub_action = models.SubAction.objects.create(
                        action=action, state_on_fail='installed')
                    job.sub_action_id = sub_action.id
                if status == config.Job.SUCCESS and test_state is None:
                    action.state_on_success = ''
                if status == config.Job.FAILED and test_state is None:
                    action.state_on_fail = ''

                state = job_module.get_state(action, job, status)

                self.assertEqual(state, test_state)

    @patch('cm.api.push_obj')
    def test_set_action_state(self, mock_push_obj):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype)
        host_provider = models.HostProvider.objects.create(prototype=prototype)
        adcm = models.ADCM.objects.create(prototype=prototype)
        action = models.Action.objects.create(prototype=prototype)
        task = models.TaskLog.objects.create(
            action_id=action.id, object_id=1, start_date=timezone.now(),
            finish_date=timezone.now())

        data = [
            (cluster_object, 'running'),
            (cluster, 'removed'),
            (host, None),
            (host_provider, 'stopped'),
            (adcm, 'initiated'),
        ]

        for obj, state in data:
            with self.subTest(obj=obj, state=state):

                job_module.set_action_state(action, task, obj, state)

                mock_push_obj.assert_called_with(obj, state)

    @patch('cm.job.api.set_object_state')
    def test_unlock_obj(self, mock_set_object_state):
        event = Mock()
        data = [
            (Mock(stack=['running']), mock_set_object_state.assert_called_once),
            (Mock(stack=[]), mock_set_object_state.assert_not_called),
            (Mock(stack=''), mock_set_object_state.assert_not_called),
        ]

        for obj, check_assert in data:
            with self.subTest(obj=obj):

                job_module.unlock_obj(obj, event)

                check_assert()
                mock_set_object_state.reset_mock()

    @patch('cm.job.unlock_obj')
    def test_unlock_objects(self, mock_unlock_obj):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype, cluster=cluster)
        host_provider = models.HostProvider.objects.create(prototype=prototype)
        adcm = models.ADCM.objects.create(prototype=prototype)

        data = [cluster_object, host, host_provider, adcm, cluster]
        event = Mock()

        for obj in data:
            with self.subTest(obj=obj):

                job_module.unlock_objects(obj, event)

                if isinstance(obj, models.ClusterObject):
                    mock_unlock_obj.assert_has_calls([
                        call(obj, event),
                        call(cluster, event),
                        call(host, event)
                    ])
                if isinstance(obj, models.Host):
                    mock_unlock_obj.assert_has_calls([
                        call(obj, event),
                        call(obj.cluster, event),
                        call(cluster_object, event),
                    ])
                if isinstance(obj, models.HostProvider):
                    mock_unlock_obj.assert_has_calls([
                        call(obj, event)
                    ])
                if isinstance(obj, models.ADCM):
                    mock_unlock_obj.assert_has_calls([
                        call(obj, event)
                    ])
                if isinstance(obj, models.Cluster):
                    mock_unlock_obj.assert_has_calls([
                        call(obj, event),
                        call(cluster_object, event),
                        call(host, event),
                    ])
                mock_unlock_obj.reset_mock()

    @patch('cm.job.api.save_hc')
    def test_restore_hc(self, mock_save_hc):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype, cluster=cluster)
        component = models.Component.objects.create(prototype=prototype)
        service_component = models.ServiceComponent.objects.create(
            cluster=cluster, service=cluster_object, component=component)
        hostcomponentmap = [
            {
                'host_id': host.id,
                'service_id': cluster_object.id,
                'component_id': service_component.id
            }
        ]
        action = models.Action.objects.create(
            prototype=prototype, hostcomponentmap=hostcomponentmap)
        task = models.TaskLog.objects.create(
            action_id=action.id, object_id=cluster.id,
            start_date=timezone.now(), finish_date=timezone.now(),
            selector={'cluster': cluster.id},
            hostcomponentmap=hostcomponentmap)

        job_module.restore_hc(task, action, config.Job.FAILED)

        mock_save_hc.assert_called_once_with(cluster, [(cluster_object, host, service_component)])

    @patch('cm.job.err')
    def test_check_selector(self, mock_err):
        selector = job_module.check_selector({'cluster': 1}, 'cluster')
        self.assertEqual(selector, 1)
        self.assertEqual(mock_err.call_count, 0)

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

    def test_get_action_context(self):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle, type='cluster')
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype, cluster=cluster)
        host_provider = models.HostProvider.objects.create(prototype=prototype)
        adcm = models.ADCM.objects.create(prototype=prototype)
        action = models.Action.objects.create(prototype=prototype)

        data = [
            ({'cluster': cluster.id}, 'service', cluster_object, cluster),
            ({'host': host.id}, 'host', host, cluster),
            ({'cluster': cluster.id}, 'cluster', cluster, cluster),
            ({'provider': cluster.id}, 'provider', host_provider, None),
            ({'adcm': cluster.id}, 'adcm', adcm, None),
        ]

        for selector, prototype_type, test_obj, test_cluster in data:
            with self.subTest(selector=selector, prototype_type=prototype_type):
                prototype.type = prototype_type
                prototype.save()

                obj, _cluster, _provider = job_module.get_action_context(action, selector)

                self.assertEqual(obj, test_obj)
                self.assertEqual(_cluster, test_cluster)

    @patch('cm.job.prepare_ansible_config')
    @patch('cm.job.prepare_job_config')
    @patch('cm.job.inventory.prepare_job_inventory')
    def test_prepare_job(self, mock_prepare_job_inventory, mock_prepare_job_config,
                         mock_prepare_ansible_config):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        action = models.Action.objects.create(prototype=prototype)
        job = models.JobLog.objects.create(
            action_id=action.id, start_date=timezone.now(), finish_date=timezone.now())

        job_module.prepare_job(action, None, {'cluster': 1}, job.id, cluster, '', {}, None)

        mock_prepare_job_inventory.assert_called_once_with({'cluster': 1}, job.id, {}, None)
        mock_prepare_job_config.assert_called_once_with(action, None, {'cluster': 1},
                                                        job.id, cluster, '')
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
        data = [
            ({'cluster': 1}, {'type': 'cluster', 'cluster_id': 1}),
            ({'service': 1}, {'type': 'service', 'service_id': 1}),
            ({'provider': 1}, {'type': 'provider', 'provider_id': 1}),
            ({'host': 1}, {'type': 'host', 'host_id': 1}),
            ({'adcm': 1}, {'type': 'adcm', 'adcm_id': 1}),
        ]

        for selector, test_context in data:
            with self.subTest(selector=selector):
                context = job_module.prepare_context(selector)
                self.assertDictEqual(context, test_context)

    def test_get_bundle_root(self):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        action = models.Action.objects.create(prototype=prototype)

        data = [
            ('adcm', os.path.join(config.BASE_DIR, 'conf')),
            ('', config.BUNDLE_DIR)
        ]

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
            (sub_action, 'main.yaml', os.path.join(
                config.BUNDLE_DIR, action.prototype.bundle.hash, 'ansible/sleep.yaml')),
            (None, 'main.yaml', os.path.join(
                config.BUNDLE_DIR, action.prototype.bundle.hash, 'main.yaml')),
            (None, './main.yaml', os.path.join(
                config.BUNDLE_DIR, action.prototype.bundle.hash, 'main.yaml')),
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
    def test_prepare_job_config(self, mock_open, mock_dump, mock_get_adcm_config,
                                mock_prepare_context, mock_get_bundle_root, mock_cook_script):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        action = models.Action.objects.create(prototype=prototype)
        adcm = models.ADCM.objects.create(prototype=prototype)

        fd = Mock()
        mock_open.return_value = fd
        mock_get_adcm_config.return_value = {}
        mock_prepare_context.return_value = {'type': 'cluster', 'cluster_id': 1}
        mock_get_bundle_root.return_value = config.BUNDLE_DIR
        mock_cook_script.return_value = os.path.join(
            config.BUNDLE_DIR, action.prototype.bundle.hash, action.script)

        job = models.JobLog.objects.create(
            action_id=action.id, start_date=timezone.now(), finish_date=timezone.now())

        action.params = {'ansible_tags': 'create_users'}
        action.save()
        sub_action = models.SubAction(action=action)
        selector = {'cluster': 1}
        conf = 'test'
        provider = models.HostProvider(prototype=prototype)
        host = models.Host(prototype=prototype, provider=provider)
        provider = models.HostProvider(prototype=prototype)

        data = [
            ('service', cluster_object),
            ('cluster', cluster),
            ('host', host),
            ('provider', provider),
            ('adcm', adcm),
        ]

        for prototype_type, obj in data:
            with self.subTest(provider_type=prototype_type, obj=obj):
                prototype.type = prototype_type
                prototype.save()

                job_module.prepare_job_config(
                    action, sub_action, selector, job.id, obj, conf)

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
                        'tmp_dir': os.path.join(config.RUN_DIR, f'{job.id}', 'tmp'),
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
                    '{}/{}/config.json'.format(config.RUN_DIR, job.id), 'w')
                mock_dump.assert_called_with(job_config, fd, indent=3, sort_keys=True)
                mock_get_adcm_config.assert_called()
                mock_prepare_context.assert_called_with({'cluster': 1})
                mock_get_bundle_root.assert_called_with(action)
                mock_cook_script.assert_called_with(action, sub_action)

    @patch('cm.job.cook_delta')
    @patch('cm.job.get_old_hc')
    @patch('cm.job.get_new_hc')
    @patch('cm.job.prepare_job')
    def test_re_prepare_job(self, mock_prepare_job, mock_get_new_hc,
                            mock_get_old_hc, mock_cook_delta):
        new_hc = Mock()
        mock_get_new_hc.return_value = new_hc
        old_hc = Mock()
        mock_get_old_hc.return_value = old_hc
        delta = Mock()
        mock_cook_delta.return_value = delta

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle, type='cluster')
        cluster = models.Cluster.objects.create(prototype=prototype)
        cluster_object = models.ClusterObject.objects.create(prototype=prototype, cluster=cluster)
        host = models.Host.objects.create(prototype=prototype, cluster=cluster)
        component = models.Component.objects.create(prototype=prototype)
        service_component = models.ServiceComponent.objects.create(
            cluster=cluster, service=cluster_object, component=component)
        action = models.Action.objects.create(
            prototype=prototype,
            hostcomponentmap=[{'service': '', 'component': '', 'action': ''}])
        sub_action = models.SubAction.objects.create(action=action)
        hostcomponentmap = [
            {
                'host_id': host.id,
                'service_id': cluster_object.id,
                'component_id': service_component.id
            }
        ]
        selector = {'cluster': cluster.id}
        task = models.TaskLog.objects.create(
            action_id=action.id, object_id=1, start_date=timezone.now(),
            finish_date=timezone.now(), hostcomponentmap=hostcomponentmap,
            selector=selector,
            config={"sleeptime": 1})
        job = models.JobLog.objects.create(
            task_id=task.id, action_id=action.id, sub_action_id=sub_action.id,
            start_date=timezone.now(), finish_date=timezone.now())

        job_module.re_prepare_job(task, job)

        mock_get_new_hc.assert_called_once_with(cluster)
        mock_get_old_hc.assert_called_once_with(task.hostcomponentmap)
        mock_cook_delta.assert_called_once_with(
            cluster, new_hc, action.hostcomponentmap, old_hc)
        mock_prepare_job.assert_called_once_with(
            action, sub_action, selector, job.id, cluster,
            task.config, delta, None)
