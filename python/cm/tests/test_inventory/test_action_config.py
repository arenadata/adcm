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
from cm.job import prepare_job_config
from cm.models import Action, ServiceComponent
from cm.tests.test_inventory.base import BaseInventoryTestCase
from django.conf import settings


class TestConfigAndImportsInInventory(BaseInventoryTestCase):
    CONFIG_WITH_NONES = {
        "boolean": True,
        "secrettext": "awe\nsopme\n\ttext\n",
        "list": ["1", "5", "baset"],
        "variant_inline": "f",
        "plain_group": {"file": "contente\t\n\n\n\tbest\n\t   ", "map": {"k": "v", "key": "val"}, "simple": None},
        "integer": None,
        "float": None,
        "string": None,
        "password": None,
        "map": None,
        "secretmap": None,
        "json": None,
        "file": None,
        "secretfile": None,
        "variant_builtin": None,
        "activatable_group": None,
    }

    FULL_CONFIG = {
        **CONFIG_WITH_NONES,
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
        "plain_group": {**CONFIG_WITH_NONES["plain_group"], "simple": "ingroup"},
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

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        self.set_hostcomponent(
            cluster=self.cluster, entries=((self.host_1, self.component), (self.host_2, self.component))
        )

        self.context = {
            "hostprovider_bundle": self.hostprovider.prototype.bundle,
            "cluster_bundle": self.cluster.prototype.bundle,
            "datadir": self.directories["DATA_DIR"],
            "stackdir": self.directories["STACK_DIR"],
            "token": settings.STATUS_SECRET_KEY,
        }

    def test_action_config(self) -> None:
        # Thou action has a defined config
        # `prepare_job_config` itself doesn't check input config sanity,
        # but `None` is a valid config,
        # so I find it easier to check it in pairs here rather than use a separate action
        for object_, config, type_name in (
            (self.cluster, None, "cluster"),
            (self.service, self.FULL_CONFIG, "service"),
            (self.component, self.CONFIG_WITH_NONES, "component"),
            (self.hostprovider, self.FULL_CONFIG, "hostprovider"),
            (self.host_1, self.CONFIG_WITH_NONES, "host"),
        ):
            with self.subTest(f"Own Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}.json.j2", context=self.context
                )

                action = Action.objects.filter(prototype=object_.prototype, name="with_config").first()
                job_config = prepare_job_config(
                    action=action, sub_action=None, job_id=1, obj=object_, conf=config, verbose=False
                )

                self.assertDictEqual(job_config, expected_data)

        for object_, config, type_name in (
            (self.cluster, self.FULL_CONFIG, "cluster"),
            (self.service, self.CONFIG_WITH_NONES, "service"),
            (self.component, None, "component"),
        ):
            with self.subTest(f"Host Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}_on_host.json.j2", context=self.context
                )

                action = Action.objects.filter(prototype=object_.prototype, name="with_config_on_host").first()
                job_config = prepare_job_config(
                    action=action, sub_action=action, job_id=100, obj=self.host_1, conf=config, verbose=True
                )

                self.assertDictEqual(job_config, expected_data)
