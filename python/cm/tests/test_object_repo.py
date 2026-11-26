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

from typing import Final, Literal

from core.object.types import Selector, SelectorOwnerDescriptor, SelectorTargetDescriptor
from core.types import ADCMCoreType, ADCMHostGroupType, CoreObjectDescriptor, Descriptor
from tests.base import BaseTestCase
from unittest_parametrize import ParametrizedTestCase, param, parametrize

from cm.impl.object.repo import ObjectRepo
from cm.models import ActionHostGroup, ADCMEntity, Cluster, Component, ContentType, Host, Provider, Service
from cm.tests.utils import gen_adcm, generate_hierarchy

OBJECT_TYPE_PARAMS: Final = [param(object_type, id=object_type.value) for object_type in ADCMCoreType]


class TestObjectRepo(ParametrizedTestCase, BaseTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        hierarchy = generate_hierarchy()
        adcm = gen_adcm()

        cls.repo = ObjectRepo()
        cls.orm_objects: dict[ADCMCoreType, ADCMEntity] = {
            ADCMCoreType.ADCM: adcm,
            ADCMCoreType.CLUSTER: hierarchy["cluster"],
            ADCMCoreType.SERVICE: hierarchy["service"],
            ADCMCoreType.COMPONENT: hierarchy["component"],
            ADCMCoreType.PROVIDER: hierarchy["provider"],
            ADCMCoreType.HOST: hierarchy["host"],
        }

    def get_object(self, object_type: ADCMCoreType) -> tuple[Descriptor[ADCMCoreType], ADCMEntity]:
        orm_object = self.orm_objects[object_type]
        return Descriptor(id=orm_object.id, type=object_type), orm_object

    @parametrize("object_type", OBJECT_TYPE_PARAMS)
    def test_set_state(self, object_type: ADCMCoreType) -> None:
        object_, orm_object = self.get_object(object_type)

        self.repo.set_state(object_=object_, state="installed")
        orm_object.refresh_from_db()
        self.assertEqual(orm_object.state, "installed")

    @parametrize("object_type", OBJECT_TYPE_PARAMS)
    def test_update_multi_state_add(self, object_type: ADCMCoreType) -> None:
        object_, orm_object = self.get_object(object_type)

        self.assertEqual(
            self.repo.update_multi_state(object_=object_, add=["flag_a", "flag_b"], remove=()),
            ["flag_a", "flag_b"],
        )

        orm_object.refresh_from_db()
        self.assertEqual(orm_object.multi_state, ["flag_a", "flag_b"])

    @parametrize("object_type", OBJECT_TYPE_PARAMS)
    def test_update_multi_state_remove(self, object_type: ADCMCoreType) -> None:
        object_, orm_object = self.get_object(object_type)

        self.repo.update_multi_state(object_=object_, add=["flag_a", "flag_b"], remove=())
        self.assertEqual(
            self.repo.update_multi_state(object_=object_, add=(), remove=["flag_a"]),
            ["flag_b"],
        )

        orm_object.refresh_from_db()
        self.assertEqual(orm_object.multi_state, ["flag_b"])

    @parametrize("object_type", OBJECT_TYPE_PARAMS)
    def test_update_multi_state_add_and_remove_in_one_call(self, object_type: ADCMCoreType) -> None:
        object_, orm_object = self.get_object(object_type)

        self.repo.update_multi_state(object_=object_, add=["flag_a"], remove=())
        self.assertEqual(
            self.repo.update_multi_state(object_=object_, add=["flag_b"], remove=["flag_a"]),
            ["flag_b"],
        )

        orm_object.refresh_from_db()
        self.assertEqual(orm_object.multi_state, ["flag_b"])

    @parametrize("object_type", OBJECT_TYPE_PARAMS)
    def test_update_multi_state_empty_is_noop(self, object_type: ADCMCoreType) -> None:
        object_, orm_object = self.get_object(object_type)

        self.assertEqual(self.repo.update_multi_state(object_=object_, add=(), remove=()), [])

        orm_object.refresh_from_db()
        self.assertEqual(orm_object.multi_state, [])

    @parametrize("object_type", OBJECT_TYPE_PARAMS)
    def test_update_multi_state_returns_whole_multi_state(self, object_type: ADCMCoreType) -> None:
        object_, _ = self.get_object(object_type)

        self.assertEqual(self.repo.update_multi_state(object_=object_, add=["flag_a"], remove=()), ["flag_a"])
        self.assertEqual(
            self.repo.update_multi_state(object_=object_, add=["flag_b"], remove=()),
            ["flag_a", "flag_b"],
        )
        self.assertEqual(
            self.repo.update_multi_state(object_=object_, add=(), remove=["flag_a"]),
            ["flag_b"],
        )

    @parametrize("object_type", OBJECT_TYPE_PARAMS)
    def test_retrieve_multi_state(self, object_type: ADCMCoreType) -> None:
        object_, _ = self.get_object(object_type)

        self.assertEqual(self.repo.retrieve_multi_state(object_=object_), [])
        self.repo.update_multi_state(object_=object_, add=["flag_b", "flag_a"], remove=())
        self.assertEqual(self.repo.retrieve_multi_state(object_=object_), ["flag_a", "flag_b"])


class TestObjectRepoBuildSelector(BaseTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.hierarchy = generate_hierarchy()
        cls.repo = ObjectRepo()

        cls.cluster: Cluster = cls.hierarchy["cluster"]
        cls.service: Service = cls.hierarchy["service"]
        cls.component: Component = cls.hierarchy["component"]
        cls.provider: Provider = cls.hierarchy["provider"]
        cls.host: Host = cls.hierarchy["host"]

        cls.adcm = gen_adcm()
        cls.action_host_group = ActionHostGroup.objects.create(
            object_id=cls.cluster.id,
            object_type=ContentType.objects.get_for_model(Cluster),
            name="action group",
            description="",
        )

    def target(self, orm_object: ADCMEntity, core_type: ADCMCoreType) -> CoreObjectDescriptor:
        return CoreObjectDescriptor(id=orm_object.id, type=core_type)

    def owner(self, orm_object: ADCMEntity, core_type: ADCMCoreType) -> CoreObjectDescriptor:
        return CoreObjectDescriptor(id=orm_object.id, type=core_type)

    def select_one(self, target: SelectorTargetDescriptor, owner: SelectorOwnerDescriptor | None = None) -> Selector:
        return self.repo.build_selector(targets=(target,), owner=owner)[target]

    def test_cluster_selector(self) -> None:
        selector = self.select_one(self.target(self.cluster, ADCMCoreType.CLUSTER))

        self.assertEqual(
            selector,
            {ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name}},
        )

    def test_service_selector(self) -> None:
        selector = self.select_one(self.target(self.service, ADCMCoreType.SERVICE))

        self.assertEqual(
            selector,
            {
                ADCMCoreType.SERVICE.value: {"id": self.service.id, "name": self.service.display_name},
                ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name},
            },
        )

    def test_component_selector(self) -> None:
        selector = self.select_one(self.target(self.component, ADCMCoreType.COMPONENT))

        self.assertEqual(
            selector,
            {
                ADCMCoreType.COMPONENT.value: {"id": self.component.id, "name": self.component.display_name},
                ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name},
                ADCMCoreType.SERVICE.value: {"id": self.service.id, "name": self.service.display_name},
            },
        )

    def test_provider_selector(self) -> None:
        selector = self.select_one(self.target(self.provider, ADCMCoreType.PROVIDER))

        self.assertEqual(
            selector,
            {ADCMCoreType.PROVIDER.value: {"id": self.provider.id, "name": self.provider.name}},
        )

    def test_host_selector_with_default_owner(self) -> None:
        selector = self.select_one(self.target(self.host, ADCMCoreType.HOST))

        self.assertEqual(
            selector,
            {
                ADCMCoreType.HOST.value: {"id": self.host.id, "name": self.host.fqdn},
                ADCMCoreType.PROVIDER.value: {"id": self.provider.id, "name": self.provider.name},
            },
        )

    def test_host_selector_with_component_owner(self) -> None:
        selector = self.select_one(
            self.target(self.host, ADCMCoreType.HOST),
            owner=self.owner(self.component, ADCMCoreType.COMPONENT),
        )

        self.assertEqual(
            selector,
            {
                ADCMCoreType.HOST.value: {"id": self.host.id, "name": self.host.fqdn},
                ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name},
                ADCMCoreType.SERVICE.value: {"id": self.service.id, "name": self.service.display_name},
                ADCMCoreType.COMPONENT.value: {"id": self.component.id, "name": self.component.display_name},
            },
        )

    def test_adcm_selector(self) -> None:
        selector = self.select_one(CoreObjectDescriptor(id=self.adcm.id, type=ADCMCoreType.ADCM))

        self.assertEqual(
            selector,
            {ADCMCoreType.ADCM.value: {"id": self.adcm.id, "name": "adcm"}},
        )

    def test_action_host_group_selector(self) -> None:
        action_group_target: Descriptor[Literal[ADCMHostGroupType.ACTION]] = Descriptor(
            id=self.action_host_group.id, type=ADCMHostGroupType.ACTION
        )

        selector = self.select_one(
            target=action_group_target,
            owner=CoreObjectDescriptor(id=self.cluster.id, type=ADCMCoreType.CLUSTER),
        )

        self.assertEqual(
            selector,
            {
                "action_host_group": {"id": self.action_host_group.id, "name": self.action_host_group.name},
                ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name},
            },
        )

    def test_multiple_selectors(self) -> None:
        targets = [
            self.target(self.cluster, ADCMCoreType.CLUSTER),
            self.target(self.service, ADCMCoreType.SERVICE),
            self.target(self.component, ADCMCoreType.COMPONENT),
            self.target(self.provider, ADCMCoreType.PROVIDER),
            self.target(self.host, ADCMCoreType.HOST),
        ]

        expected_selectors = {
            targets[0]: {ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name}},
            targets[1]: {
                ADCMCoreType.SERVICE.value: {"id": self.service.id, "name": self.service.display_name},
                ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name},
            },
            targets[2]: {
                ADCMCoreType.COMPONENT.value: {"id": self.component.id, "name": self.component.display_name},
                ADCMCoreType.CLUSTER.value: {"id": self.cluster.id, "name": self.cluster.name},
                ADCMCoreType.SERVICE.value: {"id": self.service.id, "name": self.service.display_name},
            },
            targets[3]: {ADCMCoreType.PROVIDER.value: {"id": self.provider.id, "name": self.provider.name}},
            targets[4]: {
                ADCMCoreType.HOST.value: {"id": self.host.id, "name": self.host.fqdn},
                ADCMCoreType.PROVIDER.value: {"id": self.provider.id, "name": self.provider.name},
            },
        }

        selectors = self.repo.build_selector(targets=targets)

        self.assertDictEqual(selectors, expected_selectors)
