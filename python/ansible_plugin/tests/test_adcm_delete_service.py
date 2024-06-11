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

from cm.converters import orm_object_to_core_type
from cm.models import ClusterObject, HostComponent, ServiceComponent
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.errors import PluginContextError, PluginTargetDetectionError
from ansible_plugin.executors.delete_service import ADCMDeleteServicePluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.add_host"


class TestEffectsOfADCMAnsiblePlugins(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.service_2 = self.add_services_to_cluster(["service_2"], cluster=self.cluster).first()
        self.component_1 = ServiceComponent.objects.filter(service=self.service_1).first()

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)

        self.initial_hc = self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, self.component_1),),
        )

    def test_delete_service_from_cluster_context_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMDeleteServicePluginExecutor,
            call_arguments="""
                service: service_1
            """,
            call_context=job,
        )

        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertFalse(ClusterObject.objects.filter(pk=self.service_1.pk).exists())
        self.assertTrue(ClusterObject.objects.filter(pk=self.service_2.pk).exists())
        self.assertEqual(HostComponent.objects.filter(cluster_id=self.cluster.pk).count(), 0)

    def test_delete_service_forbidden_arg_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMDeleteServicePluginExecutor,
            call_arguments="""
                service: service_1
                argument: value
            """,
            call_context=job,
        )

        result = executor.execute()

        self.assertIsNotNone(result.error)
        self.assertTrue(ClusterObject.objects.filter(pk=self.service_1.pk).exists())

    def test_delete_service_from_own_context(self) -> None:
        task = self.prepare_task(owner=self.service_2, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMDeleteServicePluginExecutor,
            call_arguments={},
            call_context=job,
        )

        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(ClusterObject.objects.filter(pk=self.service_1.pk).exists())
        self.assertFalse(ClusterObject.objects.filter(pk=self.service_2.pk).exists())

        actual = list(HostComponent.objects.values_list("host_id", "component_id").filter(cluster_id=self.cluster.pk))
        expected = [(entry.host_id, entry.component_id) for entry in self.initial_hc]
        self.assertEqual(actual, expected)

    def test_delete_service_by_name_from_service_context(self) -> None:
        task = self.prepare_task(owner=self.service_1, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMDeleteServicePluginExecutor,
            call_arguments={"service": self.service_2.name},
            call_context=job,
        )

        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(ClusterObject.objects.filter(pk=self.service_1.pk).exists())
        self.assertFalse(ClusterObject.objects.filter(pk=self.service_2.pk).exists())

    def test_delete_non_existing_service_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMDeleteServicePluginExecutor,
            call_arguments={"service": "does not exist"},
            call_context=job,
        )

        result = executor.execute()

        self.assertIsInstance(result.error, PluginTargetDetectionError)
        self.assertIn("Failed to locate service", result.error.message)

    def test_incorrect_context_call_fail(self) -> None:
        for object_ in (self.component_1, self.provider, self.host_1):
            name = object_.__class__.__name__
            with self.subTest(name):
                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)
                executor = self.prepare_executor(
                    executor_type=ADCMDeleteServicePluginExecutor,
                    call_arguments={"service": f"cool-{name.lower()}"},
                    call_context=job,
                )

                result = executor.execute()

                self.assertIsInstance(result.error, PluginContextError)
                self.assertIn(
                    "Plugin should be called only in context of cluster or service, "
                    f"not {orm_object_to_core_type(object_).value}",
                    result.error.message,
                )
