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
import random

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from core.types import ADCMCoreType, CoreObjectDescriptor

from cm.converters import orm_object_to_core_type
from cm.issue import create_lock
from cm.models import (
    ADCM,
    Cluster,
    Component,
    ConcernCause,
    ConcernItem,
    ConcernType,
    Host,
    HostProvider,
    JobLog,
    Service,
    TaskLog,
)
from cm.services.concern import create_issue
from cm.services.concern.flags import BuiltInFlag, ConcernFlag, lower_all_flags, lower_flag, raise_flag


class TestFlag(BaseTestCase, BusinessLogicMixin):
    def setUp(self) -> None:
        super().setUp()

        self.change_configuration(
            target=ADCM.objects.get(), config_diff={"global": {"adcm_url": "http://localhost:8080"}}
        )

        bundles_dir = Path(__file__).parent / "bundles"
        cluster_bundle = self.add_bundle(bundles_dir / "cluster_1")
        provider_bundle = self.add_bundle(bundles_dir / "provider")

        clusters = [self.add_cluster(bundle=cluster_bundle, name=f"Cluster {i}") for i in range(3)]
        providers = [self.add_provider(bundle=provider_bundle, name=f"Provider {i}") for i in range(3)]

        for cluster in clusters:
            self.add_services_to_cluster(["service_two_components", "another_service_two_components"], cluster=cluster)

        for provider in providers:
            for i in range(4):
                self.add_host(bundle=provider.prototype.bundle, provider=provider, fqdn=f"{provider.name}-host-{i}")

    def test_raise_lower_flag_on_one_object_success(self) -> None:
        expected_name = BuiltInFlag.ADCM_OUTDATED_CONFIG.value.name
        expected_message = "${source} has a flag: " + BuiltInFlag.ADCM_OUTDATED_CONFIG.value.message

        for object_model in (Cluster, Service, Component, HostProvider, Host):
            target = object_model.objects.all()[1]
            self.assertEqual(ConcernItem.objects.count(), 0)

            on_objects = [CoreObjectDescriptor(id=target.id, type=orm_object_to_core_type(target))]

            raise_flag(flag=BuiltInFlag.ADCM_OUTDATED_CONFIG.value, on_objects=on_objects)
            self.assertEqual(ConcernItem.objects.count(), 1)

            concern = ConcernItem.objects.get()
            self.assertEqual(concern.type, ConcernType.FLAG)
            self.assertEqual(concern.owner, target)
            self.assertEqual(concern.name, expected_name)
            self.assertEqual(concern.reason["message"], expected_message)
            self.assertFalse(concern.blocking)
            self.assertEqual(concern.cause, ConcernCause.CONFIG)

            lower_flag(name=BuiltInFlag.ADCM_OUTDATED_CONFIG.value.name, on_objects=on_objects)
            self.assertEqual(ConcernItem.objects.count(), 0)

    def test_raise_lower_flag_on_many_objects_success(self) -> None:
        flag = ConcernFlag(name="custom_name", message="hi, I'm glad to see you {", cause=None)
        expected_name = flag.name
        expected_message = "${source} has a flag: " + flag.message

        clusters = random.sample(tuple(Cluster.objects.all()), k=1)
        services = random.sample(tuple(Service.objects.all()), k=2)
        components = random.sample(tuple(Component.objects.all()), k=3)
        providers = random.sample(tuple(HostProvider.objects.all()), k=2)
        hosts = random.sample(tuple(Host.objects.all()), k=1)

        targets = (*clusters, *services, *components, *providers, *hosts)
        self.assertEqual(ConcernItem.objects.count(), 0)

        on_objects = [CoreObjectDescriptor(id=target.id, type=orm_object_to_core_type(target)) for target in targets]

        raise_flag(flag=flag, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 9)

        for concern in ConcernItem.objects.all():
            self.assertEqual(concern.type, ConcernType.FLAG)
            self.assertEqual(concern.name, expected_name)
            self.assertEqual(concern.reason["message"], expected_message)
            self.assertFalse(concern.blocking)
            self.assertEqual(concern.cause, None)

        for target in targets:
            concern = ConcernItem.objects.get(owner_id=target.id, owner_type=target.content_type)
            self.assertEqual(concern.owner, target)
            self.assertEqual(
                concern.reason["placeholder"],
                {
                    "source": {
                        "type": target.prototype.type,
                        "name": target.display_name,
                        "params": target.get_id_chain(),
                    }
                },
            )

        lower_flag(name=flag.name, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 0)

    def test_raise_on_objects_some_has_flags_success(self) -> None:
        flag_1 = ConcernFlag(name="awesome name", message="hi, I'm glad to see you ()}", cause=None)
        flag_2 = BuiltInFlag.ADCM_OUTDATED_CONFIG.value

        clusters = cluster_1, cluster_2 = random.sample(tuple(Cluster.objects.all()), k=2)
        services = service_1, service_2 = random.sample(tuple(Service.objects.all()), k=2)
        components = component_1, component_2 = random.sample(tuple(Component.objects.all()), k=2)
        providers = provider_1, provider_2 = random.sample(tuple(HostProvider.objects.all()), k=2)
        hosts = host_1, host_2 = random.sample(tuple(Host.objects.all()), k=2)

        self.assertEqual(ConcernItem.objects.count(), 0)
        targets = (cluster_1, service_1, service_2, component_2, provider_1, host_1)
        on_objects = [CoreObjectDescriptor(id=target.id, type=orm_object_to_core_type(target)) for target in targets]

        raise_flag(flag=flag_1, on_objects=on_objects)

        self.assertEqual(ConcernItem.objects.count(), 6)

        raise_flag(flag=flag_2, on_objects=on_objects)

        self.assertEqual(ConcernItem.objects.count(), 12)
        self.assertEqual(ConcernItem.objects.filter(name=flag_1.name).count(), 6)
        self.assertEqual(ConcernItem.objects.filter(name=flag_2.name).count(), 6)
        component_2_concern_names = ConcernItem.objects.values_list("name", flat=True).filter(
            owner_id=component_2.id, owner_type=component_2.content_type
        )
        self.assertListEqual(sorted((flag_1.name, flag_2.name)), sorted(component_2_concern_names))

        targets = (*clusters, *services, *components, *providers, *hosts)
        on_objects = [CoreObjectDescriptor(id=target.id, type=orm_object_to_core_type(target)) for target in targets]

        raise_flag(flag=flag_1, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 16)
        self.assertEqual(ConcernItem.objects.filter(name=flag_1.name).count(), 10)
        self.assertEqual(ConcernItem.objects.filter(name=flag_2.name).count(), 6)

    def test_lower_flag_does_not_interfere_with_other_concerns_success(self) -> None:
        clusters = cluster_1, cluster_2 = random.sample(tuple(Cluster.objects.all()), k=2)
        components = component_1, component_2 = random.sample(tuple(Component.objects.all()), k=2)
        hosts = host_1, host_2 = random.sample(tuple(Host.objects.all()), k=2)

        dummy_job = JobLog(name="cool", task=TaskLog(id=10))
        for object_ in (*clusters, *components, *hosts):
            create_issue(
                owner=CoreObjectDescriptor(id=object_.id, type=orm_object_to_core_type(object_)),
                cause=ConcernCause.CONFIG,
            )
            create_lock(owner=object_, job=dummy_job)
        self.assertEqual(ConcernItem.objects.count(), 12)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG).count(), 0)

        issue_like_flag = ConcernFlag(
            name=ConcernItem.objects.filter(type=ConcernType.ISSUE).first().name, message="imitate issue", cause=None
        )
        lock_like_flag = ConcernFlag(
            name=ConcernItem.objects.filter(type=ConcernType.LOCK).first().name, message="imitate lock", cause=None
        )

        targets = (*clusters, *components, *hosts)
        on_objects = [CoreObjectDescriptor(id=target.id, type=orm_object_to_core_type(target)) for target in targets]

        lower_flag(name=issue_like_flag.name, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 12)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG).count(), 0)

        lower_flag(name=lock_like_flag.name, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 12)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG).count(), 0)

        lower_all_flags(on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 12)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG).count(), 0)

        targets = (cluster_1, component_2, host_1)
        on_objects = [CoreObjectDescriptor(id=target.id, type=orm_object_to_core_type(target)) for target in targets]

        raise_flag(flag=issue_like_flag, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 15)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG).count(), 3)

        raise_flag(flag=lock_like_flag, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 18)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG, name=issue_like_flag.name).count(), 3)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG, name=lock_like_flag.name).count(), 3)

        targets = (cluster_1, host_1)
        on_objects = [CoreObjectDescriptor(id=target.id, type=orm_object_to_core_type(target)) for target in targets]

        lower_flag(name=issue_like_flag.name, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 16)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG, name=issue_like_flag.name).count(), 1)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG, name=lock_like_flag.name).count(), 3)

        lower_flag(name=lock_like_flag.name, on_objects=on_objects)
        self.assertEqual(ConcernItem.objects.count(), 14)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG, name=issue_like_flag.name).count(), 1)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG, name=lock_like_flag.name).count(), 1)

        lower_all_flags(on_objects=[CoreObjectDescriptor(id=component_2.id, type=ADCMCoreType.COMPONENT)])
        self.assertEqual(ConcernItem.objects.count(), 12)
        self.assertEqual(ConcernItem.objects.filter(type=ConcernType.FLAG).count(), 0)
