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

from typing import Iterable

from core.types import ADCMCoreType, CoreObjectDescriptor

from cm.api import DataForMultiBind, multi_bind
from cm.converters import model_name_to_core_type
from cm.models import (
    Action,
    ADCMModel,
    Cluster,
    Component,
    PrototypeImport,
    Service,
)
from cm.services.job.inventory import get_imports_for_inventory, get_inventory_data
from cm.tests.test_inventory.base import BaseInventoryTestCase, decrypt_secrets


class TestConfigAndImportsInInventory(BaseInventoryTestCase):
    PARTIAL_CONFIG = {
        "boolean": True,
        "secrettext": "awe\nsopme\n\ttext\n",
        "list": ["1", "5", "baset"],
        "variant_inline": "f",
        "plain_group": {"file": "contente\t\n\n\n\tbest\n\t   ", "map": {"k": "v", "key": "val"}},
    }

    FULL_CONFIG = {
        **PARTIAL_CONFIG,
        "integer": 4102,
        "float": 23.43,
        "string": "outside",
        "password": "unbreakable",
        "map": {"see": "yes", "no": "no"},
        "secretmap": {"see": "dont", "me": "you"},
        "json": '{"hey": ["yooo", 1]}',
        "file": "filecontent",
        "secretfile": "somesecrethere",
        "variant_builtin": "host-1",
        "plain_group": {**PARTIAL_CONFIG["plain_group"], "simple": "ingroup"},
        "activatable_group": {"simple": "inactive", "list": ["one", "two"]},
    }

    def setUp(self) -> None:
        super().setUp()

        self.provider = self.add_provider(
            bundle=self.add_bundle(self.bundles_dir / "provider_full_config"), name="Host Provider"
        )
        self.host_1 = self.add_host(bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host-1")
        self.host_2 = self.add_host(bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host-2")

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_full_config"), name="Main Cluster"
        )
        self.service = self.add_services_to_cluster(service_names=["all_params"], cluster=self.cluster).first()
        self.component = Component.objects.get(service=self.service)

        self.export_cluster_1 = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_config_host_group"), name="Cluster With Export 1"
        )
        self.export_cluster_2 = self.add_cluster(
            bundle=self.export_cluster_1.prototype.bundle, name="Cluster With Export 2"
        )
        self.export_service_1 = self.add_services_to_cluster(
            service_names=["for_export"], cluster=self.export_cluster_1
        ).first()
        self.export_service_2 = self.add_services_to_cluster(
            service_names=["for_export"], cluster=self.export_cluster_2
        ).first()

        self.context = {
            "cluster": self.cluster,
            "service": self.service,
            "component": self.component,
            "host_1": self.host_1,
            "host_2": self.host_2,
            "hostprovider": self.provider,
            "filedir": self.directories["FILE_DIR"],
        }

        self.cluster_with_defaults = self.add_cluster(bundle=self.cluster.prototype.bundle, name="With Default Imports")
        self.service_with_defaults = self.add_services_to_cluster(
            service_names=["imports_with_defaults"], cluster=self.cluster_with_defaults
        ).get()

    def prepare_cluster_hostcomponent(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        self.set_hostcomponent(
            cluster=self.cluster, entries=((self.host_1, self.component), (self.host_2, self.component))
        )

    @staticmethod
    def bind_objects(*entries: tuple[Cluster | Service, Iterable[Cluster | Service]]) -> None:
        for import_object, export_objects in entries:
            multibind_data: list[DataForMultiBind] = []

            for export_object in export_objects:
                if isinstance(export_object, Cluster):
                    export_entry = {"cluster_id": export_object.pk}
                else:
                    export_entry = {"cluster_id": export_object.cluster.pk, "service_id": export_object.pk}

                proto_import = PrototypeImport.objects.filter(
                    name=export_object.prototype.name, prototype=import_object.prototype
                ).first()

                multibind_data.append({"import_id": int(proto_import.pk), "export_id": export_entry})

            if isinstance(import_object, Cluster):
                multi_bind(cluster=import_object, service=None, bind_list=multibind_data)
            else:
                multi_bind(cluster=import_object.cluster, service=import_object, bind_list=multibind_data)

    def change_config_partial(self, target: ADCMModel) -> None:
        self.change_configuration(
            target=target,
            config_diff=self.PARTIAL_CONFIG,
            preprocess_config=lambda d: {
                **d,
                "map": {},
                "secretmap": {},
                "plain_group": {**d["plain_group"], "map": {}},
            },
        )

    def change_config_full(self, target: ADCMModel) -> None:
        self.change_configuration(
            target=target,
            config_diff=self.FULL_CONFIG,
            meta_diff={"/activatable_group": {"isActive": True}},
            preprocess_config=lambda d: {
                **d,
                "map": {},
                "secretmap": {},
                "activatable_group": d["activatable_group"],
                "plain_group": {**d["plain_group"], "map": {}},
            },
        )

    def test_provider_objects_success(self) -> None:
        self.change_config_partial(target=self.host_1)
        self.change_config_full(target=self.host_2)
        self.change_config_partial(target=self.provider)

        for object_, template in (
            (self.provider, "provider_full.json.j2"),
            (self.host_1, "host_1_full.json.j2"),
            (self.host_2, "host_2_full.json.j2"),
        ):
            with self.subTest(object_.__class__.__name__):
                action = Action.objects.filter(prototype=object_.prototype, name="dummy").first()
                target = CoreObjectDescriptor(id=object_.id, type=model_name_to_core_type(object_.__class__.__name__))
                actual_inventory = decrypt_secrets(get_inventory_data(target=target, is_host_action=action.host_action))
                expected_inventory = self.render_json_template(
                    file=self.templates_dir / "configs_and_imports" / template, context=self.context
                )
                self.assertDictEqual(actual_inventory, expected_inventory)

    def test_cluster_objects_no_import_success(self) -> None:
        self.prepare_cluster_hostcomponent()

        self.change_config_full(target=self.cluster)
        self.change_config_partial(target=self.component)

        expected_vars = self.render_json_template(
            file=self.templates_dir / "configs_and_imports" / "vars_no_imports.json.j2", context=self.context
        )

        for object_ in (self.cluster, self.service, self.component):
            with self.subTest(object_.__class__.__name__):
                action = Action.objects.filter(prototype=object_.prototype, name="dummy").first()
                target = CoreObjectDescriptor(id=object_.id, type=model_name_to_core_type(object_.__class__.__name__))
                actual_vars = decrypt_secrets(
                    get_inventory_data(target=target, is_host_action=action.host_action)["all"]["vars"]
                )
                self.assertDictEqual(actual_vars, expected_vars)

    def test_cluster_objects_single_import_success(self) -> None:
        self.prepare_cluster_hostcomponent()

        self.change_config_partial(target=self.service)
        self.change_config_full(target=self.component)

        self.change_configuration(
            target=self.export_cluster_1,
            config_diff={
                "list_of_dicts": [{"integer": 1, "string": "one"}],
                "just_integer": 100,
                "variant_inline": "f",
                "plain_group": {"list_of_dicts": [{"integer": 2, "string": "two"}]},
            },
        )

        self.bind_objects(
            # undefined behavior
            # (self.cluster, [self.export_cluster_1]),
            (self.service, [self.export_cluster_1, self.export_service_1]),
        )

        expected_vars = self.render_json_template(
            file=self.templates_dir / "configs_and_imports" / "vars_single_imports.json.j2", context=self.context
        )

        for object_ in (self.cluster, self.service, self.component):
            with self.subTest(object_.__class__.__name__):
                action = Action.objects.filter(prototype=object_.prototype, name="dummy").first()
                target = CoreObjectDescriptor(id=object_.id, type=model_name_to_core_type(object_.__class__.__name__))
                actual_vars = decrypt_secrets(
                    get_inventory_data(target=target, is_host_action=action.host_action)["all"]["vars"]
                )
                self.assertDictEqual(actual_vars, expected_vars)

    def test_cluster_objects_multi_import_success(self) -> None:
        self.prepare_cluster_hostcomponent()

        self.change_config_partial(target=self.cluster)
        self.change_config_full(target=self.service)

        self.bind_objects(
            (self.cluster, [self.export_cluster_2, self.export_service_1, self.export_service_2]),
            # undefined behavior
            # (self.service, [self.export_cluster_1, self.export_service_2]),
        )

        self.change_configuration(
            target=self.export_cluster_1,
            config_diff={
                "list_of_dicts": [{"integer": 1, "string": "one"}],
                "just_integer": 100,
                "variant_inline": "f",
                "plain_group": {"list_of_dicts": [{"integer": 2, "string": "two"}]},
            },
        )
        self.change_configuration(
            target=self.export_service_2,
            config_diff={
                "just_integer": 100,
                "plain_group": {"list_of_dicts": [{"integer": 3, "string": "three"}]},
                "activatable_group": {"secretmap": {"one": "two"}},
            },
            meta_diff={"/activatable_group": {"isActive": True}},
            preprocess_config=lambda d: {**d, "activatable_group": d["activatable_group"]},
        )

        expected_vars = self.render_json_template(
            file=self.templates_dir / "configs_and_imports" / "vars_multiple_imports.json.j2", context=self.context
        )

        for object_ in (self.cluster, self.service, self.component):
            with self.subTest(object_.__class__.__name__):
                action = Action.objects.filter(prototype=object_.prototype, name="dummy").first()
                target = CoreObjectDescriptor(id=object_.id, type=model_name_to_core_type(object_.__class__.__name__))
                actual_vars = decrypt_secrets(
                    get_inventory_data(target=target, is_host_action=action.host_action)["all"]["vars"]
                )
                self.assertDictEqual(actual_vars, expected_vars)

    def test_imports_have_default_no_import_success(self) -> None:
        self.change_configuration(
            target=self.service_with_defaults,
            config_diff={"another_stuff": {"hehe": 30.43}, "plain_group": {"listofstuff": ["204"]}},
        )

        expected = {
            "for_export": [{"another_stuff": {"hehe": 30.43}}],
            "very_complex": {"activatable_group": None, "plain_group": {"listofstuff": ["204"]}},
        }
        result = decrypt_secrets(get_imports_for_inventory(cluster_id=self.cluster_with_defaults.pk))
        self.assertDictEqual(result, expected)

    def test_imports_have_default_one_import_succeess(self) -> None:
        self.change_configuration(
            target=self.service_with_defaults,
            config_diff={"another_stuff": {"hehe": 500.5}, "plain_group": {"listofstuff": ["204"]}},
            meta_diff={"/activatable_group": {"isActive": True}},
        )
        self.bind_objects((self.service_with_defaults, [self.export_cluster_1]))

        expected = {
            "very_complex": {
                "just_integer": 4,
                "plain_group": {
                    "simple": "ingroup",
                    "secretmap": {"gk1": "gv1", "gk2": "gv2"},
                    "secretfile": f"{self.directories['FILE_DIR']}/cluster.2.plain_group.secretfile",
                    "list_of_dicts": None,
                    "listofstuff": ["x", "y"],
                },
                "variant_inline": None,
            },
            "for_export": [{"another_stuff": {"hehe": 500.5}}],
        }

        result = decrypt_secrets(get_imports_for_inventory(cluster_id=self.cluster_with_defaults.pk))
        self.assertDictEqual(result, expected)

    def test_imports_have_default_all_imported_success(self) -> None:
        self.bind_objects(
            (self.service_with_defaults, [self.export_cluster_1, self.export_service_1, self.export_service_2])
        )
        self.change_configuration(
            target=self.export_service_2,
            config_diff={"just_integer": 400},
            meta_diff={"/activatable_group": {"isActive": True}},
        )

        expected = {
            "very_complex": {
                "just_integer": 4,
                "plain_group": {
                    "simple": "ingroup",
                    "secretmap": {"gk1": "gv1", "gk2": "gv2"},
                    "secretfile": f"{self.directories['FILE_DIR']}/cluster.2.plain_group.secretfile",
                    "list_of_dicts": None,
                    "listofstuff": ["x", "y"],
                },
                "variant_inline": None,
            },
            "for_export": [
                {
                    "activatable_group": None,
                    "just_integer": 12,
                    "plain_group": {"list_of_dicts": None, "listofstuff": ["x", "y"]},
                },
                {
                    "activatable_group": {"simple": "inactgroup", "secretmap": {"agk1": "agv1", "agk2": "agv2"}},
                    "just_integer": 400,
                    "plain_group": {"list_of_dicts": None, "listofstuff": ["x", "y"]},
                },
            ],
        }
        result = decrypt_secrets(get_imports_for_inventory(cluster_id=self.cluster_with_defaults.pk))
        self.assertDictEqual(result, expected)

    def test_config_host_group_effect_on_import_with_default(self) -> None:
        host_3 = self.add_host(bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host-3")
        host_4 = self.add_host(bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host-4")

        self.add_host_to_cluster(cluster=self.cluster_with_defaults, host=host_3)
        self.add_host_to_cluster(cluster=self.cluster_with_defaults, host=host_4)
        component = Component.objects.filter(service=self.service_with_defaults).get()
        self.set_hostcomponent(cluster=self.cluster_with_defaults, entries=[(host_3, component), (host_4, component)])
        group = self.add_config_host_group(parent=self.service_with_defaults, hosts=[host_3])
        self.change_configuration(
            target=self.service_with_defaults,
            config_diff={"another_stuff": {"hehe": 500.5}, "plain_group": {"listofstuff": ["204"]}},
            meta_diff={"/activatable_group": {"isActive": True}},
        )
        self.change_configuration(
            target=group,
            config_diff={
                "another_stuff": {"hehe": 2000},
                "plain_group": {"listofstuff": ["ooo"]},
                "activatable_group": {"simple": "ch"},
            },
            meta_diff={"/activatable_group": {"isActive": True}},
        )
        self.bind_objects((self.service_with_defaults, [self.export_cluster_1]))

        action = Action.objects.filter(prototype=self.service_with_defaults.prototype, name="dummy").first()
        target = CoreObjectDescriptor(id=self.service_with_defaults.id, type=ADCMCoreType.SERVICE)
        result = decrypt_secrets(get_inventory_data(target=target, is_host_action=action.host_action))["all"]
        expected_vars_imports = {
            "very_complex": {
                "just_integer": 4,
                "plain_group": {
                    "simple": "ingroup",
                    "secretmap": {"gk1": "gv1", "gk2": "gv2"},
                    "secretfile": f"{self.directories['FILE_DIR']}/cluster.2.plain_group.secretfile",
                    "list_of_dicts": None,
                    "listofstuff": ["x", "y"],
                },
                "variant_inline": None,
            },
            "for_export": [{"another_stuff": {"hehe": 500.5}}],
        }

        self.assertDictEqual(result["vars"]["cluster"]["imports"], expected_vars_imports)
        self.assertDictEqual(result["hosts"]["host-3"]["cluster"]["imports"], expected_vars_imports)
        self.assertNotIn("cluster", result["hosts"]["host-4"])
