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

import cm.inventory
from cm import models


class TestInventory(TestCase):
    # pylint: disable=too-many-locals

    def setUp(self):
        pass

    @patch('cm.inventory.process_config')
    @patch('cm.inventory.get_prototype_config')
    def test_process_config_and_attr(self, mock_get_prototype_config, mock_process_config):
        mock_get_prototype_config.return_value = ({}, {}, {}, {})
        mock_process_config.return_value = {}
        obj_mock = Mock(prototype={})

        attr = {"global": {"active": ""}}
        conf = cm.inventory.process_config_and_attr(obj_mock, {}, attr)

        self.assertDictEqual(conf, {'global': None})
        mock_get_prototype_config.assert_called_once_with({})
        mock_process_config.assert_called_once_with(obj_mock, {}, {})

    @patch('cm.inventory.process_config_and_attr')
    def test_get_obj_config(self, mock_process_config_and_attr):
        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        object_config = models.ObjectConfig.objects.create(current=1, previous=1)
        cluster = models.Cluster.objects.create(prototype=prototype, config=object_config)
        config_log = models.ConfigLog.objects.create(obj_ref=object_config, config='{}')

        cm.inventory.get_obj_config(cluster)
        mock_process_config_and_attr.assert_called_once_with(
            cluster, config_log.config, config_log.attr
        )

    @patch('cm.inventory.get_import')
    @patch('cm.inventory.get_obj_config')
    def test_get_cluster_config(self, mock_get_obj_config, mock_get_import):
        mock_get_obj_config.return_value = {}
        mock_get_import.return_value = {}

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle, version="2.2")
        object_config = models.ObjectConfig.objects.create(current=1, previous=1)
        cluster = models.Cluster.objects.create(prototype=prototype, config=object_config)

        res = cm.inventory.get_cluster_config(cluster)
        test_res = {
            'cluster': {
                'config': {},
                'edition': 'community',
                'name': '',
                'id': 1,
                'version': '2.2',
                'state': 'created',
                'multi_state': [],
                'before_upgrade': {'state': None},
            },
            'services': {},
        }
        self.assertDictEqual(res, test_res)

        mock_get_obj_config.assert_called_once_with(cluster)
        mock_get_import.assert_called_once_with(cluster)

    @patch('cm.inventory.get_obj_config')
    def test_get_provider_config(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle, type='host')
        object_config = models.ObjectConfig.objects.create(current=1, previous=1)
        provider = models.HostProvider.objects.create(prototype=prototype, config=object_config)

        config = cm.inventory.get_provider_config(provider.id)

        test_config = {
            'provider': {
                'config': {},
                'name': '',
                'id': 1,
                'host_prototype_id': 1,
                'state': 'created',
                'multi_state': [],
                'before_upgrade': {'state': None},
            }
        }
        self.assertDictEqual(config, test_config)
        mock_get_obj_config.assert_called_once_with(provider)

    @patch('cm.inventory.get_obj_config')
    def test_get_host_groups(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        object_config = models.ObjectConfig.objects.create(current=1, previous=1)
        cluster = models.Cluster.objects.create(prototype=prototype, config=object_config)

        groups = cm.inventory.get_host_groups(cluster, {})

        self.assertDictEqual(groups, {})
        mock_get_obj_config.assert_not_called()

    @patch('cm.inventory.get_hosts')
    @patch('cm.inventory.get_cluster_config')
    def test_get_cluster_hosts(self, mock_get_cluster_config, mock_get_hosts):
        mock_get_cluster_config.return_value = []
        mock_get_hosts.return_value = []

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        cluster = models.Cluster.objects.create(prototype=prototype)

        test_cluster_hosts = {'CLUSTER': {'hosts': [], 'vars': []}}

        cluster_hosts = cm.inventory.get_cluster_hosts(cluster)

        self.assertDictEqual(cluster_hosts, test_cluster_hosts)
        mock_get_hosts.assert_called_once()
        mock_get_cluster_config.assert_called_once_with(cluster)

    @patch('cm.inventory.get_hosts')
    def test_get_provider_hosts(self, mock_get_hosts):
        mock_get_hosts.return_value = []

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle)
        provider = models.HostProvider.objects.create(prototype=prototype)
        models.Host.objects.create(prototype=prototype, provider=provider)

        provider_hosts = cm.inventory.get_provider_hosts(provider)

        test_provider_hosts = {'PROVIDER': {'hosts': []}}

        self.assertDictEqual(provider_hosts, test_provider_hosts)
        mock_get_hosts.assert_called_once()

    @patch('cm.inventory.get_provider_hosts')
    @patch('cm.inventory.get_hosts')
    def test_get_host(self, mock_get_hosts, mock_get_provider_hosts):
        mock_get_hosts.return_value = []
        mock_get_provider_hosts.return_value = {'PROVIDER': {'hosts': [], 'vars': []}}

        bundle = models.Bundle.objects.create()
        prototype = models.Prototype.objects.create(bundle=bundle, type='host')
        provider = models.HostProvider.objects.create(prototype=prototype)
        host = models.Host.objects.create(prototype=prototype, provider=provider)

        groups = cm.inventory.get_host(host.id)
        test_groups = {
            'HOST': {
                'hosts': [],
                'vars': {
                    'provider': {
                        'config': {},
                        'name': '',
                        'id': 1,
                        'host_prototype_id': 1,
                        'state': 'created',
                        'multi_state': [],
                        'before_upgrade': {'state': None},
                    }
                },
            }
        }
        self.assertDictEqual(groups, test_groups)
        mock_get_hosts.assert_called_once_with([host], host)

    @patch('json.dump')
    @patch('cm.inventory.open')
    def test_prepare_job_inventory(self, mock_open, mock_dump):
        bundle = models.Bundle.objects.create(edition='community')
        proto1 = models.Prototype.objects.create(bundle=bundle, version='2.2', type='cluster')
        cluster = models.Cluster.objects.create(prototype=proto1)
        proto2 = models.Prototype.objects.create(bundle=bundle, type='provider')
        host_provider = models.HostProvider.objects.create(prototype=proto2)
        proto3 = models.Prototype.objects.create(bundle=bundle, type='host')
        host = models.Host.objects.create(prototype=proto3, provider=host_provider)
        host2 = models.Host.objects.create(
            prototype=proto3, fqdn='h2', cluster=cluster, provider=host_provider
        )
        action = models.Action.objects.create(prototype=proto1)
        job = models.JobLog.objects.create(
            action=action, start_date=timezone.now(), finish_date=timezone.now()
        )

        fd = Mock()
        mock_open.return_value = fd
        cluster_inv = {
            'all': {
                'children': {
                    'CLUSTER': {
                        'hosts': {
                            host2.fqdn: {'adcm_hostid': 2, 'state': 'created', 'multi_state': []}
                        },
                        'vars': {
                            'cluster': {
                                'config': {},
                                'name': '',
                                'id': 1,
                                'version': '2.2',
                                'edition': 'community',
                                'state': 'created',
                                'multi_state': [],
                                'before_upgrade': {'state': None},
                            },
                            'services': {},
                        },
                    }
                }
            }
        }
        host_inv = {
            'all': {
                'children': {
                    'HOST': {
                        'hosts': {'': {'adcm_hostid': 1, 'state': 'created', 'multi_state': []}},
                        'vars': {
                            'provider': {
                                'config': {},
                                'name': '',
                                'id': 1,
                                'host_prototype_id': proto3.id,
                                'state': 'created',
                                'multi_state': [],
                                'before_upgrade': {'state': None},
                            }
                        },
                    }
                }
            }
        }
        provider_inv = {
            'all': {
                'children': {
                    'PROVIDER': {
                        'hosts': {
                            '': {'adcm_hostid': 1, 'state': 'created', 'multi_state': []},
                            'h2': {'adcm_hostid': 2, 'state': 'created', 'multi_state': []},
                        }
                    }
                },
                'vars': {
                    'provider': {
                        'config': {},
                        'name': '',
                        'id': 1,
                        'host_prototype_id': proto3.id,
                        'state': 'created',
                        'multi_state': [],
                        'before_upgrade': {'state': None},
                    }
                },
            }
        }

        data = [
            (host, host_inv),
            (host_provider, provider_inv),
            (cluster, cluster_inv),
        ]

        for obj, inv in data:
            with self.subTest(obj=obj, inv=inv):
                cm.inventory.prepare_job_inventory(obj, job.id, action, [])
                mock_dump.assert_called_once_with(inv, fd, indent=3)
                mock_dump.reset_mock()