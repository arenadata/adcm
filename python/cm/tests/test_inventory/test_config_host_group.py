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

from api_v2.service.utils import bulk_add_services_to_cluster
from core.types import CoreObjectDescriptor

from cm.converters import model_name_to_core_type
from cm.models import (
    Action,
    Component,
    ObjectType,
    Prototype,
)
from cm.services.job.inventory import get_inventory_data
from cm.tests.test_inventory.base import BaseInventoryTestCase, decrypt_secrets


class TestCHGsInInventory(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(source_dir=self.bundles_dir / "cluster_config_host_group"), name="Target Cluster"
        )

        self.provider = self.add_provider(
            bundle=self.add_bundle(source_dir=self.bundles_dir / "provider"), name="provider"
        )
        self.host_1 = self.add_host(
            bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster
        )
        self.host_2 = self.add_host(
            bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster
        )
        self.host_3 = self.add_host(
            bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host_3", cluster=self.cluster
        )

        self.service_not_simple, self.service_thesame = bulk_add_services_to_cluster(
            cluster=self.cluster,
            prototypes=Prototype.objects.filter(type=ObjectType.SERVICE, name__in=["not_simple", "thesame"]),
        )
        self.component_not_simple = Component.objects.get(
            service=self.service_not_simple, prototype__name="not_simple_component"
        )
        self.component_another_not_simple = Component.objects.get(
            service=self.service_not_simple, prototype__name="another_not_simple_component"
        )
        self.component_thesame = Component.objects.get(
            service=self.service_thesame, prototype__name="thesame_component"
        )
        self.component_another_thesame = Component.objects.get(
            service=self.service_thesame, prototype__name="another_thesame_component"
        )

    def test_config_host_group_in_inventory(self) -> None:
        self.set_hostcomponent(
            cluster=self.cluster,
            entries=(
                (self.host_1, self.component_not_simple),
                (self.host_1, self.component_another_not_simple),
                (self.host_1, self.component_thesame),
                (self.host_1, self.component_another_thesame),
                (self.host_2, self.component_not_simple),
                (self.host_2, self.component_another_not_simple),
                (self.host_3, self.component_not_simple),
                (self.host_3, self.component_thesame),
            ),
        )

        host_names = [self.host_1.name, self.host_2.name, self.host_3.name]
        expected_topology = {
            "CLUSTER": host_names,
            self.service_not_simple.name: host_names,
            f"{self.service_not_simple.name}.{self.component_another_not_simple.name}": [host_names[0], host_names[1]],
            f"{self.service_not_simple.name}.{self.component_not_simple.name}": host_names,
            self.service_thesame.name: [host_names[0], host_names[2]],
            f"{self.service_thesame.name}.{self.component_thesame.name}": [host_names[0], host_names[2]],
            f"{self.service_thesame.name}.{self.component_another_thesame.name}": [host_names[0]],
        }

        context = {
            **{
                obj_.name: obj_
                for obj_ in (
                    self.service_thesame,
                    self.service_not_simple,
                    self.component_thesame,
                    self.component_another_thesame,
                    self.component_not_simple,
                    self.component_another_not_simple,
                )
            },
            "filedir": self.directories["FILE_DIR"],
        }
        expected_parts = {
            file.stem.replace(".json", ""): self.render_json_template(file=file, context=context)
            for file in (self.templates_dir / "config_host_group").iterdir()
        }

        cluster_group = self.add_config_host_group(parent=self.cluster, hosts=(self.host_1, self.host_3))
        service_group = self.add_config_host_group(parent=self.service_thesame, hosts=(self.host_1,))
        component_group_1 = self.add_config_host_group(parent=self.component_another_thesame, hosts=(self.host_2,))
        self.add_config_host_group(parent=self.component_thesame, hosts=(self.host_1, self.host_3))

        self.change_configuration(
            target=cluster_group,
            config_diff={
                "plain_group": {"listofstuff": ["hello"]},
                "just_bool": True,
                "secrettext": "imsecrett\nextforu\n",
                "variant_inline": "f",
                "variant_config": "1",
                "variant_builtin": self.host_1.name,
            },
            meta_diff={
                key: {"isSynchronized": False}
                for key in (
                    "/plain_group/listofstuff",
                    "/just_bool",
                    "/secrettext",
                    "/variant_inline",
                    "/variant_config",
                    "/variant_builtin",
                )
            },
        )

        self.change_configuration(
            target=self.service_thesame,
            config_diff={
                "activatable_group": {"simple": "bestgroupever"},
                "list_of_dicts": [{"integer": 400, "string": "woo"}],
            },
            meta_diff={"/activatable_group": {"isActive": True}},
        )
        self.change_configuration(
            target=service_group,
            config_diff={"list_of_dicts": [], "just_map": {"key": "val"}},
            meta_diff={
                "/activatable_group": {"isActive": False, "isSynchronized": False},
                "/just_map": {"isSynchronized": False},
                "/list_of_dicts": {"isSynchronized": False},
            },
            # because `just_map` is None and it'll fail `deep_merge`
            preprocess_config=lambda d: {**d, "just_map": {}},
        )

        self.change_configuration(
            target=component_group_1,
            config_diff={"plain_group": {"secretmap": {"donot": "know", "m": "e"}}},
            meta_diff={
                "/activatable_group": {"isActive": True, "isSynchronized": False},
                "/plain_group/secretmap": {"isSynchronized": False},
                "/just_float": {"isSynchronized": False},
            },
        )
        self.change_configuration(
            target=self.component_another_thesame,
            config_diff={
                "plain_group": {"secretmap": {}, "listofstuff": ["wind", "vs", "oak"]},
                "just_float": 1000.304,
            },
        )

        for object_ in (
            self.cluster,
            self.service_not_simple,
            self.service_thesame,
            self.component_not_simple,
            self.component_another_not_simple,
            self.component_thesame,
            self.component_another_thesame,
        ):
            with self.subTest(object_.__class__.__name__):
                action = Action.objects.filter(prototype=object_.prototype).first()
                target = CoreObjectDescriptor(id=object_.id, type=model_name_to_core_type(object_.__class__.__name__))
                actual_inventory = decrypt_secrets(get_inventory_data(target=target, is_host_action=action.host_action))
                self.check_hosts_topology(actual_inventory["all"]["children"], expected_topology)
                self.assertDictEqual(actual_inventory["all"]["vars"], expected_parts["vars"])
                for group in actual_inventory["all"]["children"].values():
                    for host_name, actual_data in group["hosts"].items():
                        self.assertDictEqual(
                            actual_data["cluster"]["config"], expected_parts[f"{host_name}_cluster_config"]
                        )
                        self.assertDictEqual(actual_data["services"], expected_parts[f"{host_name}_services"])
