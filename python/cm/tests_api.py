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
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

import cm.api as api_module
import cm.hierarchy
from cm import models
from cm.unit_tests import utils


class TestApi(TestCase):
    def setUp(self):
        utils.gen_adcm()
        self.bundle = models.Bundle.objects.create(
            **{
                'name': 'ADB',
                'version': '2.5',
                'version_order': 4,
                'edition': 'community',
                'license': 'absent',
                'license_path': None,
                'license_hash': None,
                'hash': '2232f33c6259d44c23046fce4382f16c450f8ba5',
                'description': '',
                'date': timezone.now(),
            }
        )

        self.prototype = models.Prototype.objects.create(
            **{
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
                'description': '',
            }
        )
        self.object_config = models.ObjectConfig.objects.create(**{'current': 1, 'previous': 1})

        self.cluster = models.Cluster.objects.create(
            **{
                'prototype_id': self.prototype.id,
                'name': 'Fear Limpopo',
                'description': '',
                'config_id': self.object_config.id,
                'state': 'installed',
            }
        )

    @patch('cm.status_api.load_service_map')
    @patch('cm.issue.update_hierarchy_issues')
    @patch('cm.status_api.post_event')
    def test_save_hc(self, mock_post_event, mock_update_issues, mock_load_service_map):
        cluster_object = models.ClusterObject.objects.create(
            prototype=self.prototype, cluster=self.cluster
        )
        host = models.Host.objects.create(prototype=self.prototype, cluster=self.cluster)
        component = models.Prototype.objects.create(
            parent=self.prototype, type='component', bundle_id=self.bundle.id, name='node'
        )
        service_component = models.ServiceComponent.objects.create(
            cluster=self.cluster, service=cluster_object, prototype=component
        )

        models.HostComponent.objects.create(
            cluster=self.cluster, host=host, service=cluster_object, component=service_component
        )

        host_comp_list = [(cluster_object, host, service_component)]
        hc_list = api_module.save_hc(self.cluster, host_comp_list)

        self.assertListEqual(hc_list, [models.HostComponent.objects.get(id=2)])
        mock_post_event.assert_called_once_with(
            'change_hostcomponentmap', 'cluster', self.cluster.id
        )
        mock_update_issues.assert_called_once_with(self.cluster)
        mock_load_service_map.assert_called_once()

    @patch('cm.api.ctx')
    @patch('cm.status_api.load_service_map')
    @patch('cm.issue.update_hierarchy_issues')
    def test_save_hc__big_update__locked_hierarchy(self, mock_post, mock_load, ctx):
        """
        Update bigger HC map - move `component_2` from `host_2` to `host_3`
        On locked hierarchy (from ansible task)
        Test:
            host_1 remains the same
            host_2 is unlocked
            host_3 became locked
        """
        service = utils.gen_service(self.cluster)
        component_1 = utils.gen_component(service)
        component_2 = utils.gen_component(service)
        provider = utils.gen_provider()
        host_1 = utils.gen_host(provider, cluster=self.cluster)
        host_2 = utils.gen_host(provider, cluster=self.cluster)
        host_3 = utils.gen_host(provider, cluster=self.cluster)
        utils.gen_host_component(component_1, host_1)
        utils.gen_host_component(component_2, host_2)

        task = utils.gen_task_log(service)
        tree = cm.hierarchy.Tree(self.cluster)
        affected = (node.value for node in tree.get_all_affected(tree.built_from))
        task.lock_affected(affected)
        ctx.lock = task.lock

        # refresh due to new instances were updated in task.lock_affected()
        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()
        self.assertTrue(host_1.is_locked)
        self.assertTrue(host_2.is_locked)
        self.assertFalse(host_3.is_locked)

        new_hc_list = [
            (service, host_1, component_1),
            (service, host_3, component_2),
        ]
        api_module.save_hc(self.cluster, new_hc_list)

        # refresh due to new instances were updated in save_hc()
        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()
        self.assertTrue(host_1.is_locked)
        self.assertFalse(host_2.is_locked)
        self.assertTrue(host_3.is_locked)

    @patch('cm.status_api.load_service_map')
    @patch('cm.issue.update_hierarchy_issues')
    def test_save_hc__big_update__unlocked_hierarchy(self, mock_update, mock_load):
        """
        Update bigger HC map - move `component_2` from `host_2` to `host_3`
        On unlocked hierarchy (from API)
        Test:
            host_1 remains unlocked
            host_2 remains unlocked
            host_3 remains unlocked
        """
        service = utils.gen_service(self.cluster)
        component_1 = utils.gen_component(service)
        component_2 = utils.gen_component(service)
        provider = utils.gen_provider()
        host_1 = utils.gen_host(provider, cluster=self.cluster)
        host_2 = utils.gen_host(provider, cluster=self.cluster)
        host_3 = utils.gen_host(provider, cluster=self.cluster)
        utils.gen_host_component(component_1, host_1)
        utils.gen_host_component(component_2, host_2)

        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()
        self.assertFalse(host_1.is_locked)
        self.assertFalse(host_2.is_locked)
        self.assertFalse(host_3.is_locked)

        new_hc_list = [
            (service, host_1, component_1),
            (service, host_3, component_2),
        ]
        api_module.save_hc(self.cluster, new_hc_list)

        # refresh due to new instances were updated in save_hc()
        host_1.refresh_from_db()
        host_2.refresh_from_db()
        host_3.refresh_from_db()
        self.assertFalse(host_1.is_locked)
        self.assertFalse(host_2.is_locked)
        self.assertFalse(host_3.is_locked)
