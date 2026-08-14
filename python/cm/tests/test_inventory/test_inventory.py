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

from core.cluster import ClusterService
from core.legacy.cluster.types import HostComponentEntry
from core.types import CoreObjectDescriptor
from tests.suites import GenericTestCase
from use_cases.dto import RunActionDTO
import core

from cm.converters import model_name_to_core_type
from cm.impl.job.repo import JobRepo
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.job.action import ObjectWithAction
from cm.legacy.services.job.context import get_inventory_data
from cm.legacy.services.job.context._constants import MAINTENANCE_MODE_GROUP_SUFFIX
from cm.legacy.services.job.types import HcAclAction
from cm.models import (
    Action,
    Component,
    Host,
    HostComponent,
    JobLog,
    MaintenanceMode,
    Service,
    TaskLog,
)
from cm.tests.test_action_host_group import ScheduleTask
from cm.tests.utils import (
    gen_bundle,
    gen_cluster,
    gen_config,
    gen_group,
    gen_host,
    gen_prototype,
    gen_provider,
)


class TestInventory(GenericTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.cluster_bundle = gen_bundle()
        cls.cluster_pt = gen_prototype(cls.cluster_bundle, "cluster", "cluster")
        cls.cluster = gen_cluster(prototype=cls.cluster_pt, config=gen_config(), name="cluster")

        cls.provider_bundle = gen_bundle()

        cls.provider_pt = gen_prototype(cls.provider_bundle, "provider")
        cls.host_pt = gen_prototype(cls.provider_bundle, "host")

        cls.provider = gen_provider(prototype=cls.provider_pt)
        cls.host = gen_host(cls.provider, prototype=cls.host_pt)

    def test_prepare_job_inventory(self):
        host2 = Host.objects.create(prototype=self.host_pt, fqdn="h2", cluster=self.cluster, provider=self.provider)
        action = Action.objects.create(prototype=self.cluster_pt)

        self.maxDiff = None

        cluster_inv = {
            "all": {
                "children": {"CLUSTER": {"hosts": {host2.fqdn: {}}}},
                "hosts": {
                    host2.fqdn: {
                        "adcm_hostid": host2.pk,
                        "uuid": str(host2.uuid),
                        "state": "created",
                        "multi_state": [],
                    }
                },
                "vars": {
                    "cluster": {
                        "config": {},
                        "name": "cluster",
                        "id": self.cluster.pk,
                        "uuid": str(self.cluster.uuid),
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
                "children": {"HOST": {"hosts": {self.host.fqdn: {}}}},
                "hosts": {
                    self.host.fqdn: {
                        "adcm_hostid": self.host.pk,
                        "uuid": str(self.host.uuid),
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
            },
        }
        provider_inv = {
            "all": {
                "children": {
                    "PROVIDER": {
                        "hosts": {
                            self.host.fqdn: {},
                            "h2": {},
                        },
                    },
                },
                "hosts": {
                    self.host.fqdn: {
                        "adcm_hostid": self.host.pk,
                        "uuid": str(self.host.uuid),
                        "state": "created",
                        "multi_state": [],
                    },
                    "h2": {"adcm_hostid": host2.pk, "uuid": str(host2.uuid), "state": "created", "multi_state": []},
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
                actual_data = get_inventory_data(
                    target=target,
                    is_host_action=action.host_action,
                    cluster_service=self.uc.container.get(ClusterService),
                )
                self.assertDictEqual(actual_data, inv)


class TestInventoryAndMaintenanceMode(GenericTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

        cls.bundles_dir = Path(__file__).parent.parent / "bundles"
        cls.cluster_hc_acl = cls.uc.add_cluster(
            bundle=cls.uc.upload_bundle(src=cls.bundles_dir / "test_inventory_remove_group_mm_hosts"),
            name="cluster_hc_acl",
        )
        cls.provider = gen_provider(name="test_provider")
        host_prototype = gen_prototype(bundle=cls.provider.prototype.bundle, proto_type="host")
        cls.host_hc_acl_1 = gen_host(
            provider=cls.provider, cluster=cls.cluster_hc_acl, fqdn="hc_acl_host_1", prototype=host_prototype
        )
        cls.host_hc_acl_2 = gen_host(
            provider=cls.provider, cluster=cls.cluster_hc_acl, fqdn="hc_acl_host_2", prototype=host_prototype
        )
        cls.host_hc_acl_3 = gen_host(
            provider=cls.provider, cluster=cls.cluster_hc_acl, fqdn="hc_acl_host_3", prototype=host_prototype
        )

        cls.service_hc_acl, *_ = cls.uc.add_services_to_cluster(cluster=cls.cluster_hc_acl, names=["service_1"])

        cls.component_hc_acl_1 = Component.objects.get(cluster=cls.cluster_hc_acl, prototype__name="component_1")
        cls.component_hc_acl_2 = Component.objects.get(cluster=cls.cluster_hc_acl, prototype__name="component_2")

        cls.hc_c1_h1 = {
            "host_id": cls.host_hc_acl_1.pk,
            "service_id": cls.service_hc_acl.pk,
            "component_id": cls.component_hc_acl_1.pk,
        }
        cls.hc_c1_h2 = {
            "host_id": cls.host_hc_acl_2.pk,
            "service_id": cls.service_hc_acl.pk,
            "component_id": cls.component_hc_acl_1.pk,
        }
        cls.hc_c1_h3 = {
            "host_id": cls.host_hc_acl_3.pk,
            "service_id": cls.service_hc_acl.pk,
            "component_id": cls.component_hc_acl_1.pk,
        }
        cls.hc_c2_h1 = {
            "host_id": cls.host_hc_acl_1.pk,
            "service_id": cls.service_hc_acl.pk,
            "component_id": cls.component_hc_acl_2.pk,
        }
        cls.hc_c2_h2 = {
            "host_id": cls.host_hc_acl_2.pk,
            "service_id": cls.service_hc_acl.pk,
            "component_id": cls.component_hc_acl_2.pk,
        }

        cls.uc.set_hostcomponent(
            cluster=cls.cluster_hc_acl,
            entries=(
                (Host.objects.get(id=entry["host_id"]), Component.objects.get(id=entry["component_id"]))
                for entry in (cls.hc_c1_h1, cls.hc_c1_h2, cls.hc_c1_h3, cls.hc_c2_h1, cls.hc_c2_h2)
            ),
        )

        cls.action_hc_acl = Action.objects.get(name="cluster_action_hc_acl", allow_in_maintenance_mode=True)

        cls.cluster_target_group = cls.uc.add_cluster(
            bundle=cls.uc.upload_bundle(src=cls.bundles_dir / "cluster_mm_host_target_group"),
            name="cluster_target_group",
        )

        cls.host_target_group_1 = gen_host(
            provider=cls.provider,
            cluster=cls.cluster_target_group,
            fqdn="host_target_group_1",
            prototype=host_prototype,
        )
        cls.host_target_group_2 = gen_host(
            provider=cls.provider,
            cluster=cls.cluster_target_group,
            fqdn="host_target_group_2",
            prototype=host_prototype,
        )

        cls.service_target_group, *_ = cls.uc.add_services_to_cluster(
            cluster=cls.cluster_target_group, names=["service_1_target_group"]
        )
        cls.component_target_group = Component.objects.get(
            cluster=cls.cluster_target_group, prototype__name="component_1_target_group"
        )

        cls.uc.set_hostcomponent(
            cluster=cls.cluster_target_group,
            entries=[
                (cls.host_target_group_1, cls.component_target_group),
                (cls.host_target_group_2, cls.component_target_group),
            ],
        )

        cls.action_target_group = Action.objects.get(name="host_action_target_group", allow_in_maintenance_mode=True)

    @staticmethod
    def _get_hc_request_data(*new_hc_items: dict) -> list[dict]:
        hc_fields = ("id", "service_id", "component_id", "host_id")
        hc_request_data = []

        for host_component in new_hc_items:
            hc_values = HostComponent.objects.filter(**host_component).values_list(*hc_fields).first()
            hc_request_data.append(dict(zip(hc_fields, hc_values, strict=False)))

        return hc_request_data

    def get_all_from_inventory(
        self, action: Action, object_: ObjectWithAction, payload: RunActionDTO, cluster_id: int
    ) -> dict:
        from cm.legacy.services.job.run._target_factories import prepare_ansible_inventory

        self.assertEqual(TaskLog.objects.count(), 0)
        self.assertEqual(JobLog.objects.count(), 0)

        with self.container() as container:
            container.get(ScheduleTask).do(
                action_orm=action,
                target=object_,
                payload=payload,
            )

        task_id = self.task_runner.expect_task_launched().id

        inventory = prepare_ansible_inventory(
            task=JobRepo().get_task(task_id),
            topology=retrieve_cluster_topology(cluster_id),
            cluster_service=self.uc.container.get(ClusterService),
        )
        return inventory["all"]

    def test_groups_remove_host_not_in_mm_success(self):
        self.host_hc_acl_3.maintenance_mode = MaintenanceMode.ON
        self.host_hc_acl_3.save()

        # remove: hc_c1_h2
        hc_request_data = self._get_hc_request_data(self.hc_c1_h1, self.hc_c1_h3, self.hc_c2_h1, self.hc_c2_h2)

        inventory_data = self.get_all_from_inventory(
            action=self.action_hc_acl,
            object_=self.cluster_hc_acl,
            payload=RunActionDTO(
                mapping={
                    HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                    for entry in hc_request_data
                },
                launch=core.action.job.LaunchOptions(
                    is_verbose=False,
                ),
            ),
            cluster_id=self.cluster_hc_acl.pk,
        )["children"]

        target_key_remove = (
            f"{Service.objects.get(pk=self.hc_c1_h2['service_id']).prototype.name}"
            f".{Component.objects.get(pk=self.hc_c1_h2['component_id']).prototype.name}"
            f".{HcAclAction.REMOVE.value}"
        )
        target_key_mm_service = (
            f"{Service.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}." f"{MAINTENANCE_MODE_GROUP_SUFFIX}"
        )
        target_key_mm_service_component = (
            f"{Service.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}"
            f".{Component.objects.get(pk=self.hc_c1_h3['component_id']).prototype.name}"
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

        inventory_data = self.get_all_from_inventory(
            action=self.action_hc_acl,
            object_=self.cluster_hc_acl,
            payload=RunActionDTO(
                mapping={
                    HostComponentEntry(host_id=entry["host_id"], component_id=entry["component_id"])
                    for entry in hc_request_data
                },
                launch=core.action.job.LaunchOptions(is_verbose=False),
            ),
            cluster_id=self.cluster_hc_acl.pk,
        )["children"]

        target_key_remove = (
            f"{Service.objects.get(pk=self.hc_c1_h3['service_id']).prototype.name}"
            f".{Component.objects.get(pk=self.hc_c1_h3['component_id']).prototype.name}"
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
            gen_group(name="service_1", object_id=self.service_target_group.id, model_name="service"),
        ]

        for group in groups:
            group.hosts.add(self.host_target_group_1)
            self.uc.set_config_of_group(
                group=group,
                config=core.config.Configuration(
                    values={"some_string": group.name, "float": 0.1},
                    attributes={
                        "/some_string": core.config.Attributes(is_synced=False),
                        "/float": core.config.Attributes(is_synced=True),
                    },
                ),
            )

        inventory_data = self.get_all_from_inventory(
            action=Action.objects.get(name="not_host_action"),
            object_=self.cluster_target_group,
            payload=RunActionDTO(launch=core.action.job.LaunchOptions(is_verbose=False)),
            cluster_id=self.cluster_target_group.pk,
        )["children"]

        group_key = f"chg_{groups[0].pk}_{groups[1].pk}"

        self.assertDictEqual(
            inventory_data[group_key]["vars"]["cluster"]["config"],
            {"some_string": "cluster", "float": 0.1},
        )
        self.assertDictEqual(
            inventory_data[group_key]["vars"]["services"]["service_1_target_group"]["config"],
            {"some_string": "service_1", "float": 0.1},
        )
        self.assertDictEqual(
            inventory_data[group_key]["vars"]["services"]["service_1_target_group"]["component_1_target_group"][
                "config"
            ],
            {"some_string": "some_string", "float": 0.1},
        )

    def test_host_in_target_group_hostaction_on_host_in_mm_success(self):
        self.host_target_group_1.maintenance_mode = MaintenanceMode.ON
        self.host_target_group_1.save()

        target_hosts_data = self.get_all_from_inventory(
            action=self.action_target_group,
            object_=self.host_target_group_1,
            payload=RunActionDTO(launch=core.action.job.LaunchOptions(is_verbose=False)),
            cluster_id=self.cluster_target_group.pk,
        )["children"]["target"]["hosts"]

        self.assertIn(self.host_target_group_1.fqdn, target_hosts_data)

    def test_host_in_target_group_hostaction_on_host_not_in_mm_success(self):
        self.host_target_group_2.maintenance_mode = MaintenanceMode.OFF
        self.host_target_group_2.save()

        target_hosts_data = self.get_all_from_inventory(
            action=self.action_target_group,
            object_=self.host_target_group_2,
            payload=RunActionDTO(launch=core.action.job.LaunchOptions(is_verbose=False)),
            cluster_id=self.cluster_target_group.pk,
        )["children"]["target"]["hosts"]

        self.assertIn(self.host_target_group_2.fqdn, target_hosts_data)
