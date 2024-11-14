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

from cm.models import Action
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestInventoryProviderHost(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_bundle = self.add_bundle(source_dir=self.bundles_dir / "provider")

        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")
        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host_1")
        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host_2")

        self.action_on_provider = Action.objects.get(name="action_on_provider", prototype=self.provider.prototype)
        self.action_on_host_1 = Action.objects.get(name="action_on_host", prototype=self.host_1.prototype)
        self.action_on_host_2 = Action.objects.get(name="action_on_host", prototype=self.host_2.prototype)

    def test_action_on_provider(self):
        expected_topology = {
            "PROVIDER": [self.host_1.fqdn, self.host_2.fqdn],
        }
        expected_data = {
            ("PROVIDER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("PROVIDER", "hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.provider,
            action=self.action_on_provider,
            expected_topology=expected_topology,
            expected_data=expected_data,
        )

    def test_action_on_host(self):
        expected_topology = {
            "HOST": [self.host_1.fqdn],
        }
        expected_data = {
            ("HOST", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.host_1.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.host_1,
            action=self.action_on_host_1,
            expected_topology=expected_topology,
            expected_data=expected_data,
        )

    def test_action_on_provider_with_config_host_group(self):
        provider_host_group = self.add_config_host_group(parent=self.provider, hosts=[self.host_1])
        self.change_configuration(
            target=provider_host_group,
            config_diff={"integer": 101},
            meta_diff={"/integer": {"isSynchronized": False}},
        )

        expected_topology = {
            "PROVIDER": [self.host_1.fqdn, self.host_2.fqdn],
        }
        expected_data = {
            ("PROVIDER", "hosts", f"{self.host_1.fqdn}"): (
                self.templates_dir / "host_with_provider_vars.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                    "provider_config_integer": 101,
                    "provider_id": self.provider.pk,
                },
            ),
            ("PROVIDER", "hosts", f"{self.host_2.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.provider,
            action=self.action_on_provider,
            expected_topology=expected_topology,
            expected_data=expected_data,
        )

    def test_action_on_host_with_config_host_group(self):
        provider_host_group = self.add_config_host_group(parent=self.provider, hosts=[self.host_1])
        self.change_configuration(
            target=provider_host_group,
            config_diff={"integer": 101},
            meta_diff={"/integer": {"isSynchronized": False}},
        )

        expected_topology = {
            "HOST": [self.host_1.fqdn],
        }
        expected_data = {
            ("HOST", "hosts", f"{self.host_1.fqdn}"): (
                self.templates_dir / "host_with_provider_vars.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                    "provider_id": self.provider.pk,
                    "provider_config_integer": 101,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.host_1,
            action=self.action_on_host_1,
            expected_data=expected_data,
            expected_topology=expected_topology,
        )

    def test_action_on_host_without_config_host_group(self):
        provider_host_group = self.add_config_host_group(parent=self.provider, hosts=[self.host_1])
        self.change_configuration(
            target=provider_host_group,
            config_diff={"integer": 101},
            meta_diff={"/integer": {"isSynchronized": False}},
        )

        expected_topology = {
            "HOST": [self.host_2.fqdn],
        }
        expected_data = {
            ("HOST", "hosts", f"{self.host_2.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_2.prototype.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.host_2,
            action=self.action_on_host_2,
            expected_data=expected_data,
            expected_topology=expected_topology,
        )
