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

from cm.api import DataForMultiBind, multi_bind
from cm.inventory import get_inventory_data
from cm.models import (
    Action,
    ADCMModel,
    Cluster,
    ClusterObject,
    PrototypeImport,
    ServiceComponent,
)
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

        self.hostprovider = self.add_provider(
            bundle=self.add_bundle(self.bundles_dir / "provider_full_config"), name="Host Provider"
        )
        self.host_1 = self.add_host(
            bundle=self.hostprovider.prototype.bundle, provider=self.hostprovider, fqdn="host-1"
        )
        self.host_2 = self.add_host(
            bundle=self.hostprovider.prototype.bundle, provider=self.hostprovider, fqdn="host-2"
        )

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_full_config"), name="Main Cluster"
        )
        self.service = self.add_services_to_cluster(service_names=["all_params"], cluster=self.cluster).first()
        self.component = ServiceComponent.objects.get(service=self.service)

        self.export_cluster_1 = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_group_config"), name="Cluster With Export 1"
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
            "hostprovider": self.hostprovider,
            "filedir": self.directories["FILE_DIR"],
        }

    def prepare_cluster_hostcomponent(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        self.set_hostcomponent(
            cluster=self.cluster, entries=((self.host_1, self.component), (self.host_2, self.component))
        )

    @staticmethod
    def bind_objects(*entries: tuple[Cluster | ClusterObject, Iterable[Cluster | ClusterObject]]) -> None:
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

    def test_hostprovider_objects_success(self) -> None:
        self.change_config_partial(target=self.host_1)
        self.change_config_full(target=self.host_2)
        self.change_config_partial(target=self.hostprovider)

        for object_, template in (
            (self.hostprovider, "hostprovider_full.json.j2"),
            (self.host_1, "host_1_full.json.j2"),
            (self.host_2, "host_2_full.json.j2"),
        ):
            with self.subTest(object_.__class__.__name__):
                action = Action.objects.filter(prototype=object_.prototype, name="dummy").first()
                actual_inventory = decrypt_secrets(get_inventory_data(obj=object_, action=action)["all"]["children"])
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
                actual_inventory = decrypt_secrets(get_inventory_data(obj=object_, action=action)["all"]["children"])

            self.assertDictEqual(actual_inventory["CLUSTER"]["vars"], expected_vars)

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
                actual_inventory = decrypt_secrets(get_inventory_data(obj=object_, action=action)["all"]["children"])
            self.assertDictEqual(actual_inventory["CLUSTER"]["vars"], expected_vars)

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
                actual_inventory = decrypt_secrets(get_inventory_data(obj=object_, action=action)["all"]["children"])
                self.assertDictEqual(actual_inventory["CLUSTER"]["vars"], expected_vars)
