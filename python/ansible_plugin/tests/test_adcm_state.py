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

from cm.models import Cluster, ClusterObject, Host, HostProvider, ServiceComponent
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.executors.state import ADCMStatePluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

ADCM_OBJECT: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host


class TestADCMStatePluginExecutor(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        services = self.add_services_to_cluster(service_names=["service_1", "service_2"], cluster=self.cluster)
        self.service = services.get(prototype__name="service_1")
        self.component = self.service.servicecomponent_set.first()

        self.new_state = "brand new object's state"

        provider = self.add_provider(bundle=self.provider_bundle, name="Control provider")
        cluster = self.add_cluster(bundle=self.cluster_bundle, name="Control cluster")
        service_2 = services.get(prototype__name="service_2")
        other_components = ServiceComponent.objects.filter(cluster=self.cluster).exclude(pk=self.component.pk)
        self.control_objects = [cluster, service_2, *list(other_components), provider, self.host_2]

    def _execute_test(
        self, owner: ADCM_OBJECT, target: ADCM_OBJECT, call_arguments: str | dict, expect_fail: bool = False
    ) -> None:
        old_state = target.state

        task = self.prepare_task(owner=owner, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMStatePluginExecutor,
            call_arguments=call_arguments,
            call_context=job,
        )
        result = executor.execute()

        if expect_fail:
            target_state = old_state
            self.assertIsNotNone(result.error)
            self.assertFalse(result.changed)
        else:
            target_state = self.new_state
            self.assertIsNone(result.error)
            self.assertTrue(result.changed)

        target.refresh_from_db()
        self.assertEqual(target.state, target_state)

    def _check_control_group(self):
        states = set()
        for object_ in self.control_objects:
            object_.refresh_from_db()
            states.add(object_.state)

        self.assertEqual(states, {"created"})

    def test_states(self):
        for owner, target, call_args in (
            (self.cluster, self.cluster, {"type": "cluster", "state": self.new_state}),
            (
                self.cluster,
                self.service,
                {"type": "service", "service_name": self.service.name, "state": self.new_state},
            ),
            (
                self.cluster,
                self.component,
                {
                    "type": "component",
                    "service_name": self.service.name,
                    "component_name": self.component.name,
                    "state": self.new_state,
                },
            ),
            (self.service, self.cluster, {"type": "cluster", "state": self.new_state}),
            (self.service, self.service, {"type": "service", "state": self.new_state}),
            (
                self.service,
                self.component,
                {"type": "component", "component_name": self.component.name, "state": self.new_state},
            ),
            (self.component, self.cluster, {"type": "cluster", "state": self.new_state}),
            (self.component, self.service, {"type": "service", "state": self.new_state}),
            (self.component, self.component, {"type": "component", "state": self.new_state}),
            (self.provider, self.provider, {"type": "provider", "state": self.new_state}),
            (self.provider, self.host_1, {"type": "host", "host_id": self.host_1.pk, "state": self.new_state}),
            (self.host_1, self.provider, {"type": "provider", "state": self.new_state}),
            (self.host_1, self.host_1, {"type": "host", "state": self.new_state}),
        ):
            with self.subTest(owner=owner, target=target, call_args=call_args):
                self._execute_test(owner=owner, target=target, call_arguments=call_args)
                self._check_control_group()

    def test_forbidden_owner_targert_pairs(self):
        for owner, target, call_args in (
            (self.host_1, self.host_2, {"type": "host", "host_id": self.host_2.pk, "state": self.new_state}),
        ):
            with self.subTest(owner=owner, target=target, call_args=call_args):
                self._execute_test(owner=owner, target=target, call_arguments=call_args, expect_fail=True)
