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
from uuid import uuid4
import unittest

from core.dynamic_bundle.types import ContextGathererI
from core.legacy.action.process.types import ProcessState
from django.utils import timezone
from tests.base import BaseTestCase
from tests.deprecated import BusinessLogicMixin, TaskTestMixin

from cm.legacy.adcm_config.ansible import ansible_decrypt, ansible_encrypt_and_format
from cm.legacy.services.bundle_alt.render import ActionArgs, TaskArgs
from cm.legacy.utils import decrypt_secrets
from cm.models import (
    ADCM,
    Action,
    ConfigLog,
    MaintenanceMode,
    Process,
    ProcessStep,
    ProcessStepInput,
)
from cm.tests.dependencies import WithDishkaContainer


class TestScriptsTemplateEnvironment(WithDishkaContainer, BusinessLogicMixin, TaskTestMixin, BaseTestCase):
    # COPIED FROM cm.tests.test_jinja_scripts.TestJinjaScriptsEnvironment

    maxDiff = None

    def setUp(self) -> None:
        bundles_dir = Path(__file__).parent / "bundles"

        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")
        provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")

        self.cluster = self.add_cluster(bundle=cluster_bundle, name="test_cluster")

        self.service = self.add_services_to_cluster(service_names=["service_one_component"], cluster=self.cluster).get()

        self.component = self.service.components.get(prototype__name="component_1")

        provider = self.add_provider(bundle=provider_bundle, name="test_provider")
        host = self.add_host(provider=provider, fqdn="test_host", cluster=self.cluster)
        self.host = host
        self.set_hostcomponent(cluster=self.cluster, entries=((host, self.component),))

        self.cluster_action = Action.objects.get(prototype=self.cluster.prototype, name="action_on_cluster")
        self.service_action = Action.objects.get(prototype=self.service.prototype, name="action_on_service")
        self.component_action = Action.objects.get(prototype=self.component.prototype, name="action_on_component")
        self.component_host_action = Action.objects.get(
            prototype=self.component.prototype, name="host_action_on_component"
        )

        common_config = ConfigLog.objects.get(pk=self.cluster.config.current).config
        common_config["password"] = ansible_decrypt(common_config["password"])

        self.expected_env_part = {
            "adcm": {"uuid": str(ADCM.objects.filter().values("uuid").first()["uuid"])},
            "cluster": {
                "uuid": str(self.cluster.uuid),
                "before_upgrade": {"state": None, "config": None},
                "edition": self.cluster.edition,
                "config": common_config,
                "id": self.cluster.pk,
                "multi_state": self.cluster.multi_state,
                "name": self.cluster.name,
                "state": self.cluster.state,
                "version": self.cluster.prototype.version,
                "imports": None,
            },
            "services": {
                self.service.prototype.name: {
                    "uuid": str(self.service.uuid),
                    "before_upgrade": {"state": None, "config": None},
                    "config": common_config,
                    "id": self.service.pk,
                    "multi_state": self.service.multi_state,
                    "state": self.service.state,
                    "display_name": self.service.display_name,
                    "maintenance_mode": self.service.maintenance_mode == MaintenanceMode.ON,
                    "version": self.service.prototype.version,
                    self.component.prototype.name: {
                        "uuid": str(self.component.uuid),
                        "before_upgrade": {"state": None, "config": None},
                        "component_id": self.component.pk,
                        "config": common_config,
                        "display_name": self.component.display_name,
                        "maintenance_mode": self.component.maintenance_mode.value == MaintenanceMode.ON,
                        "multi_state": self.component.multi_state,
                        "state": self.component.state,
                    },
                }
            },
            "env": {"consul_cacert_file": None, "consul_datacenter": None, "consul_url": None},
            "groups": {
                "CLUSTER": [host.fqdn],
                "service_one_component": [host.fqdn],
                "service_one_component.component_1": [host.fqdn],
            },
            "task": {"config": None, "verbose": False},
        }
        with self.container() as container:
            self.context_gatherer = container.get(ContextGathererI[ActionArgs, TaskArgs])

    def test_env_for_cluster(self):
        args = TaskArgs(target_object=self.cluster, owner_object=self.cluster, action=self.cluster_action)
        env = decrypt_secrets(source=self.context_gatherer.prepare_context_for_task(args=args))
        expected_env = {
            **self.expected_env_part,
            "action": {"name": "action_on_cluster", "owner_group": "CLUSTER"},
        }
        self.assertDictEqual(env, expected_env)

    def test_env_for_service(self):
        args = TaskArgs(target_object=self.service, owner_object=self.service, action=self.service_action)
        env = decrypt_secrets(source=self.context_gatherer.prepare_context_for_task(args=args))
        expected_env = {
            **self.expected_env_part,
            "action": {"name": "action_on_service", "owner_group": "service_one_component"},
        }
        self.assertDictEqual(env, expected_env)

    def test_env_for_component(self):
        args = TaskArgs(target_object=self.component, owner_object=self.component, action=self.component_action)
        env = decrypt_secrets(source=self.context_gatherer.prepare_context_for_task(args=args))
        expected_env = {
            **self.expected_env_part,
            "action": {
                "name": "action_on_component",
                "owner_group": "service_one_component.component_1",
            },
        }
        self.assertDictEqual(env, expected_env)

    def test_env_for_host(self):
        args = TaskArgs(target_object=self.host, owner_object=self.component, action=self.component_host_action)
        env = decrypt_secrets(source=self.context_gatherer.prepare_context_for_task(args=args))
        expected_env = {
            **self.expected_env_part,
            "groups": {**self.expected_env_part["groups"], "target": [self.host.fqdn]},
            "action": {
                "name": "host_action_on_component",
                "owner_group": "service_one_component.component_1",
            },
        }
        self.assertDictEqual(env, expected_env)

    # redo correctly after ADCM-7517
    @unittest.skip("ADCM-7517")
    def test_env_for_action_process(self):
        # this case is quite BS even in original, won't fix it now
        action = Action.objects.get(prototype=self.cluster.prototype, display_name="action_on_cluster")
        spec = [
            {
                "name": "keystore_path",
                "type": "string",
            },
            {
                "name": "keystore_password",
                "type": "password",
            },
        ]
        process = Process.objects.create(
            action=action,
            target_id=1,
            target_type="test_type",
            owner_id=1,
            owner_type="test_type",
            flow_spec=[
                {
                    "name": "manage_ssl_stage",
                    "steps": [
                        {
                            "name": f"configure_step_{j + 1}",
                            "config_template": "blah",
                        }
                        for j in range(3)
                    ]
                    + [{"name": "operation_step_4"}],
                },
                {"name": "manage_kerberos_stage", "steps": [{"name": f"configure_step_{j + 1}"} for j in range(2)]},
            ],
            created_at=timezone.now(),
            sync_key=uuid4(),
            state="created",
        )

        for j in range(3):
            step = ProcessStep.objects.create(
                process=process,
                name=f"configure_step_{j + 1}",
                display_name=f"Configure Step {j + 1}",
                step_spec=spec,
                created_at=timezone.now(),
                state=ProcessState.COMPLETED,
            )
            ProcessStepInput.objects.create(
                step=step,
                configuration={
                    "values": {
                        "keystore_path": f"/etc/security/ssl/step{j + 1}",
                        "keystore_password": {"__ansible_vault": ansible_encrypt_and_format("pass")},
                    },
                    "attributes": {},
                },
                created_at=timezone.now(),
            )
        ProcessStep.objects.create(
            process=process,
            name="operation_step_4",
            display_name="Operation Step 4",
            step_spec={"operation": {"button": "button operation"}},
            created_at=timezone.now(),
            state="created",
        )
        args = TaskArgs(
            target_object=self.cluster,
            owner_object=self.cluster,
            action=self.cluster_action,
            wizard_process_id=process.pk,
        )
        encrypted_env = self.context_gatherer.prepare_context_for_task(args=args)
        env = decrypt_secrets(source=encrypted_env)
        expected_env = {
            **self.expected_env_part,
            "action": {
                "name": "action_on_cluster",
                "owner_group": "CLUSTER",
                "process": {
                    # don't even ask
                    "current": None,
                    "stages": {
                        "manage_ssl_stage": {
                            "configure_step_1": {
                                "config": {"keystore_path": "/etc/security/ssl/step1", "keystore_password": "pass"}
                            },
                            "configure_step_2": {
                                "config": {"keystore_path": "/etc/security/ssl/step2", "keystore_password": "pass"}
                            },
                            "configure_step_3": {
                                "config": {"keystore_path": "/etc/security/ssl/step3", "keystore_password": "pass"}
                            },
                        },
                        "manage_kerberos_stage": {
                            "configure_step_1": {
                                "config": {"keystore_path": "/etc/security/ssl/step1", "keystore_password": "pass"}
                            },
                            "configure_step_2": {
                                "config": {"keystore_path": "/etc/security/ssl/step2", "keystore_password": "pass"}
                            },
                        },
                    },
                },
            },
        }
        self.assertDictEqual(env, expected_env)
