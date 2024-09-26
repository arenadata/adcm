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

from cm.models import Action, Component
from cm.services.job.action import ActionRunPayload, run_action
from cm.tests.mocks.task_runner import ETFMockWithEnvPreparation, JobImitator, RunTaskMock


class TestEffectsOfADCMAnsiblePlugins(
    TestCaseWithCommonSetUpTearDown, ParallelReadyTestCase, BusinessLogicMixin, ADCMAnsiblePluginTestMixin
):
    def setUp(self) -> None:
        super().setUp()

        self.bundles_dir = Path(__file__).parent / "bundles"

        self.cluster_bundle = self.add_bundle(self.bundles_dir / "cluster")
        self.hostprovider_bundle = self.add_bundle(self.bundles_dir / "hostprovider")

        self.cluster = self.add_cluster(bundle=self.cluster_bundle, name="Just Cluster")

        self.hostprovider = self.add_provider(bundle=self.hostprovider_bundle, name="Just HP")
        self.host_1 = self.add_host(bundle=self.hostprovider_bundle, provider=self.hostprovider, fqdn="host-1")
        self.host_2 = self.add_host(bundle=self.hostprovider_bundle, provider=self.hostprovider, fqdn="host-2")

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

        with RunTaskMock(
            execution_target_factory=ETFMockWithEnvPreparation(
                change_jobs={0: JobImitator(call=plugin_call, use_call_return_code=True)}
            )
        ) as run_task:
            run_action(
                action=Action.objects.get(prototype=self.cluster.prototype, name="two_ansible_steps"),
                obj=self.cluster,
                payload=ActionRunPayload(),
            )

        self.assertIsNotNone(run_task.target_task)
        run_task.runner.run(task_id=run_task.target_task.pk)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")
        for job_id in run_task.target_task.joblog_set.values_list("id", flat=True):
            inventory = json.loads((self.directories["RUN_DIR"] / str(job_id) / "inventory.json").read_text())
            self.assertTrue(
                all(".add" not in key and ".remove" not in key for key in map(str.lower, inventory["all"]["children"]))
            )
