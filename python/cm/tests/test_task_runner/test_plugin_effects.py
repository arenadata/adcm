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

from adcm.tests.ansible import ADCMAnsiblePluginTestMixin
from adcm.tests.base import BusinessLogicMixin, ParallelReadyTestCase, TestCaseWithCommonSetUpTearDown
from ansible_plugin.executors.hostcomponent import ADCMHostComponentPluginExecutor
from use_cases.dto import RunActionDTO

from cm.models import Action, Component, JobLog, TaskLog
from cm.tests.dependencies import WithDishkaContainer
from cm.tests.mocks.task_runner import ETFMockWithEnvPreparation, JobImitator
from cm.tests.test_action_host_group import ScheduleTask


class TestEffectsOfADCMAnsiblePlugins(
    WithDishkaContainer,
    TestCaseWithCommonSetUpTearDown,
    ParallelReadyTestCase,
    BusinessLogicMixin,
    ADCMAnsiblePluginTestMixin,
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # shouldn't be here
        from api_v2.tests.setup.overrides import get_task_runner_manager

        cls.task_runner = get_task_runner_manager()

    def setUp(self) -> None:
        super().setUp()

        self.bundles_dir = Path(__file__).parent / "bundles"

        self.cluster_bundle = self.add_bundle(self.bundles_dir / "cluster")
        self.provider_bundle = self.add_bundle(self.bundles_dir / "provider")

        self.cluster = self.add_cluster(bundle=self.cluster_bundle, name="Just Cluster")

        self.provider = self.add_provider(bundle=self.provider_bundle, name="Just HP")
        self.host_1 = self.add_host(provider=self.provider, fqdn="host-1")
        self.host_2 = self.add_host(provider=self.provider, fqdn="host-2")

    def test_adcm_hc_should_not_cause_hc_acl_effect(self) -> None:
        service = self.add_services_to_cluster(["simple"], cluster=self.cluster).first()
        component_1, component_2 = Component.objects.filter(service=service).all()

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)

        self.set_hostcomponent(
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
            container.get(ScheduleTask).do(action_orm=action, target=self.cluster, payload=RunActionDTO())

        task_id = self.task_runner.expect_task_launched().id

        etf = ETFMockWithEnvPreparation(change_jobs={0: JobImitator(call=plugin_call, use_call_return_code=True)})
        self.task_runner.run_task(task_id=task_id, execution_target_factory=etf)

        task_status = TaskLog.objects.values_list("status", flat=True).get(id=task_id)
        self.assertEqual(task_status, "success")

        for job_id in JobLog.objects.filter(task_id=task_id).values_list("id", flat=True):
            inventory = json.loads((self.directories["RUN_DIR"] / str(job_id) / "inventory.json").read_text())
            self.assertTrue(
                all(".add" not in key and ".remove" not in key for key in map(str.lower, inventory["all"]["children"]))
            )
