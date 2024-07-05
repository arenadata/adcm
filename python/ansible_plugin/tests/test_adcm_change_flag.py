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

from typing import Collection
from unittest.mock import patch

from cm.models import ConcernItem, ServiceComponent
from cm.services.concern.flags import BuiltInFlag, ConcernFlag, lower_all_flags, raise_flag
from cm.services.job.run.repo import JobRepoImpl
from core.job.types import Task
from core.types import ADCMCoreType, CoreObjectDescriptor

from ansible_plugin.executors.change_flag import ADCMChangeFlagPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.change_flag"


class TestEffectsOfADCMAnsiblePlugins(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        ConcernItem.objects.all().delete()

        self.service_1, self.service_2 = self.add_services_to_cluster(
            ["service_1", "service_2"], cluster=self.cluster
        ).order_by("prototype__name")
        self.component_1, self.component_2 = (
            ServiceComponent.objects.filter(service=self.service_1).order_by("prototype__name").all()
        )

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, self.component_1), (self.host_1, self.component_2), (self.host_2, self.component_1)),
        )

    def execute_plugin_patched(self, task, arguments):
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor, call_arguments=arguments, call_context=job
        )

        with (
            patch(f"{EXECUTOR_MODULE}.raise_flag") as raise_flag_mock,
            patch(f"{EXECUTOR_MODULE}.lower_flag") as lower_flag_mock,
            patch(f"{EXECUTOR_MODULE}.lower_all_flags") as lower_all_flags_mock,
            patch(f"{EXECUTOR_MODULE}.update_hierarchy_for_flag") as update_hierarchy_for_flag_mock,
        ):
            result = executor.execute()

        self.assertIsNone(result.error)

        return raise_flag_mock, lower_flag_mock, lower_all_flags_mock, update_hierarchy_for_flag_mock

    def check_raise_called(
        self, flag: ConcernFlag, task: Task, arguments: str | dict, targets: Collection[CoreObjectDescriptor]
    ) -> None:
        (
            raise_flag_mock,
            lower_flag_mock,
            lower_all_flags_mock,
            update_hierarchy_for_flag_mock,
        ) = self.execute_plugin_patched(task, arguments)

        raise_flag_mock.assert_called_once_with(flag=flag, on_objects=targets)
        update_hierarchy_for_flag_mock.assert_called_once_with(flag=flag, on_objects=targets)
        lower_flag_mock.assert_not_called()
        lower_all_flags_mock.assert_not_called()

    def check_lower_called(
        self, flag_name: str, task: Task, arguments: str | dict, targets: Collection[CoreObjectDescriptor]
    ) -> None:
        (
            raise_flag_mock,
            lower_flag_mock,
            lower_all_flags_mock,
            update_hierarchy_for_flag_mock,
        ) = self.execute_plugin_patched(task, arguments)

        raise_flag_mock.assert_not_called()
        update_hierarchy_for_flag_mock.assert_not_called()
        lower_flag_mock.assert_called_once_with(name=flag_name, on_objects=targets)
        lower_all_flags_mock.assert_not_called()

    def check_lower_all_called(
        self, task: Task, arguments: str | dict, targets: Collection[CoreObjectDescriptor]
    ) -> None:
        (
            raise_flag_mock,
            lower_flag_mock,
            lower_all_flags_mock,
            update_hierarchy_for_flag_mock,
        ) = self.execute_plugin_patched(task, arguments)

        raise_flag_mock.assert_not_called()
        update_hierarchy_for_flag_mock.assert_not_called()
        lower_flag_mock.assert_not_called()
        lower_all_flags_mock.assert_called_once_with(on_objects=targets)

    def test_raise_flag_on_objects_success(self) -> None:
        flag = ConcernFlag(name="need_restart", message='You need to run action "Restart"')

        self.check_raise_called(
            flag=flag,
            task=self.prepare_task(owner=self.cluster, name="dummy"),
            arguments=f"""
                operation: up
                name: {flag.name}
                msg: '{flag.message}'
                objects:
                  - type: service
                    service_name: service_2
                  - type: component
                    service_name: service_1
                    component_name: component_2
            """,
            targets=(
                CoreObjectDescriptor(id=self.service_2.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=self.component_2.id, type=ADCMCoreType.COMPONENT),
            ),
        )

    def test_raise_default_flag_on_provider_from_context_success(self) -> None:
        flag = BuiltInFlag.ADCM_OUTDATED_CONFIG.value

        self.check_raise_called(
            flag=flag,
            task=self.prepare_task(owner=self.provider, name="dummy"),
            arguments="""
                operation: up
                name: adcm_outdated_config
            """,
            targets=(CoreObjectDescriptor(id=self.provider.id, type=ADCMCoreType.HOSTPROVIDER),),
        )

    def test_raise_default_flag_changed_message_on_component_from_context_success(self) -> None:
        default_flag = BuiltInFlag.ADCM_OUTDATED_CONFIG.value
        flag = ConcernFlag(
            name=default_flag.name, message="Your config is in pretty bad shape", cause=default_flag.cause
        )

        self.check_raise_called(
            flag=flag,
            task=self.prepare_task(owner=self.host_2, name="dummy"),
            arguments=f"""
                operation: up
                name: adcm_outdated_config
                msg: {flag.message}
            """,
            targets=(CoreObjectDescriptor(id=self.host_2.id, type=ADCMCoreType.HOST),),
        )

    def test_lower_with_name_component_host_action_from_context_success(self) -> None:
        flag_name = "some_flag"

        self.check_lower_called(
            flag_name=flag_name,
            task=self.prepare_task(owner=self.component_2, name="on_host", host=self.host_1),
            arguments=f"""
                operation: down
                name: {flag_name}
            """,
            targets=(CoreObjectDescriptor(id=self.component_2.id, type=ADCMCoreType.COMPONENT),),
        )

    def test_lower_all_service_context_from_objects_success(self) -> None:
        component = ServiceComponent.objects.get(prototype__name="component_2", service=self.service_2)

        self.check_lower_all_called(
            task=self.prepare_task(owner=self.service_2, name="dummy"),
            arguments="""
                operation: down
                objects:
                  - type: cluster
                  - type: service
                  - type: component
                    component_name: component_2
            """,
            targets=(
                CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER),
                CoreObjectDescriptor(id=self.service_2.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=component.id, type=ADCMCoreType.COMPONENT),
            ),
        )

    def test_lower_all_cluster_context_from_objects_success(self) -> None:
        self.check_lower_all_called(
            task=self.prepare_task(owner=self.cluster, name="dummy"),
            arguments="""
                operation: down
                objects:
                  - type: cluster
            """,
            targets=(CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER),),
        )

    def test_incorrect_name_fail(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor, call_arguments={"operation": "up"}, call_context=job
        )
        result = executor.execute()
        self.assertIsNotNone(result.error)
        self.assertEqual("`name` should be specified for `up` operation", result.error.message)

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor, call_arguments={"operation": "up", "name": ""}, call_context=job
        )
        result = executor.execute()
        self.assertIsNotNone(result.error)
        self.assertIn("`name` should be at least 1 symbol", result.error.message)

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor,
            call_arguments={"operation": "down", "name": ""},
            call_context=job,
        )
        result = executor.execute()
        self.assertIsNotNone(result.error)
        self.assertIn("`name` should be at least 1 symbol", result.error.message)

    def test_forbidden_arg_fail(self):
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor,
            call_arguments={"operation": "up", "name": "adcm_outdated_config", "test": "arg"},
            call_context=job,
        )
        result = executor.execute()

        self.assertIsNotNone(result.error)

    def test_hierarchy_is_updated_on_raise(self) -> None:
        flag_name = "custom"

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor,
            call_arguments={
                "operation": "up",
                "name": flag_name,
                "objects": [
                    {"type": "component", "service_name": self.service_1.name, "component_name": self.component_2.name},
                ],
            },
            call_context=job,
        )

        result = executor.execute()
        self.assertIsNone(result.error)

        self.assertEqual(self.cluster.concerns.count(), 1)
        self.assertTrue(
            self.cluster.concerns.filter(
                owner_id=self.component_2.id, owner_type=self.component_2.content_type
            ).exists()
        )

        self.assertEqual(self.service_1.concerns.count(), 1)
        self.assertTrue(
            self.service_1.concerns.filter(
                owner_id=self.component_2.id, owner_type=self.component_2.content_type
            ).exists()
        )

        self.assertEqual(self.service_2.concerns.count(), 0)

    def test_changed_on_raise(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor,
            call_arguments={
                "operation": "up",
                "name": "adcm_outdated_config",
                "objects": [
                    {"type": "component", "service_name": self.service_1.name, "component_name": self.component_2.name},
                ],
            },
            call_context=job,
        )

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertTrue(result.changed)

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertFalse(result.changed)

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertFalse(result.changed)

        lower_all_flags(on_objects=[CoreObjectDescriptor(id=self.component_2.id, type=ADCMCoreType.COMPONENT)])

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertTrue(result.changed)

    def test_changed_on_lower(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor,
            call_arguments={
                "operation": "down",
                "name": "adcm_outdated_config",
                "objects": [{"type": "cluster"}, {"type": "service", "service_name": self.service_1.name}],
            },
            call_context=job,
        )

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertFalse(result.changed)

        raise_flag(
            flag=BuiltInFlag.ADCM_OUTDATED_CONFIG.value,
            on_objects=(
                CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER),
                CoreObjectDescriptor(id=self.service_2.id, type=ADCMCoreType.SERVICE),
            ),
        )

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertTrue(result.changed)

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertFalse(result.changed)

    def test_changed_on_lower_all(self) -> None:
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        executor = self.prepare_executor(
            executor_type=ADCMChangeFlagPluginExecutor,
            call_arguments={
                "operation": "down",
                "objects": [
                    {"type": "cluster"},
                ],
            },
            call_context=job,
        )

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertFalse(result.changed)

        raise_flag(
            flag=BuiltInFlag.ADCM_OUTDATED_CONFIG.value,
            on_objects=(CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER),),
        )

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertTrue(result.changed)

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertFalse(result.changed)
