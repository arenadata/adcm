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

from cm.models import Action, ConfigLog
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestClusterHosts(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None

        bundles_dir = Path(__file__).parent.parent / "bundles"
        self.templates_dir = Path(__file__).parent.parent / "files/response_templates"

        self.provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")

    def test_cluster_action_on_cluster(self):
        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        expected_topology = {
            "CLUSTER": [],
        }
        expected_data = {
            ("CLUSTER", "vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                    "password": ConfigLog.objects.get(pk=self.cluster_1.config.current).config["password"],
                },
            ),
        }
        with self.subTest(
            msg=f"Object: {self.cluster_1.prototype.type} #{self.cluster_1.pk} "
            f"{self.cluster_1.name}, action: {action_on_cluster.name}"
        ):
            self.assert_inventory(self.cluster_1, action_on_cluster, expected_topology, expected_data)

    def test_add_1_host_on_cluster_actions(self):
        host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_host = Action.objects.get(name="action_on_host", prototype=host_1.prototype)

        host_names = [host_1.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
        }

        expected_data = {
            ("CLUSTER", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": host_1.fqdn,
                    "adcm_hostid": host_1.pk,
                    "password": ConfigLog.objects.get(pk=host_1.config.current).config["password"],
                },
            ),
            ("CLUSTER", "vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                    "password": ConfigLog.objects.get(pk=self.cluster_1.config.current).config["password"],
                },
            ),
        }

        for obj, action, expected_topology, expected_data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (
                host_1,
                action_on_host,
                {**expected_topology, **{"HOST": host_names}},
                {**expected_data, **self.get_action_on_host_expected_template_data_part(host=host_1)},
            ),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj, action, expected_topology, expected_data)

    def test_add_2_hosts_on_cluster_actions(self):
        host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )
        host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_host_1 = Action.objects.get(name="action_on_host", prototype=host_1.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=host_2.prototype)

        host_names = [host_1.fqdn, host_2.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
        }

        expected_data = {
            ("CLUSTER", "hosts"): (
                self.templates_dir / "two_hosts.json.j2",
                {
                    "host_1_id": host_1.pk,
                    "host_1_password": ConfigLog.objects.get(pk=host_1.config.current).config["password"],
                    "host_2_id": host_2.pk,
                    "host_2_password": ConfigLog.objects.get(pk=host_2.config.current).config["password"],
                },
            ),
            ("CLUSTER", "vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                    "password": ConfigLog.objects.get(pk=self.cluster_1.config.current).config["password"],
                },
            ),
        }

        for obj, action, expected_topology, expected_data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (
                host_1,
                action_on_host_1,
                {**expected_topology, **{"HOST": [host_1.fqdn]}},
                {**expected_data, **self.get_action_on_host_expected_template_data_part(host=host_1)},
            ),
            (
                host_2,
                action_on_host_2,
                {**expected_topology, **{"HOST": [host_2.fqdn]}},
                {**expected_data, **self.get_action_on_host_expected_template_data_part(host=host_2)},
            ),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj, action, expected_topology, expected_data)
