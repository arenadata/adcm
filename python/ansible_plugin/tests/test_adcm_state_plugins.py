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

from typing import TypeAlias

from cm.legacy.services.job.run.repo import JobRepoImpl
from cm.models import Cluster, Component, Host, Provider, Service
from tests.suites import ADCMPluginExecutorSuite

from ansible_plugin.base import ADCMAnsiblePluginExecutor
from ansible_plugin.executors.multi_state_set import ADCMMultiStateSetPluginExecutor
from ansible_plugin.executors.multi_state_unset import ADCMMultiStateUnsetPluginExecutor
from ansible_plugin.executors.state import ADCMStatePluginExecutor

ADCMObject: TypeAlias = Cluster | Service | Component | Provider | Host


class TestADCMStatePluginExecutors(ADCMPluginExecutorSuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.uc.add_services_to_cluster(["service_1", "service_2"], cluster=cls.cluster)
        cls.service = Service.objects.get(prototype__name="service_1")
        cls.component = cls.service.components.first()

        cls.target_state = "brand new object's (multi)state"
        cls.default_multi_state = "default multi-state"

        cls.another_provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="another_provider")

        provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="Control provider")
        cluster = cls.uc.add_cluster(bundle=cls.cluster_bundle, name="Control cluster")
        service_2 = Service.objects.get(prototype__name="service_2")
        other_components = Component.objects.filter(cluster=cls.cluster).exclude(pk=cls.component.pk)
        cls.control_objects = [cluster, service_2, *list(other_components), provider, cls.host_2]

        cls.allowed_owner_target_args = (
            (cls.cluster, cls.cluster, {"type": "cluster", "state": cls.target_state}),
            (
                cls.cluster,
                cls.service,
                {"type": "service", "service_name": cls.service.name, "state": cls.target_state},
            ),
            (
                cls.cluster,
                cls.component,
                {
                    "type": "component",
                    "service_name": cls.service.name,
                    "component_name": cls.component.name,
                    "state": cls.target_state,
                },
            ),
            (cls.service, cls.cluster, {"type": "cluster", "state": cls.target_state}),
            (cls.service, cls.service, {"type": "service", "state": cls.target_state}),
            (
                cls.service,
                cls.component,
                {"type": "component", "component_name": cls.component.name, "state": cls.target_state},
            ),
            (cls.component, cls.cluster, {"type": "cluster", "state": cls.target_state}),
            (cls.component, cls.service, {"type": "service", "state": cls.target_state}),
            (cls.component, cls.component, {"type": "component", "state": cls.target_state}),
            (cls.provider, cls.provider, {"type": "provider", "state": cls.target_state}),
            (cls.provider, cls.host_1, {"type": "host", "host_id": cls.host_1.pk, "state": cls.target_state}),
            (cls.host_1, cls.provider, {"type": "provider", "state": cls.target_state}),
            (cls.host_1, cls.host_1, {"type": "host", "state": cls.target_state}),
        )
        cls.forbidden_owner_target_args = (
            (  # owner host, target host, not self
                cls.host_1,
                cls.host_2,
                {"type": "host", "host_id": cls.host_2.pk, "state": cls.target_state},
            ),
            (  # foreign host
                cls.another_provider,
                cls.host_2,
                {"type": "host", "host_id": cls.host_2.pk, "state": cls.target_state},
            ),
            # forbidden args for target type
            (cls.cluster, cls.cluster, {"type": "cluster", "state": cls.target_state, "test": "test"}),
            (cls.service, cls.cluster, {"type": "cluster", "state": cls.target_state, "service_name": "some_name"}),
            (
                cls.component,
                cls.cluster,
                {"type": "cluster", "state": cls.target_state, "component_name": "some_name"},
            ),
            (cls.cluster, cls.cluster, {"type": "cluster", "state": cls.target_state, "host_id": 8}),
            (
                cls.service,
                cls.service,
                {"type": "service", "state": cls.target_state, "component_name": "some_name"},
            ),
            (cls.component, cls.service, {"type": "service", "state": cls.target_state, "host_id": 8}),
            (cls.component, cls.component, {"type": "component", "state": cls.target_state, "host_id": 8}),
            (
                cls.provider,
                cls.provider,
                {"type": "provider", "state": cls.target_state, "service_name": "some_name"},
            ),
            (
                cls.provider,
                cls.provider,
                {"type": "provider", "state": cls.target_state, "component_name": "some_name"},
            ),
            (cls.host_1, cls.provider, {"type": "provider", "state": cls.target_state, "host_id": 8}),
            (cls.host_1, cls.host_1, {"type": "host", "state": cls.target_state, "service_name": "some_name"}),
            (
                cls.provider,
                cls.host_1,
                {"type": "host", "host_id": cls.host_1.pk, "state": cls.target_state, "component_name": "some_name"},
            ),
        )

    def _execute_test(
        self,
        owner: ADCMObject,
        target: ADCMObject,
        call_arguments: str | dict,
        executor_class: type[ADCMAnsiblePluginExecutor],
        expected_value: str | list[str] | None = None,
        expect_fail: bool = False,
    ) -> None:
        target._multi_state = {}
        target.save(update_fields=["_multi_state"])

        match executor_class.__name__:
            case ADCMStatePluginExecutor.__name__:
                model_field = "state"
                control_value = ["created"]
                expected_value = control_value[0] if expect_fail else expected_value
            case ADCMMultiStateSetPluginExecutor.__name__:
                target.set_multi_state(multi_state=self.default_multi_state)
                model_field = "multi_state"
                control_value = [[]]
                expected_value = [self.default_multi_state] if expect_fail else expected_value
            case ADCMMultiStateUnsetPluginExecutor.__name__:
                target.set_multi_state(multi_state=self.default_multi_state)
                target.set_multi_state(multi_state=self.target_state)
                model_field = "multi_state"
                control_value = [[]]
                expected_value = (
                    sorted([self.target_state, self.default_multi_state]) if expect_fail else expected_value
                )
            case _:
                raise NotImplementedError(str(executor_class))

        task = self.prepare_task(owner=owner, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=executor_class,
            call_arguments=call_arguments,
            call_context=job,
        )
        result = executor.execute()

        if expect_fail:
            self.assertIsNotNone(result.error)
            self.assertFalse(result.changed)
        else:
            self.assertIsNone(result.error)
            self.assertTrue(result.changed)

        target.refresh_from_db()
        self.assertEqual(getattr(target, model_field), expected_value)

        if expect_fail:
            return

        # check control objects' states
        states = []
        for object_ in self.control_objects:
            object_.refresh_from_db()
            states.append(getattr(object_, model_field))

        self.assertListEqual(states, control_value * len(self.control_objects))

    def test_success_scenarios(self):
        for owner, target, call_args in self.allowed_owner_target_args:
            for executor_class, expected_value, extra_args in (
                (ADCMStatePluginExecutor, self.target_state, {}),
                (ADCMMultiStateSetPluginExecutor, sorted([self.default_multi_state, self.target_state]), {}),
                (ADCMMultiStateUnsetPluginExecutor, [self.default_multi_state], {}),
                (
                    ADCMMultiStateUnsetPluginExecutor,
                    sorted([self.default_multi_state, self.target_state]),
                    {"state": "absent state", "missing_ok": True},
                ),
            ):
                call_args = {**call_args, **extra_args}

                with self.subTest(
                    owner=owner,
                    target=target,
                    call_args=call_args,
                    executor_class=executor_class,
                    expected_value=expected_value,
                ):
                    self._execute_test(
                        owner=owner,
                        target=target,
                        call_arguments=call_args,
                        executor_class=executor_class,
                        expected_value=expected_value,
                    )

    def test_fail_scenarios(self):
        for owner, target, call_args in self.allowed_owner_target_args:
            for executor_class, extra_args in (
                (ADCMMultiStateUnsetPluginExecutor, {"state": "absent state", "missing_ok": False}),
                (ADCMMultiStateUnsetPluginExecutor, {"state": "absent state"}),  # check default missing_ok
            ):
                call_args = {**call_args, **extra_args}
                with self.subTest(owner=owner, target=target, call_args=call_args, executor_class=executor_class):
                    self._execute_test(
                        owner=owner,
                        target=target,
                        call_arguments=call_args,
                        executor_class=executor_class,
                        expect_fail=True,
                    )

    def test_forbidden_owner_targert_args(self):
        for owner, target, call_args in self.forbidden_owner_target_args:
            for executor_class, extra_args in (
                (ADCMStatePluginExecutor, {}),
                (ADCMMultiStateSetPluginExecutor, {}),
                (ADCMMultiStateUnsetPluginExecutor, {"state": "absent state", "missing_ok": True}),
            ):
                call_args = {**call_args, **extra_args}

                with self.subTest(owner=owner, target=target, call_args=call_args, executor_class=executor_class):
                    self._execute_test(
                        owner=owner,
                        target=target,
                        call_arguments=call_args,
                        executor_class=executor_class,
                        expect_fail=True,
                    )
