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


from pathlib import Path

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from core.cluster.types import HostComponentEntry
from core.types import CoreObjectDescriptor
from init_db import init as init_adcm

from cm.api import add_service_to_cluster, update_obj_config
from cm.converters import model_name_to_core_type
from cm.models import (
    Action,
    ClusterObject,
    Host,
    HostComponent,
    JobLog,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
    TaskLog,
)
from cm.services.job.action import ActionRunPayload, ObjectWithAction, run_action
from cm.services.job.inventory import get_inventory_data
from cm.services.job.inventory._constants import MAINTENANCE_MODE_GROUP_SUFFIX
from cm.services.job.types import HcAclAction
from cm.tests.mocks.task_runner import RunTaskMock
from cm.tests.utils import (
    gen_bundle,
    gen_cluster,
    gen_config,
    gen_group,
    gen_host,
    gen_prototype,
    gen_provider,
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

    def test_prepare_job_inventory(self):
        host2 = Host.objects.create(prototype=self.host_pt, fqdn="h2", cluster=self.cluster, provider=self.provider)
        action = Action.objects.create(prototype=self.cluster_pt)

        self.maxDiff = None

        cluster_inv = {
            "all": {
                "children": {
                    "CLUSTER": {"hosts": {host2.fqdn: {"adcm_hostid": host2.pk, "state": "created", "multi_state": []}}}
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
        }
        host_inv = {
            "all": {
                "children": {
                    "HOST": {
                        "hosts": {self.host.fqdn: {"adcm_hostid": self.host.pk, "state": "created", "multi_state": []}}
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
            },
        }
        provider_inv = {
            "all": {
                "children": {
                    "PROVIDER": {
                        "hosts": {
                            self.host.fqdn: {"adcm_hostid": self.host.pk, "state": "created", "multi_state": []},
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
            target = CoreObjectDescriptor(id=obj.id, type=model_name_to_core_type(obj.__class__.__name__))
            with self.subTest(obj=obj, inv=inv):
                actual_data = get_inventory_data(target=target, is_host_action=action.host_action)
                self.assertDictEqual(actual_data, inv)


class TestInventoryAndMaintenanceMode(BusinessLogicMixin, BaseTestCase):
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

        self.set_hostcomponent(
            cluster=self.cluster_hc_acl,
            entries=(
                (Host.objects.get(id=entry["host_id"]), ServiceComponent.objects.get(id=entry["component_id"]))
                for entry in (self.hc_c1_h1, self.hc_c1_h2, self.hc_c1_h3, self.hc_c2_h1, self.hc_c2_h2)
            ),
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

        self.set_hostcomponent(
            cluster=self.cluster_target_group,
            entries=[
                (self.host_target_group_1, self.component_target_group),
                (self.host_target_group_2, self.component_target_group),
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

    def get_children_from_inventory(self, action: Action, object_: ObjectWithAction, payload: ActionRunPayload) -> dict:
        from cm.services.job.run._target_factories import prepare_ansible_inventory
        from cm.services.job.run.repo import JobRepoImpl

        self.assertEqual(TaskLog.objects.count(), 0)
        self.assertEqual(JobLog.objects.count(), 0)

        with RunTaskMock() as run_task:
            run_action(action=action, obj=object_, payload=payload)

        inventory = prepare_ansible_inventory(task=JobRepoImpl.get_task(run_task.target_task.id))
        return inventory["all"]["children"]

    def test_groups_remove_host_not_in_mm_success(self):
        self.host_hc_acl_3.maintenance_mode = MaintenanceMode.ON
        self.host_hc_acl_3.save()

        # remove: hc_c1_h2
        hc_request_data = self._get_hc_request_data(self.hc_c1_h1, self.hc_c1_h3, self.hc_c2_h1, self.hc_c2_h2)

        inventory_data = self.get_children_from_inventory(
            action=self.action_hc_acl,
            object_=self.cluster_hc_acl,
            payload=ActionRunPayload(
                hostcomponent={
                    HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                    for entry in hc_request_data
                },
                verbose=False,
            ),
        )

        target_key_remove = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h2['service_id']).prototype.name}"
            f".{ServiceComponent.objects.get(pk=self.hc_c1_h2['component_id']).prototype.name}"
            f".{HcAclAction.REMOVE.value}"
        )
        target_key_mm_service = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}."
            f"{MAINTENANCE_MODE_GROUP_SUFFIX}"
        )
        target_key_mm_service_component = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}"
            f".{ServiceComponent.objects.get(pk=self.hc_c1_h3['component_id']).prototype.name}"
            f".{MAINTENANCE_MODE_GROUP_SUFFIX}"
        )

        self.assertIn(target_key_remove, inventory_data)
        self.assertIn(self.host_hc_acl_2.fqdn, inventory_data[target_key_remove]["hosts"])

        self.assertIn(target_key_mm_service, inventory_data)
        self.assertIn(self.host_hc_acl_3.fqdn, inventory_data[target_key_mm_service]["hosts"])

        self.assertIn(target_key_mm_service_component, inventory_data)
        self.assertIn(self.host_hc_acl_3.fqdn, inventory_data[target_key_mm_service_component]["hosts"])

        remove_keys = [key for key in inventory_data if key.endswith(f".{HcAclAction.REMOVE.value}")]
        self.assertEqual(len(remove_keys), 1)

        mm_keys = [key for key in inventory_data if key.endswith(f".{MAINTENANCE_MODE_GROUP_SUFFIX}")]
        self.assertEqual(len(mm_keys), 3)

    def test_groups_remove_host_in_mm_success(self):
        self.host_hc_acl_3.maintenance_mode = MaintenanceMode.ON
        self.host_hc_acl_3.save()

        # remove: hc_c1_h3
        hc_request_data = self._get_hc_request_data(self.hc_c1_h1, self.hc_c1_h2, self.hc_c2_h1, self.hc_c2_h2)

        inventory_data = self.get_children_from_inventory(
            action=self.action_hc_acl,
            object_=self.cluster_hc_acl,
            payload=ActionRunPayload(
                hostcomponent={
                    HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                    for entry in hc_request_data
                },
                verbose=False,
            ),
        )

        target_key_remove = (
            f"{ClusterObject.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}"
            f".{ServiceComponent.objects.get(pk=self.hc_c1_h3['component_id']).prototype.name}"
            f".{HcAclAction.REMOVE.value}"
            f".maintenance_mode"
        )

        self.assertIn(target_key_remove, inventory_data)
        self.assertIn(self.host_hc_acl_3.fqdn, inventory_data[target_key_remove]["hosts"])

        remove_keys = [key for key in inventory_data if f".{HcAclAction.REMOVE.value}" in key]
        self.assertEqual(len(remove_keys), 1)

        mm_keys = [
            key
            for key in inventory_data
            if key.endswith(f".{HcAclAction.REMOVE.value}.{MAINTENANCE_MODE_GROUP_SUFFIX}")
        ]
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

        inventory_data = self.get_children_from_inventory(
            action=Action.objects.get(name="not_host_action"),
            object_=self.cluster_target_group,
            payload=ActionRunPayload(verbose=False),
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

        target_hosts_data = self.get_children_from_inventory(
            action=self.action_target_group, object_=self.host_target_group_1, payload=ActionRunPayload(verbose=False)
        )["target"]["hosts"]

        self.assertIn(self.host_target_group_1.fqdn, target_hosts_data)

    def test_host_in_target_group_hostaction_on_host_not_in_mm_success(self):
        self.host_target_group_2.maintenance_mode = MaintenanceMode.OFF
        self.host_target_group_2.save()

        target_hosts_data = self.get_children_from_inventory(
            action=self.action_target_group, object_=self.host_target_group_2, payload=ActionRunPayload(verbose=False)
        )["target"]["hosts"]

        self.assertIn(self.host_target_group_2.fqdn, target_hosts_data)
