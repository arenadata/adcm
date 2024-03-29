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

from adcm.tests.base import BaseTestCase, BusinessLogicMixin
from ansible_plugin.utils import set_cluster_config, set_provider_config

from cm.adcm_config.ansible import ansible_decrypt
from cm.models import ConfigLog


class TestAnsiblePluginADCMConfig(BusinessLogicMixin, BaseTestCase):
    def setUp(self):
        super().setUp()
        self.bundles_dir = Path(__file__).parent.parent / "bundles"

        cluster_bundle = self.add_bundle(source_dir=self.bundles_dir / "cluster_full_config")
        provider_bundle = self.add_bundle(source_dir=self.bundles_dir / "provider_full_config")
        cluster_multiple_activatable_group_bundle = self.add_bundle(
            source_dir=self.bundles_dir / "cluster_multiple_activatable_group_config"
        )
        self.cluster_1 = self.add_cluster(bundle=cluster_multiple_activatable_group_bundle, name="cluster_1")
        self.current_cluster_1_config = ConfigLog.objects.get(id=self.cluster_1.config.current)
        self.cluster = self.add_cluster(bundle=cluster_bundle, name="cluster")
        self.current_cluster_config = ConfigLog.objects.get(id=self.cluster.config.current)
        self.provider = self.add_provider(bundle=provider_bundle, name="provider")
        self.current_provider_config = ConfigLog.objects.get(id=self.provider.config.current)

    def test_edit_provider_config_no_changes_success(self):
        config = {"source_list": ["ok", "fail"]}
        attr = {}

        set_provider_config(provider_id=self.provider.pk, config=config, attr=attr)

        self.provider.refresh_from_db()
        changed_hostprovider_config = ConfigLog.objects.get(id=self.provider.config.current)

        self.assertEqual(self.current_provider_config.pk, changed_hostprovider_config.pk)

    def test_edit_cluster_config_with_activate_group_changed_success(self):
        config = {
            "activatable_group": {"simple": "string"},
            "boolean": False,
            "plain_group": {"map": {"key": "value"}},
            "list": ["value4", "value2", "value3"],
        }
        attr = {"activatable_group": {"active": True}}

        set_cluster_config(cluster_id=self.cluster.pk, config=config, attr=attr)

        self.cluster.refresh_from_db()
        changed_cluster_config = ConfigLog.objects.get(id=self.cluster.config.current)

        self.assertNotEqual(self.current_cluster_config.pk, changed_cluster_config.pk)
        self.assertEqual(changed_cluster_config.config["activatable_group"]["simple"], "string")
        self.assertFalse(changed_cluster_config.config["boolean"])
        self.assertDictEqual(changed_cluster_config.config["plain_group"]["map"], {"key": "value"})
        self.assertListEqual(changed_cluster_config.config["list"], ["value4", "value2", "value3"])
        self.assertTrue(changed_cluster_config.attr["activatable_group"]["active"])

    def test_edit_provider_config_secret_field_changed_success(self):
        config = {"secretmap": {"secret_string": "string"}}
        attr = {}

        set_provider_config(provider_id=self.provider.pk, config=config, attr=attr)

        self.provider.refresh_from_db()
        changed_provider_config = ConfigLog.objects.get(id=self.provider.config.current)

        self.assertNotEqual(self.current_cluster_config.pk, changed_provider_config.pk)
        self.assertEqual("string", ansible_decrypt(changed_provider_config.config["secretmap"]["secret_string"]))

    def test_edit_cluster_config_one_field_changed_success(self):
        config = {
            "source_list": ["ok", "fail", "abort"],
        }
        attr = {}

        set_cluster_config(cluster_id=self.cluster.pk, config=config, attr=attr)

        self.cluster.refresh_from_db()

        changed_cluster_config = ConfigLog.objects.get(id=self.cluster.config.current)

        self.assertNotEqual(self.current_cluster_config.pk, changed_cluster_config.pk)
        self.assertNotEqual(
            self.current_cluster_config.config["source_list"], changed_cluster_config.config["source_list"]
        )

    def test_edit_cluster_config_update_empty_string_field_not_changes_success(self):
        config = {"string": ""}
        attr = {}

        set_cluster_config(cluster_id=self.cluster.pk, config=config, attr=attr)

        self.cluster.refresh_from_db()
        changed_cluster_config = ConfigLog.objects.get(id=self.cluster.config.current)
        self.assertEqual(self.current_cluster_config.pk, changed_cluster_config.pk)

    def test_edit_cluster_config_update_only_activated_group_changed_success(self):
        # TODO: need to send for update attr, this is guaranteed by the function `_get_config` from ActionModule class
        config = {"activatable_group": {}}
        attr = {"activatable_group": {"active": True}}

        set_cluster_config(cluster_id=self.cluster.pk, config=config, attr=attr)

        self.cluster.refresh_from_db()
        changed_cluster_config = ConfigLog.objects.get(id=self.cluster.config.current)
        self.assertNotEqual(self.current_cluster_config.pk, changed_cluster_config.pk)
        self.assertTrue(changed_cluster_config.attr["activatable_group"]["active"])

    def test_edit_cluster_config_update_only_activated_group_no_changes_success(self):
        # TODO: need to send for update attr, this is guaranteed by the function `_get_config` from ActionModule class
        config = {"activatable_group": {}}
        attr = {"activatable_group": {"active": False}}

        set_cluster_config(cluster_id=self.cluster.pk, config=config, attr=attr)

        self.cluster.refresh_from_db()
        changed_cluster_config = ConfigLog.objects.get(id=self.cluster.config.current)
        self.assertEqual(self.current_cluster_config.pk, changed_cluster_config.pk)

    def test_edit_cluster_config_update_multiple_activatable_group_changed_success(self):
        # TODO: need to send for update attr, this is guaranteed by the function `_get_config` from ActionModule class
        config = {"activatable_group_string": {}, "activatable_group_integer": {}}
        attr = {"activatable_group_string": {"active": True}, "activatable_group_integer": {"active": True}}

        set_cluster_config(cluster_id=self.cluster_1.pk, config=config, attr=attr)

        self.cluster_1.refresh_from_db()
        changed_cluster_config = ConfigLog.objects.get(id=self.cluster_1.config.current)
        self.assertNotEqual(changed_cluster_config.pk, self.current_cluster_1_config.pk)
        self.assertTrue(changed_cluster_config.attr["activatable_group_string"]["active"])
        self.assertTrue(changed_cluster_config.attr["activatable_group_integer"]["active"])

    def test_edit_cluster_config_update_multiple_activatable_group_no_changed_success(self):
        # TODO: need to send for update attr, this is guaranteed by the function `_get_config` from ActionModule class
        config = {"activatable_group_string": {}, "activatable_group_integer": {}}
        attr = {"activatable_group_string": {"active": False}, "activatable_group_integer": {"active": False}}

        set_cluster_config(cluster_id=self.cluster_1.pk, config=config, attr=attr)

        self.cluster_1.refresh_from_db()
        changed_cluster_config = ConfigLog.objects.get(id=self.cluster_1.config.current)
        self.assertEqual(changed_cluster_config.pk, self.current_cluster_1_config.pk)
