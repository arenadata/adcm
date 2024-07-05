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

from operator import itemgetter

from cm.converters import orm_object_to_core_type
from cm.models import HostComponent, ServiceComponent
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.errors import PluginContextError, PluginIncorrectCallError, PluginRuntimeError
from ansible_plugin.executors.hostcomponent import ADCMHostComponentPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins


class TestEffectsOfADCMAnsiblePlugins(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.component_1 = ServiceComponent.objects.filter(service=self.service_1).first()

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)

    def get_current_hc_dicts(self) -> list[dict]:
        return list(HostComponent.objects.values("service_id", "component_id", "host_id").filter(cluster=self.cluster))

    def test_simple_call_success(self) -> None:
        for object_ in (self.cluster, self.service_1, self.component_1):
            with self.subTest(object_.__class__.__name__):
                self.set_hostcomponent(
                    cluster=self.cluster,
                    entries=((self.host_1, self.component_1),),
                )
                hostcomponent = self.get_current_hc_dicts()
                self.assertEqual(len(hostcomponent), 1)
                expected_hc = sorted(
                    (hostcomponent[0], {**hostcomponent[0], "host_id": self.host_2.id}), key=itemgetter("host_id")
                )

                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)

                executor = self.prepare_executor(
                    executor_type=ADCMHostComponentPluginExecutor,
                    call_arguments=f"""
                        operations:
                          - action: add
                            service: {self.service_1.name}
                            component: {self.component_1.name}
                            host: {self.host_2.fqdn}
                    """,
                    call_context=job,
                )

                result = executor.execute()
                self.assertIsNone(result.error)

                actual_hc = sorted(self.get_current_hc_dicts(), key=itemgetter("host_id"))
                self.assertEqual(len(actual_hc), 2)
                self.assertListEqual(actual_hc, expected_hc)

    def test_simple_call_forbidden_arg_fail(self) -> None:
        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, self.component_1),),
        )
        hostcomponent = self.get_current_hc_dicts()
        self.assertEqual(len(hostcomponent), 1)
        expected_hc = [hostcomponent[0]]

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        extra_arg_outer = f"""
        test: arg
        operations:
          - action: add
            service: {self.service_1.name}
            component: {self.component_1.name}
            host: {self.host_2.fqdn}
        """
        extra_arg_inner = f"""
        operations:
          - action: add
            test: arg
            service: {self.service_1.name}
            component: {self.component_1.name}
            host: {self.host_2.fqdn}
        """
        for invalid_args in (extra_arg_outer, extra_arg_inner):
            with self.subTest(call_arguments=invalid_args):
                executor = self.prepare_executor(
                    executor_type=ADCMHostComponentPluginExecutor,
                    call_arguments=invalid_args,
                    call_context=job,
                )

                result = executor.execute()
                self.assertIsNotNone(result.error)

                actual_hc = sorted(self.get_current_hc_dicts(), key=itemgetter("host_id"))
                self.assertEqual(len(actual_hc), 1)
                self.assertListEqual(actual_hc, expected_hc)

    def test_complex_call_success(self) -> None:
        service_2 = self.add_services_to_cluster(["service_2"], cluster=self.cluster).get()
        component_2 = self.service_1.servicecomponent_set.get(prototype__name="component_2")
        component_3 = service_2.servicecomponent_set.get(prototype__name="component_1")
        component_4 = service_2.servicecomponent_set.get(prototype__name="component_2")

        object_ = self.service_1

        expected_hc = sorted(
            (
                {"host_id": self.host_2.id, "component_id": component_4.id, "service_id": service_2.id},
                {"host_id": self.host_2.id, "component_id": self.component_1.id, "service_id": self.service_1.id},
                {"host_id": self.host_1.id, "component_id": component_2.id, "service_id": self.service_1.id},
            ),
            key=itemgetter("component_id"),
        )

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, self.component_1), (self.host_2, component_3), (self.host_2, component_4)),
        )

        task = self.prepare_task(owner=object_, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMHostComponentPluginExecutor,
            call_arguments={
                "operations": [
                    {
                        "action": "add",
                        "service": self.service_1.name,
                        "component": self.component_1.name,
                        "host": self.host_2.fqdn,
                    },
                    {
                        "action": "remove",
                        "service": self.service_1.name,
                        "component": self.component_1.name,
                        "host": self.host_1.fqdn,
                    },
                    {
                        "action": "add",
                        "service": self.service_1.name,
                        "component": component_2.name,
                        "host": self.host_1.fqdn,
                    },
                    {
                        "action": "remove",
                        "service": service_2.name,
                        "component": component_3.name,
                        "host": self.host_2.fqdn,
                    },
                ]
            },
            call_context=job,
        )

        result = executor.execute()
        self.assertIsNone(result.error)

        self.assertEqual(sorted(self.get_current_hc_dicts(), key=itemgetter("component_id")), expected_hc)

    def test_incorrect_context_call_fail(self) -> None:
        for object_ in (self.provider, self.host_1):
            name = object_.__class__.__name__
            with self.subTest(name):
                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)
                executor = self.prepare_executor(
                    executor_type=ADCMHostComponentPluginExecutor,
                    call_arguments={"operations": []},
                    call_context=job,
                )

                result = executor.execute()

                self.assertIsInstance(result.error, PluginContextError)
                self.assertIn(
                    "Plugin should be called only in context of cluster or component or service, "
                    f"not {orm_object_to_core_type(object_).value}",
                    result.error.message,
                )

    def test_call_for_action_with_hc_fail(self) -> None:
        object_ = self.cluster

        task = self.prepare_task(owner=object_, name="with_hc")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMHostComponentPluginExecutor,
            call_arguments=f"""
                operations:
                  - action: add
                    service: {self.service_1.name}
                    component: {self.component_1.name}
                    host: {self.host_2.fqdn}
            """,
            call_context=job,
        )

        result = executor.execute()

        self.assertIsInstance(result.error, PluginIncorrectCallError)
        self.assertEqual(result.error.message, "You can not change hc in plugin for action with hc_acl")

    def test_add_already_existing_fail(self) -> None:
        object_ = self.service_1
        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, self.component_1),),
        )
        expected_hc = self.get_current_hc_dicts()

        task = self.prepare_task(owner=object_, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMHostComponentPluginExecutor,
            call_arguments=f"""
                operations:
                  - action: add
                    service: {self.service_1.name}
                    component: {self.component_1.name}
                    host: {self.host_1.fqdn}
            """,
            call_context=job,
        )

        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertEqual(
            result.error.message, f'There is already component "{self.component_1.name}" on host "{self.host_1.fqdn}"'
        )
        self.assertEqual(self.get_current_hc_dicts(), expected_hc)

    def test_remove_absent_fail(self) -> None:
        object_ = self.component_1
        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, self.component_1),),
        )
        expected_hc = self.get_current_hc_dicts()

        task = self.prepare_task(owner=object_, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMHostComponentPluginExecutor,
            call_arguments=f"""
                        operations:
                          - action: remove
                            service: {self.service_1.name}
                            component: {self.component_1.name}
                            host: {self.host_2.fqdn}
                    """,
            call_context=job,
        )

        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertEqual(
            result.error.message, f'There is no component "{self.component_1.name}" on host "{self.host_2.fqdn}"'
        )
        self.assertEqual(self.get_current_hc_dicts(), expected_hc)
