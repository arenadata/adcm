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
import json

from ansible_plugin.executors.hostcomponent import ADCMHostComponentPluginExecutor
from tests.dependencies import MockWithEnvProvider, make_overridden_container
from tests.suites import ADCMPluginExecutorSuite
from use_cases.dto import RunActionDTO

from cm.models import Action, Component, JobLog, TaskLog
from cm.tests.mocks.task_runner import JobImitator
from cm.tests.test_action_host_group import ScheduleTask


class TestEffectsOfADCMAnsiblePlugins(ADCMPluginExecutorSuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cls.bundles_dir = Path(__file__).parent / "bundles"

        cls.cluster_bundle = cls.uc.upload_bundle(cls.bundles_dir / "cluster")
        cls.provider_bundle = cls.uc.upload_bundle(cls.bundles_dir / "provider")

        cls.cluster = cls.uc.add_cluster(bundle=cls.cluster_bundle, name="Just Cluster")

        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Just HP")
        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="host-1")
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="host-2")

    def test_adcm_hc_should_not_cause_hc_acl_effect(self) -> None:
        service, *_ = self.uc.add_services_to_cluster(["simple"], cluster=self.cluster)
        component_1, component_2 = Component.objects.filter(service=service).all()

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)

        self.uc.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, component_1), (self.host_1, component_2), (self.host_2, component_1)),
        )

        operations = [
            {"action": "add", "service": service.name, "component": component_2.name, "host": self.host_2.name},
            {"action": "remove", "service": service.name, "component": component_1.name, "host": self.host_1.name},
        ]

        def plugin_call(executor):
            executor = self.prepare_executor(
                executor_type=ADCMHostComponentPluginExecutor,
                call_arguments={"operations": operations},
                call_context=int(executor._config.work_dir.name),  # id of job
            )
            result = executor.execute()
            if result.error:
                return 1

            return 0

        action = Action.objects.get(prototype=self.cluster.prototype, name="two_ansible_steps")
        with self.container() as container:
            launched_task = container.get(ScheduleTask).do(
                action_orm=action, target=self.cluster, payload=RunActionDTO()
            )

        task_id = launched_task.pk

        container = make_overridden_container(
            MockWithEnvProvider(change_jobs={0: JobImitator(call=plugin_call, use_call_return_code=True)})
        )
        self.task_runner(container).launch_task(task_id=task_id)

        task_status = TaskLog.objects.values_list("status", flat=True).get(id=task_id)
        self.assertEqual(task_status, "success")

        for job_id in JobLog.objects.filter(task_id=task_id).values_list("id", flat=True):
            inventory = json.loads((self.directories.run / str(job_id) / "inventory.json").read_text())
            self.assertTrue(
                all(".add" not in key and ".remove" not in key for key in map(str.lower, inventory["all"]["children"]))
            )
