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

from core.job.dto import TaskPayloadDTO
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.core.exceptions import ObjectDoesNotExist

from cm.models import Action
from cm.services.job.action import prepare_task_for_action
from cm.services.job.inventory import get_inventory_data
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestClusterHosts(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None

        bundles_dir = Path(__file__).parent.parent / "bundles"
        self.templates_dir = Path(__file__).parent.parent / "files/response_templates"

        self.provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")

    def test_cluster_action_on_cluster(self):
        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)

        expected_data = {
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.cluster_1,
            action=action_on_cluster,
            expected_topology={},
            expected_data=expected_data,
        )

    def test_add_1_host_on_cluster_actions(self):
        host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_host = Action.objects.get(name="action_on_host", prototype=host_1.prototype)

        expected_topology = {
            "CLUSTER": [host_1.fqdn],
        }

        expected_data = {
            ("CLUSTER", "hosts", host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_1.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
        }

        expected_topology_for_host = {
            "HOST": [host_1.fqdn],
        }

        expected_data_for_host = {
            ("HOST", "hosts", host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": host_1.prototype.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (host_1, action_on_host, expected_topology_for_host, expected_data_for_host),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)

    def test_add_2_hosts_on_cluster_actions(self):
        host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )
        host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_host_1 = Action.objects.get(name="action_on_host", prototype=host_1.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=host_2.prototype)

        expected_topology = {
            "CLUSTER": [host_1.fqdn, host_2.fqdn],
        }

        expected_data = {
            ("CLUSTER", "hosts", host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_1.pk,
                },
            ),
            ("CLUSTER", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
        }

        expected_topology_for_host_1 = {
            "HOST": [host_1.fqdn],
        }

        expected_data_for_host_1 = {
            ("HOST", "hosts", host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host_2 = {
            "HOST": [host_2.fqdn],
        }

        expected_data_for_host_2 = {
            ("HOST", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": host_2.prototype.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (host_1, action_on_host_1, expected_topology_for_host_1, expected_data_for_host_1),
            (host_2, action_on_host_2, expected_topology_for_host_2, expected_data_for_host_2),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)

    def test_adcm_5747_delete_service(self) -> None:
        service = self.add_services_to_cluster(["service_one_component"], cluster=self.cluster_1).get()
        host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1)
        self.set_hostcomponent(cluster=self.cluster_1, entries=[(host, service.servicecomponent_set.first())])

        action = Action.objects.get(prototype=service.prototype, name="action_on_service")
        target = CoreObjectDescriptor(id=service.id, type=ADCMCoreType.SERVICE)
        task = prepare_task_for_action(target=target, orm_owner=service, action=action.id, payload=TaskPayloadDTO())

        # imitate service deletion during task run (prev job deleted service)
        service.delete()

        # without related objects it fails
        with self.assertRaises(ObjectDoesNotExist) as err_context:
            get_inventory_data(target=task.target, is_host_action=False)

        self.assertIn("ClusterObject matching query does not exist.", str(err_context.exception))

        # with those inventory is generated
        data = get_inventory_data(target=task.target, is_host_action=False, related_objects=task.owner.related_objects)

        self.assertSetEqual(set(data["all"]["vars"]), {"cluster", "services"})
        self.assertDictEqual(data["all"]["vars"]["services"], {})
        self.assertSetEqual(set(data["all"]["children"]), {"CLUSTER"})
        self.assertIn("host_1", data["all"]["children"]["CLUSTER"]["hosts"])
