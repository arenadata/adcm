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

from unittest.mock import Mock, patch

from cm.api import update_obj_config
from cm.inventory import (
    get_cluster_config,
    get_cluster_hosts,
    get_host,
    get_host_groups,
    get_host_vars,
    get_obj_config,
    get_provider_config,
    get_provider_hosts,
    prepare_job_inventory,
    process_config_and_attr,
)
from cm.models import Action, ConfigLog, Host, JobLog
from cm.tests.utils import (
    gen_bundle,
    gen_cluster,
    gen_component,
    gen_config,
    gen_group,
    gen_host,
    gen_host_component,
    gen_prototype,
    gen_prototype_config,
    gen_provider,
    gen_service,
)
from django.utils import timezone

from adcm.tests.base import BaseTestCase


class TestInventory(BaseTestCase):
    # pylint: disable=too-many-instance-attributes

    def setUp(self):
        super().setUp()

        self.cluster_bundle = gen_bundle()
        self.cluster_pt = gen_prototype(self.cluster_bundle, "cluster", "cluster")
        self.cluster = gen_cluster(prototype=self.cluster_pt, config=gen_config(), name="cluster")

        self.provider_bundle = gen_bundle()

        self.provider_pt = gen_prototype(self.provider_bundle, "provider")
        self.host_pt = gen_prototype(self.provider_bundle, "host")

        self.provider = gen_provider(prototype=self.provider_pt)
        self.host = gen_host(self.provider, prototype=self.host_pt)

    @patch("cm.inventory.process_config")
    @patch("cm.inventory.get_prototype_config")
    def test_process_config_and_attr(self, mock_get_prototype_config, mock_process_config):
        mock_get_prototype_config.return_value = ({}, {}, {}, {})
        mock_process_config.return_value = {}
        obj_mock = Mock(prototype={})

        attr = {"global": {"active": ""}}
        conf = process_config_and_attr(obj_mock, {}, attr)

        self.assertDictEqual(conf, {"global": None})

        mock_get_prototype_config.assert_called_once_with(proto={})
        mock_process_config.assert_called_once_with(obj=obj_mock, spec={}, old_conf={})

    @patch("cm.inventory.process_config_and_attr")
    def test_get_obj_config(self, mock_process_config_and_attr):
        get_obj_config(self.cluster)
        config_log = ConfigLog.objects.get(id=self.cluster.config.current)
        mock_process_config_and_attr.assert_called_once_with(
            obj=self.cluster, conf=config_log.config, attr=config_log.attr
        )

    @patch("cm.inventory.get_import")
    @patch("cm.inventory.get_obj_config")
    def test_get_cluster_config(self, mock_get_obj_config, mock_get_import):
        mock_get_obj_config.return_value = {}
        mock_get_import.return_value = {}
        res = get_cluster_config(self.cluster)
        test_res = {
            "cluster": {
                "config": {},
                "edition": "community",
                "name": self.cluster.name,
                "id": self.cluster.pk,
                "version": "1.0.0",
                "state": "created",
                "multi_state": [],
                "before_upgrade": {"state": None},
            },
            "services": {},
        }
        self.assertDictEqual(res, test_res)

        mock_get_obj_config.assert_called_once_with(self.cluster)
        mock_get_import.assert_called_once_with(cluster=self.cluster)

    @patch("cm.inventory.get_obj_config")
    def test_get_provider_config(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}
        config = get_provider_config(self.provider.id)

        test_config = {
            "provider": {
                "config": {},
                "name": self.provider.name,
                "id": self.provider.pk,
                "host_prototype_id": self.host_pt.pk,
                "state": "created",
                "multi_state": [],
                "before_upgrade": {"state": None},
            }
        }

        self.assertDictEqual(config, test_config)
        mock_get_obj_config.assert_called_once_with(self.provider)

    @patch("cm.inventory.get_obj_config")
    def test_get_host_groups(self, mock_get_obj_config):
        mock_get_obj_config.return_value = {}

        groups = get_host_groups(cluster=self.cluster)

        self.assertDictEqual(groups, {})
        mock_get_obj_config.assert_not_called()

    @patch("cm.inventory.get_hosts")
    @patch("cm.inventory.get_cluster_config")
    def test_get_cluster_hosts(self, mock_get_cluster_config, mock_get_hosts):
        mock_get_cluster_config.return_value = []
        mock_get_hosts.return_value = []

        test_cluster_hosts = {"CLUSTER": {"hosts": [], "vars": []}}

        cluster_hosts = get_cluster_hosts(self.cluster)

        self.assertDictEqual(cluster_hosts, test_cluster_hosts)
        mock_get_hosts.assert_called_once()
        mock_get_cluster_config.assert_called_once_with(self.cluster)

    @patch("cm.inventory.get_hosts")
    def test_get_provider_hosts(self, mock_get_hosts):
        mock_get_hosts.return_value = []

        provider_hosts = get_provider_hosts(self.provider)

        test_provider_hosts = {"PROVIDER": {"hosts": []}}

        self.assertDictEqual(provider_hosts, test_provider_hosts)
        mock_get_hosts.assert_called_once()

    @patch("cm.inventory.get_provider_hosts")
    @patch("cm.inventory.get_hosts")
    def test_get_host(self, mock_get_hosts, mock_get_provider_hosts):
        mock_get_hosts.return_value = []
        mock_get_provider_hosts.return_value = {"PROVIDER": {"hosts": [], "vars": []}}

        groups = get_host(self.host.id)
        test_groups = {
            "HOST": {
                "hosts": [],
                "vars": {
                    "provider": {
                        "config": {},
                        "name": self.provider.name,
                        "id": self.provider.pk,
                        "host_prototype_id": self.host_pt.pk,
                        "state": "created",
                        "multi_state": [],
                        "before_upgrade": {"state": None},
                    }
                },
            }
        }
        self.assertDictEqual(groups, test_groups)
        mock_get_hosts.assert_called_once_with([self.host], self.host)

    @patch("json.dump")
    @patch("cm.inventory.open")
    def test_prepare_job_inventory(self, mock_open, mock_dump):
        # pylint: disable=too-many-locals

        host2 = Host.objects.create(prototype=self.host_pt, fqdn="h2", cluster=self.cluster, provider=self.provider)
        action = Action.objects.create(prototype=self.cluster_pt)
        job = JobLog.objects.create(action=action, start_date=timezone.now(), finish_date=timezone.now())

        file_mock = Mock()
        mock_open.return_value = file_mock
        cluster_inv = {
            "all": {
                "children": {
                    "CLUSTER": {
                        "hosts": {
                            host2.fqdn: {
                                "adcm_hostid": host2.pk,
                                "state": "created",
                                "multi_state": [],
                            }
                        },
                        "vars": {
                            "cluster": {
                                "config": {},
                                "name": "cluster",
                                "id": self.cluster.pk,
                                "version": "1.0.0",
                                "edition": "community",
                                "state": "created",
                                "multi_state": [],
                                "before_upgrade": {"state": None},
                            },
                            "services": {},
                        },
                    }
                }
            }
        }
        host_inv = {
            "all": {
                "children": {
                    "HOST": {
                        "hosts": {
                            self.host.fqdn: {
                                "adcm_hostid": self.host.pk,
                                "state": "created",
                                "multi_state": [],
                            }
                        },
                        "vars": {
                            "provider": {
                                "config": {},
                                "name": self.provider.name,
                                "id": self.provider.pk,
                                "host_prototype_id": self.host_pt.pk,
                                "state": "created",
                                "multi_state": [],
                                "before_upgrade": {"state": None},
                            }
                        },
                    }
                }
            }
        }
        provider_inv = {
            "all": {
                "children": {
                    "PROVIDER": {
                        "hosts": {
                            self.host.fqdn: {
                                "adcm_hostid": self.host.pk,
                                "state": "created",
                                "multi_state": [],
                            },
                            "h2": {"adcm_hostid": host2.pk, "state": "created", "multi_state": []},
                        }
                    }
                },
                "vars": {
                    "provider": {
                        "config": {},
                        "name": self.provider.name,
                        "id": self.provider.pk,
                        "host_prototype_id": self.host_pt.pk,
                        "state": "created",
                        "multi_state": [],
                        "before_upgrade": {"state": None},
                    }
                },
            }
        }

        data = [
            (self.host, host_inv),
            (self.provider, provider_inv),
            (self.cluster, cluster_inv),
        ]

        for obj, inv in data:
            with self.subTest(obj=obj, inv=inv):
                prepare_job_inventory(obj=obj, job_id=job.id, action=action)
                mock_dump.assert_called_once_with(obj=inv, fp=file_mock, indent=3)
                mock_dump.reset_mock()

    def test_host_vars(self):
        # pylint: disable=too-many-locals

        service_pt_1 = gen_prototype(self.cluster_bundle, "service", "service_1")
        service_pt_2 = gen_prototype(self.cluster_bundle, "service", "service_2")
        component_pt_11 = gen_prototype(self.cluster_bundle, "component", "component_11")
        component_pt_12 = gen_prototype(self.cluster_bundle, "component", "component_12")
        component_pt_21 = gen_prototype(self.cluster_bundle, "component", "component_21")

        prototypes = [
            self.cluster_pt,
            service_pt_1,
            service_pt_2,
            component_pt_11,
            component_pt_12,
            component_pt_21,
        ]
        for proto in prototypes:
            gen_prototype_config(
                prototype=proto,
                name="some_string",
                field_type="string",
                group_customization=True,
            )
        update_obj_config(self.cluster.config, conf={"some_string": "some_string"}, attr={})
        service_1 = gen_service(
            self.cluster,
            prototype=service_pt_1,
            config=gen_config({"some_string": "some_string"}),
        )
        service_2 = gen_service(
            self.cluster,
            prototype=service_pt_2,
            config=gen_config({"some_string": "some_string"}),
        )
        component_11 = gen_component(
            service_1,
            prototype=component_pt_11,
            config=gen_config({"some_string": "some_string"}),
        )
        component_12 = gen_component(
            service_1,
            prototype=component_pt_12,
            config=gen_config({"some_string": "some_string"}),
        )
        component_21 = gen_component(
            service_2,
            prototype=component_pt_21,
            config=gen_config({"some_string": "some_string"}),
        )

        self.host.cluster = self.cluster
        self.host.save()
        gen_host_component(component_11, self.host)
        gen_host_component(component_12, self.host)
        gen_host_component(component_21, self.host)

        groups = [
            gen_group("cluster", self.cluster.id, "cluster"),
            gen_group("service_1", service_1.id, "clusterobject"),
            gen_group("service_2", service_2.id, "clusterobject"),
            gen_group("component_1", component_11.id, "servicecomponent"),
        ]
        for group in groups:
            group.hosts.add(self.host)
            update_obj_config(group.config, {"some_string": group.name}, {"group_keys": {"some_string": True}})

        self.assertDictEqual(get_host_vars(self.host, self.cluster)["cluster"]["config"], {"some_string": "cluster"})

        service_1_host_vars = get_host_vars(self.host, service_1)

        self.assertDictEqual(service_1_host_vars["services"]["service_1"]["config"], {"some_string": "service_1"})
        self.assertDictEqual(service_1_host_vars["services"]["service_2"]["config"], {"some_string": "service_2"})
        self.assertDictEqual(
            service_1_host_vars["services"]["service_1"]["component_11"]["config"],
            {"some_string": "component_1"},
        )
        self.assertDictEqual(
            service_1_host_vars["services"]["service_1"]["component_12"]["config"],
            {"some_string": "some_string"},
        )
        self.assertDictEqual(
            service_1_host_vars["services"]["service_2"]["component_21"]["config"],
            {"some_string": "some_string"},
        )

        component_11_host_vars = get_host_vars(self.host, component_11)

        self.assertDictEqual(component_11_host_vars["services"]["service_1"]["config"], {"some_string": "service_1"})
        self.assertDictEqual(
            component_11_host_vars["services"]["service_1"]["component_11"]["config"],
            {"some_string": "component_1"},
        )
        self.assertDictEqual(
            component_11_host_vars["services"]["service_1"]["component_12"]["config"],
            {"some_string": "some_string"},
        )
        self.assertIn("service_2", component_11_host_vars["services"].keys())

        component_12_host_vars = get_host_vars(self.host, component_12)

        self.assertDictEqual(
            component_12_host_vars["services"]["service_1"]["component_12"]["config"],
            {"some_string": "some_string"},
        )
