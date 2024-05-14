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

from unittest.mock import patch

from cm.converters import orm_object_to_core_type
from cm.models import Host, Prototype, ServiceComponent
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.errors import PluginContextError, PluginRuntimeError
from ansible_plugin.executors.delete_host import ADCMDeleteHostPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.add_host"


class TestEffectsOfADCMAnsiblePlugins(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.provider_2 = self.add_provider(bundle=self.provider_bundle, name="Second Provider")

        bundle = self.add_bundle(self.bundles_dir / "second_provider")
        self.another_provider = self.add_provider(bundle=bundle, name="Target Provider")
        self.host_prototype = Prototype.objects.get(bundle=bundle, type="host")
        self.tp_host = self.add_host(provider=self.another_provider, fqdn="of-target-provider")

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.component_1 = ServiceComponent.objects.filter(service=self.service_1).first()

        self.add_host_to_cluster(cluster=self.cluster, host=self.tp_host)

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.tp_host, self.component_1),),
        )

    def test_delete_host_success(self) -> None:
        task = self.prepare_task(owner=self.host_2, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMDeleteHostPluginExecutor, call_arguments={}, call_context=job
        )

        with patch("cm.api.cancel_locking_tasks") as cancel_tasks_mock:
            result = executor.execute()

        self.assertIsNone(result.error)

        self.assertFalse(Host.objects.filter(pk=self.host_2.pk).exists())
        self.assertTrue(Host.objects.filter(pk=self.host_1.pk).exists())
        self.assertTrue(Host.objects.filter(pk=self.tp_host.pk).exists())

        cancel_tasks_mock.assert_not_called()

    def test_delete_host_assigned_to_cluster_fail(self) -> None:
        task = self.prepare_task(owner=self.tp_host, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMDeleteHostPluginExecutor, call_arguments={}, call_context=job
        )

        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertIn("Unable to remove a host associated with a cluster", result.error.message)

        self.assertTrue(Host.objects.filter(pk=self.host_2.pk).exists())
        self.assertTrue(Host.objects.filter(pk=self.host_1.pk).exists())
        self.assertTrue(Host.objects.filter(pk=self.tp_host.pk).exists())

    def test_incorrect_context_call_fail(self) -> None:
        for object_ in (self.cluster, self.service_1, self.component_1, self.provider):
            name = object_.__class__.__name__
            with self.subTest(name):
                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)
                executor = self.prepare_executor(
                    executor_type=ADCMDeleteHostPluginExecutor,
                    call_arguments={"fqdn": f"cool-{name.lower()}"},
                    call_context=job,
                )

                result = executor.execute()

                self.assertIsInstance(result.error, PluginContextError)
                self.assertIn(
                    "Plugin should be called only in context of host, " f"not {orm_object_to_core_type(object_).value}",
                    result.error.message,
                )
