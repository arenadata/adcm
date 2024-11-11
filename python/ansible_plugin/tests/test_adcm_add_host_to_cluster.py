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
from cm.models import Component
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.errors import PluginContextError, PluginValidationError
from ansible_plugin.executors.add_host_to_cluster import ADCMAddHostToClusterPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.add_host_to_cluster"


class TestAddHostToClusterPluginExecutor(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.component_1 = Component.objects.filter(service=self.service_1).first()

        self.host_3 = self.add_host(provider=self.host_1.provider, fqdn="host-3")

    def test_add_host_to_cluster_success(self) -> None:
        with self.subTest("Cluster Context | by fqdn"):
            task = self.prepare_task(owner=self.cluster, name="dummy")
            job, *_ = JobRepoImpl.get_task_jobs(task.id)
            executor = self.prepare_executor(
                executor_type=ADCMAddHostToClusterPluginExecutor,
                call_arguments=f"""
                    fqdn: {self.host_1.fqdn}
                """,
                call_context=job,
            )

            result = executor.execute()

            self.assertIsNone(result.error)
            self.assertTrue(result.changed)
            self.host_1.refresh_from_db()
            self.assertEqual(self.host_1.cluster_id, self.cluster.id)

        with self.subTest("Service Context | by id"):
            task = self.prepare_task(owner=self.service_1, name="dummy")
            job, *_ = JobRepoImpl.get_task_jobs(task.id)
            executor = self.prepare_executor(
                executor_type=ADCMAddHostToClusterPluginExecutor,
                call_arguments=f"""
                    host_id: {self.host_2.id}
                """,
                call_context=job,
            )

            result = executor.execute()

            self.assertIsNone(result.error)
            self.assertTrue(result.changed)
            self.host_2.refresh_from_db()
            self.assertEqual(self.host_2.cluster_id, self.cluster.id)

        with self.subTest("Component Context | by id"):
            task = self.prepare_task(owner=self.service_1, name="dummy")
            job, *_ = JobRepoImpl.get_task_jobs(task.id)
            executor = self.prepare_executor(
                executor_type=ADCMAddHostToClusterPluginExecutor,
                call_arguments=f"""
                    host_id: {self.host_3.id}
                """,
                call_context=job,
            )

            result = executor.execute()

            self.assertIsNone(result.error)
            self.assertTrue(result.changed)
            self.host_3.refresh_from_db()
            self.assertEqual(self.host_3.cluster_id, self.cluster.id)

    def test_both_arguments_specified_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMAddHostToClusterPluginExecutor,
            call_arguments={"fqdn": self.host_2.fqdn, "host_id": self.host_1.id},
            call_context=job,
        )

        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_2.refresh_from_db()
        self.assertEqual(self.host_2.cluster_id, self.cluster.id)
        self.host_1.refresh_from_db()
        self.assertIsNone(self.host_1.cluster_id)

    def test_forbidden_arg_fail(self):
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMAddHostToClusterPluginExecutor,
            call_arguments={"host_id": self.host_2.id, "some": "argument"},
            call_context=job,
        )

        result = executor.execute()

        self.assertIsNotNone(result.error)
        self.assertFalse(result.changed)
        self.host_2.refresh_from_db()
        self.assertIsNone(self.host_2.cluster_id)

    def test_absent_arguments_call_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMAddHostToClusterPluginExecutor,
            call_arguments={},
            call_context=job,
        )

        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("either `fqdn` or `host_id` has to be specified", result.error.message)

    def test_incorrect_context_call_fail(self) -> None:
        for object_ in (self.provider, self.host_1):
            name = object_.__class__.__name__
            with self.subTest(name):
                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)
                executor = self.prepare_executor(
                    executor_type=ADCMAddHostToClusterPluginExecutor,
                    call_arguments={"fqdn": f"cool-{name.lower()}"},
                    call_context=job,
                )

                result = executor.execute()

                self.assertIsInstance(result.error, PluginContextError)
                self.assertIn(
                    "Plugin should be called only in context of cluster or component or service, "
                    f"not {orm_object_to_core_type(object_).value}",
                    result.error.message,
                )
