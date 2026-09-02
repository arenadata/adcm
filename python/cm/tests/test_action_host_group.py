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
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExternalSettings,
    IntegrationsSettings,
)
from core.types import ActionTargetDescriptor, ADCMCoreType, CoreObjectDescriptor, ExtraActionTargetType
from django.conf import settings
from tests.base import BaseTestCase
from use_cases.dto import RunActionDTO
from use_cases.transition.job.schedule import ScheduleTask

from cm.errors import AdcmEx
from cm.impl.job.repo import JobRepo
from cm.legacy.services.action_host_group import ActionHostGroupRepo, ActionHostGroupService, CreateDTO
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.jinja_env import get_env_for_jinja_scripts
from cm.legacy.services.job.context import get_inventory_data
from cm.legacy.services.job.run._target_factories import prepare_ansible_job_config
from cm.models import Action, ActionHostGroup, Component, TaskLog
from cm.tests.dependencies import WithDishkaContainer


class TestActionHostGroup(WithDishkaContainer, BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundles_dir = Path(__file__).parent / "bundles"

        self.provider = self.uc.add_provider(
            bundle=self.uc.upload_bundle(self.bundles_dir / "provider_full_config"), name="Host Provider"
        )
        self.host_1 = self.uc.add_host(provider=self.provider, fqdn="host-1")
        self.host_2 = self.uc.add_host(provider=self.provider, fqdn="host-2")

        self.cluster = self.uc.add_cluster(
            bundle=self.uc.upload_bundle(self.bundles_dir / "cluster_full_config"), name="Main Cluster"
        )
        self.service, *_ = self.uc.add_services_to_cluster(names=["all_params"], cluster=self.cluster)
        self.component = Component.objects.get(service=self.service)

        self.uc.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.uc.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        self.uc.set_hostcomponent(
            cluster=self.cluster, entries=((self.host_1, self.component), (self.host_2, self.component))
        )

        self.context = {
            "hostprovider_bundle": self.provider.prototype.bundle,
            "cluster_bundle": self.cluster.prototype.bundle,
            "datadir": self.directories.data,
            "stackdir": self.directories.stack,
            "token": settings.STATUS_SECRET_KEY,
            "component_type_id": self.component.prototype_id,
        }

        self.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
            consul=ConsulSettings(
                url=settings.CONSUL_URL, datacenter=settings.CONSUL_DATACENTER, cacert_file=settings.CONSUL_CACERT_FILE
            ),
        )

        self.action_group_service = ActionHostGroupService(repository=ActionHostGroupRepo())

        group_id = self.action_group_service.create(
            CreateDTO(
                name="simple", description="", owner=CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER)
            )
        )
        self.action_group_service.add_hosts_to_group(group_id=group_id, hosts=(self.host_1.id, self.host_2.id))
        self.action_group = ActionHostGroup.objects.get(id=group_id)

    def test_run_action_success(self) -> None:
        action = Action.objects.get(prototype=self.cluster.prototype, name="dummy")

        with self.container() as container:
            launched_task = container.get(ScheduleTask).do(
                action_orm=action, target=self.action_group, payload=RunActionDTO()
            )

        task_id = launched_task.pk
        task = TaskLog.objects.get(id=task_id)
        self.assertEqual(task.task_object, self.action_group)
        self.assertEqual(task.owner_id, self.cluster.id)
        self.assertEqual(task.owner_type, ADCMCoreType.CLUSTER.value)

    def test_generate_inventory_success(self) -> None:
        group_inventory = get_inventory_data(
            target=ActionTargetDescriptor(id=self.action_group.id, type=ExtraActionTargetType.ACTION_HOST_GROUP),
            is_host_action=False,
            delta=None,
            cluster_service=self.uc.container.get(ClusterService),
        )

        self.assertIn("target", group_inventory["all"]["children"])
        self.assertSetEqual(
            set(group_inventory["all"]["children"]["target"]["hosts"]), {self.host_1.fqdn, self.host_2.fqdn}
        )

        owner_inventory = get_inventory_data(
            target=ActionTargetDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER),
            is_host_action=False,
            delta=None,
            cluster_service=self.uc.container.get(ClusterService),
        )

        group_inventory["all"]["children"].pop("target")
        self.assertEqual(group_inventory, owner_inventory)

    def test_get_env_for_jinja_scripts_success(self) -> None:
        group_id = self.action_group_service.create(
            CreateDTO(
                name="simple", description="", owner=CoreObjectDescriptor(id=self.service.id, type=ADCMCoreType.SERVICE)
            )
        )
        self.action_group_service.add_hosts_to_group(group_id=group_id, hosts=(self.host_1.id, self.host_2.id))

        action = Action.objects.get(prototype=self.service.prototype, name="dummy")
        action_group = ActionHostGroup.objects.get(id=group_id)

        with self.container() as container:
            launched_task = container.get(ScheduleTask).do(
                action_orm=action, target=action_group, payload=RunActionDTO()
            )

        task_id = launched_task.pk
        task = TaskLog.objects.get(id=task_id)
        result_env = get_env_for_jinja_scripts(task=task)

        self.assertSetEqual(
            set(result_env["groups"]),
            {"target", "CLUSTER", self.service.name, f"{self.service.name}.{self.component.name}"},
        )
        self.assertSetEqual(set(result_env["groups"]["target"]), {self.host_1.fqdn, self.host_2.fqdn})

    def test_group_not_in_selector_success(self) -> None:
        group_id = self.action_group_service.create(
            CreateDTO(
                name="simple",
                description="",
                owner=CoreObjectDescriptor(id=self.component.id, type=ADCMCoreType.COMPONENT),
            )
        )
        self.action_group_service.add_hosts_to_group(group_id=group_id, hosts=(self.host_1.id, self.host_2.id))

        action = Action.objects.get(prototype=self.service.prototype, name="dummy")
        action_group = ActionHostGroup.objects.get(id=group_id)

        with self.container() as container:
            launched_task = container.get(ScheduleTask).do(
                action_orm=action, target=action_group, payload=RunActionDTO()
            )

        task_id = launched_task.pk
        task = JobRepo().get_task(task_id)
        job, *_ = JobRepo().get_task_jobs(task.id)

        config = prepare_ansible_job_config(
            task=task,
            job=job,
            configuration=ExternalSettings(
                adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
                ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
                integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
                consul=ConsulSettings(
                    url=settings.CONSUL_URL,
                    datacenter=settings.CONSUL_DATACENTER,
                    cacert_file=settings.CONSUL_CACERT_FILE,
                ),
            ),
            topology=retrieve_cluster_topology(self.cluster.pk),
        )

        self.assertDictEqual(
            config["context"],
            {
                "cluster_id": self.cluster.id,
                "service_id": self.service.id,
                "component_id": self.component.id,
                "type": "component",
            },
        )

    def test_upload_success(self) -> None:
        bundle = self.add_bundle(self.bundles_dir / "action_host_group" / "correct")

        cluster_action = Action.objects.get(
            prototype__type="cluster", prototype__bundle=bundle, name="allow_true_ha_false"
        )
        self.assertTrue(cluster_action.allow_for_action_host_group)
        self.assertFalse(cluster_action.host_action)

        service_action = Action.objects.get(
            prototype__type="service", prototype__bundle=bundle, name="allow_false_ha_true"
        )
        self.assertFalse(service_action.allow_for_action_host_group)
        self.assertTrue(service_action.host_action)

        component_action = Action.objects.get(
            prototype__type="component", prototype__bundle=bundle, name="allow_true_ha_absent"
        )
        self.assertTrue(component_action.allow_for_action_host_group)
        self.assertFalse(component_action.host_action)

    def test_upload_fail(self) -> None:
        negative_dir = self.bundles_dir / "action_host_group" / "negative"

        with self.subTest("Host Action AND Action Host Group"):
            with self.assertRaises(AdcmEx) as err_context:
                self.add_bundle(negative_dir / "with_host_action")

            self.assertEqual(err_context.exception.code, "BUNDLE_DEFINITION_ERROR")
            self.assertIn(
                "The allow_for_action_host_group and host_action attributes are mutually exclusive",
                err_context.exception.msg,
            )

        with self.subTest("Action Host Group In Upgrade"):
            with self.assertRaises(AdcmEx) as err_context:
                self.add_bundle(negative_dir / "in_upgrade")

            self.assertEqual(err_context.exception.code, "BUNDLE_DEFINITION_ERROR")
            self.assertIn(
                "allow_for_action_host_group\n   | extra_forbidden: Extra inputs are not permitted",
                err_context.exception.msg,
            )
