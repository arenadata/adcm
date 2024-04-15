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

from pathlib import Path

from adcm.tests.ansible import ADCMAnsiblePluginTestMixin, DummyExecutor
from adcm.tests.base import BaseTestCase, BusinessLogicMixin, TaskTestMixin
from cm.models import ClusterObject, ServiceComponent
from cm.services.job.run.repo import JobRepoImpl
from core.job.types import Task
from core.types import ADCMCoreType, CoreObjectDescriptor
from pydantic import BaseModel

from ansible_plugin.base import ArgumentsConfig, PluginExecutorConfig, TargetConfig, from_objects


class EmptyArguments(BaseModel):
    ...


class TestObjectsTargetsExtraction(BaseTestCase, BusinessLogicMixin, ADCMAnsiblePluginTestMixin, TaskTestMixin):
    def setUp(self):
        super().setUp()

        self.targets_from_objects_executor = DummyExecutor(
            config=PluginExecutorConfig(
                arguments=ArgumentsConfig(represent_as=EmptyArguments),
                target=TargetConfig(detectors=(from_objects,)),
            )
        )

        self.bundles_dir = Path(__file__).parent / "bundles"

        cluster_bundle = self.add_bundle(self.bundles_dir / "cluster")
        provider_bundle = self.add_bundle(self.bundles_dir / "provider")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="Cluster 1")
        self.cluster_2 = self.add_cluster(bundle=cluster_bundle, name="Cluster 2")

        for cluster in (self.cluster_1, self.cluster_2):
            self.add_services_to_cluster(["service_1", "service_2"], cluster=cluster)

        self.provider_1 = self.add_provider(bundle=provider_bundle, name="Provider 1")
        self.provider_2 = self.add_provider(bundle=provider_bundle, name="Provider 2")

        self.host_1 = self.add_host(provider=self.provider_1, fqdn="provider-1-host-1")
        self.host_2 = self.add_host(provider=self.provider_1, fqdn="provider-1-host-2")
        self.host_3 = self.add_host(provider=self.provider_2, fqdn="provider-2-host-1")
        self.host_4 = self.add_host(provider=self.provider_2, fqdn="provider-2-host-2")

    def test_full_info_objects_of_cluster_context_success(self) -> None:
        arguments = """
            objects:
              - type: service
                service_name: service_2
              - type: cluster
              - type: component
                service_name: service_1
                component_name: component_2
        """

        expected_cluster = self.cluster_1
        expected_service = ClusterObject.objects.get(prototype__name="service_2", cluster=self.cluster_1)
        expected_component = ServiceComponent.objects.get(
            prototype__name="component_2", service__prototype__name="service_1", cluster=self.cluster_1
        )

        another_service = ClusterObject.objects.get(prototype__name="service_1", cluster=self.cluster_1)
        another_component = ServiceComponent.objects.get(
            prototype__name="component_2", service__prototype__name="service_1", cluster=self.cluster_1
        )

        for action_owner in (expected_cluster, another_service, another_component):
            with self.subTest(f"Action context from {action_owner.__class__.__name__}"):
                self.check_target_detection(
                    arguments=arguments,
                    task=self.prepare_task(owner=action_owner, name="dummy"),
                    expected_targets=[
                        CoreObjectDescriptor(id=expected_service.id, type=ADCMCoreType.SERVICE),
                        CoreObjectDescriptor(id=expected_cluster.id, type=ADCMCoreType.CLUSTER),
                        CoreObjectDescriptor(id=expected_component.id, type=ADCMCoreType.COMPONENT),
                    ],
                )

    def test_service_context_success(self) -> None:
        arguments = {
            "objects": [
                {"type": "service"},
                # another service
                {"type": "service", "service_name": "service_1"},
                {"type": "cluster"},
                # component of this service
                {"type": "component", "component_name": "component_1"},
                # component of another service
                {"type": "component", "service_name": "service_1", "component_name": "component_1"},
                # this service, but by name
                {"type": "service", "service_name": "service_2"},
            ]
        }

        parent_cluster = self.cluster_2
        context_service = ClusterObject.objects.get(prototype__name="service_2", cluster=parent_cluster)
        another_service = ClusterObject.objects.get(prototype__name="service_1", cluster=parent_cluster)
        child_component = ServiceComponent.objects.get(service=context_service, prototype__name="component_1")
        another_service_component = ServiceComponent.objects.get(service=another_service, prototype__name="component_1")

        self.check_target_detection(
            arguments=arguments,
            task=self.prepare_task(owner=context_service, name="dummy"),
            expected_targets=[
                CoreObjectDescriptor(id=context_service.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=another_service.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=parent_cluster.id, type=ADCMCoreType.CLUSTER),
                CoreObjectDescriptor(id=child_component.id, type=ADCMCoreType.COMPONENT),
                CoreObjectDescriptor(id=another_service_component.id, type=ADCMCoreType.COMPONENT),
                CoreObjectDescriptor(id=context_service.id, type=ADCMCoreType.SERVICE),
            ],
        )

    def test_component_context_success(self) -> None:
        arguments = {
            "objects": [
                # parent service
                {"type": "service"},
                # another service
                {"type": "service", "service_name": "service_1"},
                {"type": "cluster"},
                # this component
                {"type": "component", "component_name": "component_1"},
                # component of another service
                {"type": "component", "service_name": "service_1", "component_name": "component_1"},
                # parent service, but by name
                {"type": "service", "service_name": "service_2"},
                # this component
                {"type": "component"},
                # another component of this service
                {"type": "component", "component_name": "component_2"},
            ]
        }

        parent_cluster = self.cluster_2
        context_service = ClusterObject.objects.get(prototype__name="service_2", cluster=parent_cluster)
        another_service = ClusterObject.objects.get(prototype__name="service_1", cluster=parent_cluster)
        context_component = ServiceComponent.objects.get(service=context_service, prototype__name="component_1")
        another_component_of_same_service = ServiceComponent.objects.get(
            service=context_service, prototype__name="component_2"
        )
        another_service_component = ServiceComponent.objects.get(service=another_service, prototype__name="component_1")

        self.check_target_detection(
            arguments=arguments,
            task=self.prepare_task(owner=context_component, name="dummy"),
            expected_targets=[
                CoreObjectDescriptor(id=context_service.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=another_service.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=parent_cluster.id, type=ADCMCoreType.CLUSTER),
                CoreObjectDescriptor(id=context_component.id, type=ADCMCoreType.COMPONENT),
                CoreObjectDescriptor(id=another_service_component.id, type=ADCMCoreType.COMPONENT),
                CoreObjectDescriptor(id=context_service.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=context_component.id, type=ADCMCoreType.COMPONENT),
                CoreObjectDescriptor(id=another_component_of_same_service.id, type=ADCMCoreType.COMPONENT),
            ],
        )

    def test_host_context_success(self) -> None:
        arguments = """
            objects:
              - type: "host"
              - type: "provider"
        """

        host = self.host_3
        provider = host.provider

        self.check_target_detection(
            arguments=arguments,
            task=self.prepare_task(owner=host, name="dummy"),
            expected_targets=[
                CoreObjectDescriptor(id=host.id, type=ADCMCoreType.HOST),
                CoreObjectDescriptor(id=provider.id, type=ADCMCoreType.HOSTPROVIDER),
            ],
        )

    def test_component_host_action_context_success(self):
        arguments = {"objects": [{"type": "service"}, {"type": "cluster"}, {"type": "component"}, {"type": "host"}]}

        host = self.host_2
        parent_cluster = self.cluster_1
        component = ServiceComponent.objects.filter(cluster=parent_cluster).first()

        self.add_host_to_cluster(cluster_pk=parent_cluster.pk, host_pk=host.pk)
        self.set_hostcomponent(cluster=parent_cluster, entries=[(host, component)])

        self.check_target_detection(
            arguments=arguments,
            task=self.prepare_task(owner=component, host=host, name="on_host"),
            expected_targets=[
                CoreObjectDescriptor(id=component.service.id, type=ADCMCoreType.SERVICE),
                CoreObjectDescriptor(id=parent_cluster.id, type=ADCMCoreType.CLUSTER),
                CoreObjectDescriptor(id=component.id, type=ADCMCoreType.COMPONENT),
                CoreObjectDescriptor(id=host.id, type=ADCMCoreType.HOST),
            ],
        )

    def check_target_detection(
        self, task: Task, arguments: dict | str, expected_targets: list[CoreObjectDescriptor]
    ) -> None:
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=self.targets_from_objects_executor, call_arguments=arguments, call_context=job
        )

        result = executor.execute()
        self.assertIsNone(result.error, result.error.message if result.error else "")

        self.assertListEqual(
            list(result.value.targets),
            expected_targets,
        )
