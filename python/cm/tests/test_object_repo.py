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

from typing import Final

from core.types import ADCMCoreType, Descriptor
from tests.base import BaseTestCase
from unittest_parametrize import ParametrizedTestCase, param, parametrize

from cm.impl.object.repo import ObjectRepo
from cm.models import ADCMEntity
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
