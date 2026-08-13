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
from cm.models import Component, Host, Prototype
from tests.dependencies import RBACScenariosDummy
from tests.suites import ADCMPluginExecutorSuite

from ansible_plugin.errors import PluginContextError, PluginRuntimeError, PluginValidationError
from ansible_plugin.executors.add_host import ADCMAddHostPluginExecutor

EXECUTOR_MODULE = "ansible_plugin.executors.add_host"


class TestEffectsOfADCMAnsiblePlugins(ADCMPluginExecutorSuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.provider_2 = cls.uc.add_provider(bundle=cls.provider_bundle, name="Second Provider")

        bundle = cls.uc.upload_bundle(cls.bundles_dir / "second_provider")
        cls.target_provider = cls.uc.add_provider(bundle=bundle, name="Target Provider")
        cls.host_prototype = Prototype.objects.get(bundle=bundle, type="host")
        cls.tp_host = cls.uc.add_host(provider=cls.target_provider, fqdn="of-target-provider", cluster=cls.cluster)

        cls.service_1, *_ = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster)
        cls.component_1 = Component.objects.filter(service=cls.service_1).first()

        cls.uc.set_hostcomponent(
            cluster=cls.cluster,
            entries=((cls.tp_host, cls.component_1),),
        )

    def test_add_host_success(self) -> None:
        task = self.prepare_task(owner=self.target_provider, name="dummy")
        job, *_ = self.get_task_jobs(task.id)

        with self.subTest("Both fqdn and description"):
            executor = self.prepare_executor(
                executor_type=ADCMAddHostPluginExecutor,
                call_arguments="""
                    fqdn: special
                    description: this is the best host ever
                """,
                call_context=job,
            )

            with patch(f"{EXECUTOR_MODULE}.add_host") as add_host_mock:
                result = executor.execute()

            self.assertIsNone(result.error)
            add_host_mock.assert_called_once_with(
                provider=self.target_provider,
                prototype=self.host_prototype,
                fqdn="special",
                description="this is the best host ever",
                rbac_scenarios=RBACScenariosDummy(),
            )

        with self.subTest("Only fqdn"):
            executor = self.prepare_executor(
                executor_type=ADCMAddHostPluginExecutor, call_arguments={"fqdn": "cool"}, call_context=job
            )

            with patch(f"{EXECUTOR_MODULE}.add_host") as add_host_mock:
                result = executor.execute()

            self.assertIsNone(result.error)
            add_host_mock.assert_called_once_with(
                provider=self.target_provider,
                prototype=self.host_prototype,
                fqdn="cool",
                description="",
                rbac_scenarios=RBACScenariosDummy(),
            )

        with self.subTest("Check return value"):
            fqdn = "best-ever"
            executor = self.prepare_executor(
                executor_type=ADCMAddHostPluginExecutor,
                call_arguments={"fqdn": fqdn, "description": ""},
                call_context=job,
            )
            result = executor.execute()

            self.assertIsNone(result.error)
            self.assertTrue(result.changed)
            self.assertEqual(result.value, {"host_id": Host.objects.get(fqdn=fqdn).id})

    def test_add_host_forbidden_arg_fail(self):
        task = self.prepare_task(owner=self.target_provider, name="dummy")
        job, *_ = self.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMAddHostPluginExecutor,
            call_arguments="""
                fqdn: special
                test: arg
                description: this is the best host ever
            """,
            call_context=job,
        )

        with patch(f"{EXECUTOR_MODULE}.add_host") as add_host_mock:
            result = executor.execute()

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("test - Extra inputs are not permitted", result.error.message)
        add_host_mock.assert_not_called()

    def test_duplicate_fqdn_fail(self) -> None:
        task = self.prepare_task(owner=self.target_provider, name="dummy")
        job, *_ = self.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMAddHostPluginExecutor, call_arguments={"fqdn": self.host_1.fqdn}, call_context=job
        )

        result = executor.execute()

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertIn("Failed to create host due to IntegrityError", result.error.message)

    def test_incorrect_context_call_fail(self) -> None:
        for object_ in (self.cluster, self.service_1, self.component_1, self.tp_host):
            name = object_.__class__.__name__
            with self.subTest(name):
                task = self.prepare_task(owner=object_, name="dummy")
                job, *_ = self.get_task_jobs(task.id)
                executor = self.prepare_executor(
                    executor_type=ADCMAddHostPluginExecutor,
                    call_arguments={"fqdn": f"cool-{name.lower()}"},
                    call_context=job,
                )

                result = executor.execute()

                self.assertIsInstance(result.error, PluginContextError)
                self.assertIn(
                    "Plugin should be called only in context of provider, "
                    f"not {orm_object_to_core_type(object_).value}",
                    result.error.message,
                )
