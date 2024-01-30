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


from json import loads
from pathlib import Path
from unittest.mock import Mock, patch

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from init_db import init as init_adcm
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from cm.api import add_hc, add_service_to_cluster, update_obj_config
from cm.inventory import (
    MAINTENANCE_MODE,
    HcAclAction,
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
from cm.job import re_prepare_job
from cm.models import (
    Action,
    ClusterObject,
    ConfigLog,
    Host,
    HostComponent,
    JobLog,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
    TaskLog,
)
from cm.services.job.utils import JobScope
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


class TestInventory(BaseTestCase):
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

        mock_get_prototype_config.assert_called_once_with(prototype={})
        mock_process_config.assert_called_once_with(obj=obj_mock, spec={}, old_conf={})

    @patch("cm.inventory.process_config_and_attr")
    def test_get_obj_config(self, mock_process_config_and_attr):
        get_obj_config(self.cluster)
        config_log = ConfigLog.objects.get(id=self.cluster.config.current)
        mock_process_config_and_attr.assert_called_once_with(
            obj=self.cluster,
            conf=config_log.config,
            attr=config_log.attr,
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

        mock_get_obj_config.assert_called_once_with(obj=self.cluster)
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
            },
        }

        self.assertDictEqual(config, test_config)
        mock_get_obj_config.assert_called_once_with(obj=self.provider)

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
        mock_get_cluster_config.assert_called_once_with(cluster=self.cluster)

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
                    },
                },
            },
        }
        self.assertDictEqual(groups, test_groups)
        mock_get_hosts.assert_called_once_with(host_list=[self.host], obj=self.host)

    @patch("json.dump")
    @patch("cm.inventory.open")
    def test_prepare_job_inventory(self, mock_open, mock_dump):
        host2 = Host.objects.create(prototype=self.host_pt, fqdn="h2", cluster=self.cluster, provider=self.provider)
        action = Action.objects.create(prototype=self.cluster_pt)
        job = JobLog.objects.create(action=action, start_date=timezone.now(), finish_date=timezone.now())

        file_mock = Mock()
        file_mock.__enter__ = Mock(return_value=(Mock(), None))
        file_mock.__exit__ = Mock(return_value=None)
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
                            },
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
                    },
                },
            },
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
                            },
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
                            },
                        },
                    },
                },
            },
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
                        },
                    },
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
                    },
                },
            },
        }

        data = [
            (self.host, host_inv),
            (self.provider, provider_inv),
            (self.cluster, cluster_inv),
        ]

        for obj, inv in data:
            with self.subTest(obj=obj, inv=inv):
                prepare_job_inventory(obj=obj, job_id=job.id, action=action)
                mock_dump.assert_called_once_with(obj=inv, fp=file_mock.__enter__.return_value, separators=(",", ":"))
                mock_dump.reset_mock()

    def test_host_vars(self):
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
        update_obj_config(self.cluster.config, config={"some_string": "some_string"}, attr={})
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


