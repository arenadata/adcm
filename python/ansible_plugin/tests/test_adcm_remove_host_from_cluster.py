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

from ansible_plugin.errors import (
    PluginContextError,
    PluginRuntimeError,
    PluginTargetDetectionError,
    PluginValidationError,
)
from ansible_plugin.executors.remove_host_from_cluster import ADCMRemoveHostFromClusterPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.remove_host_from_cluster"


class TestRemoveHostFromClusterPluginExecutor(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.component_1 = Component.objects.filter(service=self.service_1).first()

        self.add_host_to_cluster(self.cluster, self.host_1)

    def test_remove_host_from_cluster_by_fqdn_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                fqdn: {self.host_1.fqdn}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_1.refresh_from_db()
        self.assertIsNotNone(self.host_1)
        self.assertIsNone(self.host_1.cluster_id)

    def test_remove_host_from_cluster_by_id_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_1.refresh_from_db()
        self.assertIsNotNone(self.host_1)
        self.assertIsNone(self.host_1.cluster_id)

    def test_remove_host_from_cluster_by_id_and_name_success(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
                fqdn: {self.host_1.fqdn}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_1.refresh_from_db()
        self.assertIsNotNone(self.host_1)
        self.assertIsNone(self.host_1.cluster_id)

    def test_remove_two_different_hosts_by_fqdn_and_id_success(self) -> None:
        self.add_host_to_cluster(self.cluster, self.host_2)
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
                fqdn: {self.host_2.fqdn}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_1.refresh_from_db()
        self.host_2.refresh_from_db()
        self.assertIsNotNone(self.host_1.cluster_id)
        self.assertIsNone(self.host_2.cluster_id)

    def test_remove_two_different_hosts_by_id_success(self) -> None:
        self.add_host_to_cluster(self.cluster, self.host_2)
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
                host_id: {self.host_2.id}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_1.refresh_from_db()
        self.host_2.refresh_from_db()
        self.assertIsNotNone(self.host_1.cluster_id)
        self.assertIsNone(self.host_2.cluster_id)

    def test_remove_two_different_hosts_by_fqdn_success(self) -> None:
        self.add_host_to_cluster(self.cluster, self.host_2)
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                fqdn: {self.host_1.fqdn}
                fqdn: {self.host_2.fqdn}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_1.refresh_from_db()
        self.host_2.refresh_from_db()
        self.assertIsNotNone(self.host_1.cluster_id)
        self.assertIsNone(self.host_2.cluster_id)

    def test_remove_host_from_cluster_no_arguments_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments={},
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("either `fqdn` or `host_id` have to be specified", result.error.message)

    def test_remove_host_from_cluster_forbidden_arg_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
                argument: value
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNotNone(result.error)
        self.assertFalse(result.changed)
        self.host_1.refresh_from_db()
        self.assertIsNotNone(self.host_1.cluster_id)

    def test_remove_host_from_cluster_wrong_arguments_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                            name: {self.host_1.fqdn}
                        """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)

    def test_remove_host_from_cluster_no_host_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments="""
                            fqdn: "incorrect-fqdn"
                        """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginTargetDetectionError)
        self.assertIn(
            "Can't find host by given arguments: "
            "arguments=RemoveHostFromClusterArguments(fqdn='incorrect-fqdn', host_id=None)",
            result.error.message,
        )

    def test_remove_host_from_cluster_constraint_error(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        self.cluster.set_state("upgrading")

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertIn("It is forbidden to delete host from cluster in upgrade mode", result.error.message)

    def test_remove_host_from_cluster_with_component_on_host_constraint_error(self) -> None:
        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, Component.objects.get(service=self.service_1, prototype__name="component_1")),),
        )

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertIn("There are components on the host.", result.error.message)

    def test_remove_host_from_cluster_with_component_on_host_success(self) -> None:
        self.add_host_to_cluster(self.cluster, self.host_2)
        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_2, Component.objects.get(service=self.service_1, prototype__name="component_1")),),
        )
        task = self.prepare_task(owner=self.component_1, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.host_1.refresh_from_db()
        self.assertIsNotNone(self.host_1)
        self.assertIsNone(self.host_1.cluster_id)

    def test_incorrect_context_call_fail(self) -> None:
        for object_ in (self.host_1, self.provider):
            name = object_.__class__.__name__
            with self.subTest(name):
                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)
                executor = self.prepare_executor(
                    executor_type=ADCMRemoveHostFromClusterPluginExecutor,
                    call_arguments=f"""
                        host_id: {self.host_1.id}
                    """,
                    call_context=job,
                )
                result = executor.execute()

                self.assertIsInstance(result.error, PluginContextError)
                self.assertIn(
                    "Plugin should be called only in context of cluster or component or service, "
                    f"not {orm_object_to_core_type(object_).value}",
                    result.error.message,
                )

    def test_incorrect_cluster_in_context_fail(self) -> None:
        cluster_2 = self.add_cluster(bundle=self.cluster_bundle, name="Another Cluster")
        task = self.prepare_task(owner=cluster_2, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_1.id}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertIn(f"Host {self.host_1.fqdn} is not in cluster id: {cluster_2.id}", result.error.message)

    def test_remove_unbound_host_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMRemoveHostFromClusterPluginExecutor,
            call_arguments=f"""
                host_id: {self.host_2.id}
            """,
            call_context=job,
        )
        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertIn(f"Host {self.host_2.fqdn} is unbound to any cluster", result.error.message)
