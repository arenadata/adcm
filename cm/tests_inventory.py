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
from unittest.mock import patch, Mock, call

from django.test import TestCase

import cm.inventory
from cm.models import (
    ObjectConfig, ConfigLog, Prototype, Bundle, Cluster, HostProvider, Host
)


class TestInventory(TestCase):

    def setUp(self):
        pass

    @patch('cm.inventory.cook_file_type_name')
    @patch('cm.inventory.get_prototype_config')
    def test_process_config(self, mock_get_prototype_config, mock_cook_file_type_name):
        mock_cook_file_type_name.return_value = 'data_from_file'
        obj_mock = Mock()
        obj_mock.prototype = Mock()

        test_data = [
            (
                {'global': ''},
                ({'global': {'type': 'file'}}, {}, {}, {}),
                None,
                {'global': 'data_from_file'}
            ),
            (
                {'global': {'test': ''}},
                ({'global': {'test': {'type': 'file'}}}, {}, {}, {}),
                None,
                {'global': {'test': 'data_from_file'}}
            ),
            (
                {},
                ({}, {}, {}, {}),
                '{"global": {"active": false}}',
                {'global': None}
            ),
        ]

        for conf, spec, attr, test_conf in test_data:
            with self.subTest(conf=conf, spec=spec, attr=attr):
                mock_get_prototype_config.return_value = spec

                config = cm.inventory.process_config(obj_mock, conf, attr)

                self.assertDictEqual(config, test_conf)

        mock_get_prototype_config.assert_has_calls([
            call(obj_mock.prototype),
            call(obj_mock.prototype),
            call(obj_mock.prototype),
        ])
        mock_cook_file_type_name.assert_has_calls([
            call(obj_mock, 'global', ''),
            call(obj_mock, 'global', 'test'),
        ])

    def test_get_import(self):
        pass

    @patch('cm.inventory.process_config')
    def test_get_obj_config(self, mock_process_config):
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        object_config = ObjectConfig.objects.create(current=1, previous=1)
        cluster = Cluster.objects.create(prototype=prototype, config=object_config)
        config_log = ConfigLog.objects.create(obj_ref=object_config, config='{}')

        cm.inventory.get_obj_config(cluster)
        mock_process_config.assert_called_once_with(
            cluster, json.loads(config_log.config), config_log.attr)

    @patch('cm.inventory.get_import')
    @patch('cm.inventory.get_obj_config')
    def test_get_cluster_config(self, mock_get_obj_config, mock_get_import):
        mock_get_obj_config.return_value = {}
        mock_get_import.return_value = {}

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        object_config = ObjectConfig.objects.create(current=1, previous=1)
        cluster = Cluster.objects.create(prototype=prototype, config=object_config)

        res = cm.inventory.get_cluster_config(cluster.id)
        test_res = {
            'cluster': {
                'config': {},
                'name': '',
                'id': 1
            },
            'services': {}
        }
        self.assertDictEqual(res, test_res)

        mock_get_obj_config.assert_called_once_with(cluster)
        mock_get_import.assert_called_once_with(cluster)

    @patch('cm.inventory.get_obj_config')
    def test_get_provider_config(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle, type='host')
        object_config = ObjectConfig.objects.create(current=1, previous=1)
        provider = HostProvider.objects.create(prototype=prototype, config=object_config)

        config = cm.inventory.get_provider_config(provider.id)

        test_config = {
            'provider': {
                'config': {},
                'name': '',
                'id': 1,
                'host_prototype_id': 1
            }
        }
        self.assertDictEqual(config, test_config)
        mock_get_obj_config.assert_called_once_with(provider)

    @patch('cm.inventory.get_obj_config')
    def test_get_host_groups(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        object_config = ObjectConfig.objects.create(current=1, previous=1)
        cluster = Cluster.objects.create(prototype=prototype, config=object_config)

        groups = cm.inventory.get_host_groups(cluster.id, {})

        self.assertDictEqual(groups, {})
        mock_get_obj_config.assert_not_called()

    @patch('cm.inventory.get_obj_config')
    def test_get_host(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}
        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        host = Host.objects.create(prototype=prototype, fqdn='test')
        host_list = [host]

        qroup = cm.inventory.get_hosts(host_list)

        test_group = {
            'test': {
                'adcm_hostid': 1
            }
        }
        self.assertDictEqual(qroup, test_group)
        mock_get_obj_config.assert_called_once_with(host)

    @patch('cm.inventory.get_hosts')
    @patch('cm.inventory.get_cluster_config')
    def test_get_cluster_hosts(self, mock_get_cluster_config, mock_get_hosts):
        mock_get_cluster_config.return_value = []
        mock_get_hosts.return_value = []

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        cluster = Cluster.objects.create(prototype=prototype)

        test_cluster_hosts = {
            'CLUSTER': {
                'hosts': [],
                'vars': []
            }
        }

        cluster_hosts = cm.inventory.get_cluster_hosts(cluster.id)

        self.assertDictEqual(cluster_hosts, test_cluster_hosts)
        mock_get_hosts.assert_called_once()
        mock_get_cluster_config.assert_called_once_with(cluster.id)

    @patch('cm.inventory.get_provider_config')
    @patch('cm.inventory.get_hosts')
    def test_get_provider_hosts(self, mock_get_hosts, mock_get_provider_config):
        mock_get_hosts.return_value = []
        mock_get_provider_config.return_value = []

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        provider = HostProvider.objects.create(prototype=prototype)
        Host.objects.create(prototype=prototype, provider=provider)

        provider_hosts = cm.inventory.get_provider_hosts(provider.id)

        test_provider_hosts = {
            'PROVIDER': {
                'hosts': [],
                'vars': []
            }
        }

        self.assertDictEqual(provider_hosts, test_provider_hosts)
        mock_get_hosts.assert_called_once()
        mock_get_provider_config.assert_called_once_with(provider.id)

    @patch('cm.inventory.get_provider_hosts')
    @patch('cm.inventory.get_hosts')
    def test_get_host(self, mock_get_hosts, mock_get_provider_hosts):
        mock_get_hosts.return_value = []
        mock_get_provider_hosts.return_value = {
            'PROVIDER': {
                'hosts': [],
                'vars': []
            }
        }

        bundle = Bundle.objects.create()
        prototype = Prototype.objects.create(bundle=bundle)
        provider = HostProvider.objects.create(prototype=prototype)
        host = Host.objects.create(prototype=prototype, provider=provider)

        groups = cm.inventory.get_host(host.id)
        test_groups = {
            'HOST': {
                'hosts': []
            },
            'PROVIDER': {
                'hosts': [],
                'vars': []
            }
        }
        self.assertDictEqual(groups, test_groups)
        mock_get_hosts.assert_called_once_with([host])
        mock_get_provider_hosts.assert_called_once_with(host.provider.id)
