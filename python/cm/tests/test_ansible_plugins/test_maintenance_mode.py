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

from itertools import chain, product
from pathlib import Path

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from ansible_plugin.maintenance_mode import TYPE_CLASS_MAP, get_object, validate_args, validate_obj

from cm.models import MaintenanceMode


class TestMaintenanceModePlugin(BusinessLogicMixin, BaseTestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")
        bundles_dir = Path(__file__).parent.parent / "bundles"

        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")
        self.cluster = self.add_cluster(bundle=cluster_bundle, name="test_cluster")
        self.service = self.add_services_to_cluster(service_names=["service_one_component"], cluster=self.cluster).get()
        self.component = self.service.servicecomponent_set.get(prototype__name="component_1")

        provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")
        provider = self.add_provider(bundle=provider_bundle, name="test_provider")
        self.host = self.add_host(bundle=provider_bundle, provider=provider, fqdn="test_host", cluster=self.cluster)
        self.set_hostcomponent(cluster=self.cluster, entries=[(self.host, self.component)])

    def _set_objects_mm(
        self,
        host: MaintenanceMode = MaintenanceMode.OFF,
        service: MaintenanceMode = MaintenanceMode.OFF,
        component: MaintenanceMode = MaintenanceMode.OFF,
    ) -> None:
        for obj, mm_value in zip((self.host, self.service, self.component), (host, service, component)):
            obj.maintenance_mode = mm_value
            obj.save()

    def test_task_args_validation(self):
        correct_types = tuple(TYPE_CLASS_MAP.keys())
        correct_values = (True, False)
        wrong_types = ("cluster", "provider", "some_string", 1.3, None)
        wrong_values = (8, None, [])

        for assert_func, type_value_pairs in (
            (self.assertIsNone, product(correct_types, correct_values)),
            (
                self.assertIsNotNone,
                chain(
                    product(wrong_types, wrong_values),
                    product(wrong_types, correct_values),
                    product(correct_types, wrong_values),
                ),
            ),
        ):
            for type_, value_ in type_value_pairs:
                args = {"type": type_, "value": value_}
                with self.subTest(args):
                    error = validate_args(task_args=args)
                    assert_func(error)

    def test_object_validation(self):
        correct_values = (MaintenanceMode.CHANGING,)
        wrong_values = (MaintenanceMode.ON, MaintenanceMode.OFF)
        object_type_pairs = ((self.host, "host"), (self.service, "service"), (self.component, "component"))

        for assert_func, mm_states in ((self.assertIsNone, correct_values), (self.assertIsNotNone, wrong_values)):
            for mm_state, object_type_pair in product(mm_states, object_type_pairs):
                object_, type_ = object_type_pair
                self._set_objects_mm(**{type_: mm_state})
                with self.subTest(f"{object_.__class__.__name__} with mm `{object_.maintenance_mode}`"):
                    error = validate_obj(obj=object_)
                    assert_func(error)

    def test_object_getting(self):
        test_data = {
            "host": {
                "context": {
                    "type": "cluster",
                    "host_id": self.host.pk,
                }
            },
            "service": {
                "context": {
                    "type": "service",
                    "service_id": self.service.pk,
                }
            },
            "component": {
                "context": {
                    "type": "component",
                    "component_id": self.component.pk,
                }
            },
        }
        for type_, task_vars in test_data.items():
            with self.subTest(type_):
                object_, error = get_object(task_vars=task_vars, obj_type=type_)
                self.assertIsNotNone(object_)
                self.assertIsInstance(object_, TYPE_CLASS_MAP[type_])
                self.assertIsNone(error)