class TestInventoryAndMaintenanceMode(BaseTestCase):
    def setUp(self):
        super().setUp()
        init_adcm()

        self.test_files_dir = self.base_dir / "python" / "cm" / "tests" / "files"

        _, self.cluster_hc_acl, _ = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(self.test_files_dir, "test_inventory_remove_group_mm_hosts.tar"),
            cluster_name="cluster_hc_acl",
        )

        self.provider = gen_provider(name="test_provider")
        host_prototype = gen_prototype(bundle=self.provider.prototype.bundle, proto_type="host")
        self.host_hc_acl_1 = gen_host(
            provider=self.provider, cluster=self.cluster_hc_acl, fqdn="hc_acl_host_1", prototype=host_prototype
        )
        self.host_hc_acl_2 = gen_host(
            provider=self.provider, cluster=self.cluster_hc_acl, fqdn="hc_acl_host_2", prototype=host_prototype
        )
        self.host_hc_acl_3 = gen_host(
            provider=self.provider, cluster=self.cluster_hc_acl, fqdn="hc_acl_host_3", prototype=host_prototype
        )

        self.service_hc_acl = add_service_to_cluster(
            cluster=self.cluster_hc_acl,
            proto=Prototype.objects.get(name="service_1", type="service"),
        )

        self.component_hc_acl_1 = ServiceComponent.objects.get(
            cluster=self.cluster_hc_acl, prototype__name="component_1"
        )
        self.component_hc_acl_2 = ServiceComponent.objects.get(
            cluster=self.cluster_hc_acl, prototype__name="component_2"
        )

        self.hc_c1_h1 = {
            "host_id": self.host_hc_acl_1.pk,
            "service_id": self.service_hc_acl.pk,
            "component_id": self.component_hc_acl_1.pk,
        }
        self.hc_c1_h2 = {
            "host_id": self.host_hc_acl_2.pk,
            "service_id": self.service_hc_acl.pk,
            "component_id": self.component_hc_acl_1.pk,
        }
        self.hc_c1_h3 = {
            "host_id": self.host_hc_acl_3.pk,
            "service_id": self.service_hc_acl.pk,
            "component_id": self.component_hc_acl_1.pk,
        }
        self.hc_c2_h1 = {
            "host_id": self.host_hc_acl_1.pk,
            "service_id": self.service_hc_acl.pk,
            "component_id": self.component_hc_acl_2.pk,
        }
        self.hc_c2_h2 = {
            "host_id": self.host_hc_acl_2.pk,
            "service_id": self.service_hc_acl.pk,
            "component_id": self.component_hc_acl_2.pk,
        }

        add_hc(
            cluster=self.cluster_hc_acl,
            hc_in=[self.hc_c1_h1, self.hc_c1_h2, self.hc_c1_h3, self.hc_c2_h1, self.hc_c2_h2],
        )

        self.action_hc_acl = Action.objects.get(name="cluster_action_hc_acl", allow_in_maintenance_mode=True)

        _, self.cluster_target_group, _ = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(self.test_files_dir, "cluster_mm_host_target_group.tar"),
            cluster_name="cluster_target_group",
        )

        self.host_target_group_1 = gen_host(
            provider=self.provider,
            cluster=self.cluster_target_group,
            fqdn="host_target_group_1",
            prototype=host_prototype,
        )
        self.host_target_group_2 = gen_host(
            provider=self.provider,
            cluster=self.cluster_target_group,
            fqdn="host_target_group_2",
            prototype=host_prototype,
        )

        self.service_target_group = add_service_to_cluster(
            cluster=self.cluster_target_group,
            proto=Prototype.objects.get(name="service_1_target_group", type="service"),
        )
        self.component_target_group = ServiceComponent.objects.get(
            cluster=self.cluster_target_group, prototype__name="component_1_target_group"
        )

        add_hc(
            cluster=self.cluster_target_group,
            hc_in=[
                {
                    "host_id": self.host_target_group_1.pk,
                    "service_id": self.service_target_group.pk,
                    "component_id": self.component_target_group.pk,
                },
                {
                    "host_id": self.host_target_group_2.pk,
                    "service_id": self.service_target_group.pk,
                    "component_id": self.component_target_group.pk,
                },
            ],
        )

        self.action_target_group = Action.objects.get(name="host_action_target_group", allow_in_maintenance_mode=True)

    @staticmethod
    def _get_hc_request_data(*new_hc_items: dict) -> list[dict]:
        hc_fields = ("id", "service_id", "component_id", "host_id")
        hc_request_data = []

        for host_component in new_hc_items:
            hc_values = HostComponent.objects.filter(**host_component).values_list(*hc_fields).first()
            hc_request_data.append(dict(zip(hc_fields, hc_values)))

        return hc_request_data

    def get_inventory_data(self, data: dict, kwargs: dict) -> dict:
        self.assertEqual(TaskLog.objects.count(), 0)
        self.assertEqual(JobLog.objects.count(), 0)

        response: Response = self.client.post(
            path=reverse(viewname="v1:run-task", kwargs=kwargs),
            data=data,
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        job = JobLog.objects.last()

        re_prepare_job(job_scope=JobScope(job_id=job.pk))

        inventory_file = settings.RUN_DIR / str(job.pk) / "inventory.json"
        with Path(inventory_file).open(encoding=settings.ENCODING_UTF_8) as f:
            return loads(s=f.read())["all"]["children"]

    def test_groups_remove_host_not_in_mm_success(self):
        self.host_hc_acl_3.maintenance_mode = MaintenanceMode.ON
        self.host_hc_acl_3.save()

        # remove: hc_c1_h2
        hc_request_data = self._get_hc_request_data(self.hc_c1_h1, self.hc_c1_h3, self.hc_c2_h1, self.hc_c2_h2)

        inventory_data = self.get_inventory_data(
            data={"hc": hc_request_data, "verbose": False},
            kwargs={
                "cluster_id": self.cluster_hc_acl.pk,
                "object_type": "cluster",
                "action_id": self.action_hc_acl.pk,
            },
        )

        target_key_remove = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h2['service_id']).prototype.name}"
            f".{ServiceComponent.objects.get(pk=self.hc_c1_h2['component_id']).prototype.name}"
            f".{HcAclAction.REMOVE}"
        )
        target_key_mm_service = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}.{MAINTENANCE_MODE}"
        )
        target_key_mm_service_component = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}"
            f".{ServiceComponent.objects.get(pk=self.hc_c1_h3['component_id']).prototype.name}"
            f".{MAINTENANCE_MODE}"
        )

        self.assertIn(target_key_remove, inventory_data)
        self.assertIn(self.host_hc_acl_2.fqdn, inventory_data[target_key_remove]["hosts"])

        self.assertIn(target_key_mm_service, inventory_data)
        self.assertIn(self.host_hc_acl_3.fqdn, inventory_data[target_key_mm_service]["hosts"])

        self.assertIn(target_key_mm_service_component, inventory_data)
        self.assertIn(self.host_hc_acl_3.fqdn, inventory_data[target_key_mm_service_component]["hosts"])

        remove_keys = [key for key in inventory_data if key.endswith(f".{HcAclAction.REMOVE}")]
        self.assertEqual(len(remove_keys), 1)

        mm_keys = [key for key in inventory_data if key.endswith(f".{MAINTENANCE_MODE}")]
        self.assertEqual(len(mm_keys), 2)

    def test_groups_remove_host_in_mm_success(self):
        self.host_hc_acl_3.maintenance_mode = MaintenanceMode.ON
        self.host_hc_acl_3.save()

        # remove: hc_c1_h3
        hc_request_data = self._get_hc_request_data(self.hc_c1_h1, self.hc_c1_h2, self.hc_c2_h1, self.hc_c2_h2)

        inventory_data = self.get_inventory_data(
            data={"hc": hc_request_data, "verbose": False},
            kwargs={
                "cluster_id": self.cluster_hc_acl.pk,
                "object_type": "cluster",
                "action_id": self.action_hc_acl.pk,
            },
        )

        target_key_remove = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}"
            f".{ServiceComponent.objects.get(pk=self.hc_c1_h3['component_id']).prototype.name}"
            f".{HcAclAction.REMOVE}"
        )

        self.assertIn(target_key_remove, inventory_data)
        self.assertNotIn(self.host_hc_acl_3.fqdn, inventory_data[target_key_remove]["hosts"])

        remove_keys = [key for key in inventory_data if key.endswith(f".{HcAclAction.REMOVE}")]
        self.assertEqual(len(remove_keys), 1)

        mm_keys = [key for key in inventory_data if key.endswith(f".{HcAclAction.REMOVE}.{MAINTENANCE_MODE}")]
        self.assertEqual(len(mm_keys), 1)

    def test_vars_in_mm_group(self):
        self.host_target_group_1.maintenance_mode = MaintenanceMode.ON
        self.host_target_group_1.save()

        groups = [
            gen_group(name="cluster", object_id=self.cluster_target_group.id, model_name="cluster"),
            gen_group(name="service_1", object_id=self.service_target_group.id, model_name="clusterobject"),
        ]

        for group in groups:
            group.hosts.add(self.host_target_group_1)
            update_obj_config(
                obj_conf=group.config,
                config={"some_string": group.name, "float": 0.1},
                attr={"group_keys": {"some_string": True, "float": False}},
            )

        inventory_data = self.get_inventory_data(
            data={"verbose": False},
            kwargs={
                "cluster_id": self.cluster_target_group.pk,
                "object_type": "cluster",
                "action_id": Action.objects.get(name="not_host_action").id,
            },
        )

        self.assertDictEqual(
            inventory_data["service_1_target_group.component_1_target_group.maintenance_mode"]["hosts"][
                "host_target_group_1"
            ]["cluster"]["config"],
            {"some_string": "cluster", "float": 0.1},
        )
        self.assertDictEqual(
            inventory_data["service_1_target_group.component_1_target_group.maintenance_mode"]["hosts"][
                "host_target_group_1"
            ]["services"]["service_1_target_group"]["config"],
            {"some_string": "service_1", "float": 0.1},
        )
        self.assertDictEqual(
            inventory_data["service_1_target_group.component_1_target_group.maintenance_mode"]["hosts"][
                "host_target_group_1"
            ]["services"]["service_1_target_group"]["component_1_target_group"]["config"],
            {"some_string": "some_string", "float": 0.1},
        )

    def test_host_in_target_group_hostaction_on_host_in_mm_success(self):
        self.host_target_group_1.maintenance_mode = MaintenanceMode.ON
        self.host_target_group_1.save()

        target_hosts_data = self.get_inventory_data(
            data={"verbose": False},
            kwargs={
                "cluster_id": self.cluster_target_group.pk,
                "host_id": self.host_target_group_1.pk,
                "object_type": "host",
                "action_id": self.action_target_group.pk,
            },
        )["target"]["hosts"]

        self.assertIn(self.host_target_group_1.fqdn, target_hosts_data)

    def test_host_in_target_group_hostaction_on_host_not_in_mm_success(self):
        self.host_target_group_2.maintenance_mode = MaintenanceMode.OFF
        self.host_target_group_2.save()

        target_hosts_data = self.get_inventory_data(
            data={"verbose": False},
            kwargs={
                "cluster_id": self.cluster_target_group.pk,
                "host_id": self.host_target_group_2.pk,
                "object_type": "host",
                "action_id": self.action_target_group.pk,
            },
        )["target"]["hosts"]

        self.assertIn(self.host_target_group_2.fqdn, target_hosts_data)
