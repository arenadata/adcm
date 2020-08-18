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

import cm.api as api_module
from cm import models


class TestApi(TestCase):

    def setUp(self):
        self.bundle = models.Bundle.objects.create(**{
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

        self.prototype = models.Prototype.objects.create(**{
            'bundle_id': self.bundle.id,
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
        self.object_config = models.ObjectConfig.objects.create(**{
            'current': 1,
            'previous': 1
        })

        self.cluster = models.Cluster.objects.create(**{
            'prototype_id': self.prototype.id,
            'name': 'Fear Limpopo',
            'description': '',
            'config_id': self.object_config.id,
            'state': 'installed',
            'stack': [],
            'issue': {}
        })

    def test_push_obj(self):

        data = [
            ([], 'created'),
            ('', 'running'),
            (['created'], 'running'),
        ]

        for stack, state in data:
            with self.subTest(stack=stack, state=state):
                self.cluster.stack = stack
                self.cluster.save()

                cluster = api_module.push_obj(self.cluster, state)
                self.assertEqual(cluster.stack, [state])

    def test_set_object_state(self):
        event = Mock()
        event.set_obj_state = Mock()
        state = self.cluster.state

        cluster = api_module.set_object_state(self.cluster, 'created', event)

        self.assertTrue(cluster.state != state)
        event.set_object_state.assert_called_once_with(
            self.cluster.prototype.type, self.cluster.id, 'created')

    @patch('cm.status_api.load_service_map')
    @patch('cm.issue.save_issue')
    @patch('cm.status_api.post_event')
    def test_save_hc(self, mock_post_event, mock_save_issue, mock_load_service_map):
        cluster_object = models.ClusterObject.objects.create(
            prototype=self.prototype, cluster=self.cluster)
        host = models.Host.objects.create(prototype=self.prototype, cluster=self.cluster)
        component = models.Component.objects.create(prototype=self.prototype)
        service_component = models.ServiceComponent.objects.create(
            cluster=self.cluster, service=cluster_object, component=component)

        models.HostComponent.objects.create(
            cluster=self.cluster, host=host, service=cluster_object, component=service_component)

        host_comp_list = [(cluster_object, host, service_component)]
        hc_list = api_module.save_hc(self.cluster, host_comp_list)

        self.assertListEqual(hc_list, [models.HostComponent.objects.get(id=2)])
        mock_post_event.assert_called_once_with(
            'change_hostcomponentmap', 'cluster', self.cluster.id)
        mock_save_issue.assert_called_once_with(self.cluster)
        mock_load_service_map.assert_called_once()
