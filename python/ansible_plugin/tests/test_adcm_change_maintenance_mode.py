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

from cm.models import MaintenanceMode, ServiceComponent
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.errors import (
    PluginValidationError,
)
from ansible_plugin.executors.change_maintenance_mode import ADCMChangeMMExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins


class TestEffectsOfADCMAnsiblePlugins(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.component_1 = ServiceComponent.objects.filter(service=self.service_1).first()

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)

    def test_simple_call_success(self) -> None:
        for object_, arguments, expected_mm in (
            (self.service_1, {"type": "service", "value": False}, MaintenanceMode.OFF),
            (self.component_1, {"type": "component", "value": True}, MaintenanceMode.ON),
            (self.host_1, {"type": "host", "value": True}, MaintenanceMode.ON),
        ):
            object_.maintenance_mode = MaintenanceMode.CHANGING
            object_.save()

            with self.subTest(arguments["type"]):
                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)

                executor = self.prepare_executor(
                    executor_type=ADCMChangeMMExecutor,
                    call_arguments=arguments,
                    call_context=job,
                )

                result = executor.execute()
                self.assertIsNone(result.error)

                object_.refresh_from_db()
                self.assertEqual(object_.maintenance_mode, expected_mm)

    def test_call_from_another_context_success(self) -> None:
        self.service_1.maintenance_mode = MaintenanceMode.CHANGING
        self.service_1.save()
        self.component_1.maintenance_mode = MaintenanceMode.CHANGING
        self.component_1.save()
        self.host_1.maintenance_mode = MaintenanceMode.CHANGING
        self.host_1.save()

        with self.subTest("component-from-host"):
            task = self.prepare_task(owner=self.component_1, name="on_host", host=self.host_1)
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            executor = self.prepare_executor(
                executor_type=ADCMChangeMMExecutor,
                call_arguments="""
                  type: component
                  value: yes
                """,
                call_context=job,
            )

            result = executor.execute()
            self.assertIsNone(result.error)

            self.component_1.refresh_from_db()
            self.assertEqual(self.component_1.maintenance_mode, MaintenanceMode.ON)
            self.service_1.refresh_from_db()
            self.assertEqual(self.service_1.maintenance_mode, MaintenanceMode.CHANGING)
            self.host_1.refresh_from_db()
            self.assertEqual(self.host_1.maintenance_mode, MaintenanceMode.CHANGING)

        with self.subTest("service-from-component"):
            task = self.prepare_task(owner=self.component_1, name="dummy")
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            executor = self.prepare_executor(
                executor_type=ADCMChangeMMExecutor,
                call_arguments="""
                  type: service
                  value: no
                """,
                call_context=job,
            )

            result = executor.execute()
            self.assertIsNone(result.error)

            self.service_1.refresh_from_db()
            self.assertEqual(self.service_1.maintenance_mode, MaintenanceMode.OFF)
            self.component_1.refresh_from_db()
            self.assertEqual(self.component_1.maintenance_mode, MaintenanceMode.ON)
            self.host_1.refresh_from_db()
            self.assertEqual(self.host_1.maintenance_mode, MaintenanceMode.CHANGING)

    def test_incorrect_type_fail(self) -> None:
        for type_ in ("cluster", "provider"):
            with self.subTest(type_):
                task = self.prepare_task(owner=self.component_1, name="dummy")
                job, *_ = JobRepoImpl.get_task_jobs(task.id)
                executor = self.prepare_executor(
                    executor_type=ADCMChangeMMExecutor,
                    call_arguments=f"""
                      type: {type_}
                      value: true
                    """,
                    call_context=job,
                )

                result = executor.execute()

                self.assertIsInstance(result.error, PluginValidationError)
                self.assertIn(f"plugin can't be called to change {type_}'s MM", result.error.message)

    def test_forbidden_arg_fail(self):
        self.host_1.maintenance_mode = MaintenanceMode.CHANGING
        self.host_1.save()

        task = self.prepare_task(owner=self.host_1, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMChangeMMExecutor,
            call_arguments={"type": "host", "value": True, "arg": "ument"},
            call_context=job,
        )

        result = executor.execute()
        self.assertIsNotNone(result.error)
        self.host_1.refresh_from_db()
        self.assertEqual(self.host_1.maintenance_mode, MaintenanceMode.CHANGING)
