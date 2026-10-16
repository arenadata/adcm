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

"""
Config host group processing of `adcm_config` lookup plugin.

Spec and group keys preparation used to be `ConfigHostGroup` methods,
but nothing besides this plugin called them.
"""

from pathlib import Path

from ansible_collections.arenadata.adcm.plugins.lookup.adcm_config import create_group_keys, get_config_spec
from cm.models import ConfigHostGroup, ConfigLog
import django.test

from tests.suites import _ADCMTestCase

BUNDLES_DIR = Path(__file__).parent / "bundles"


class TestConfigHostGroupProcessing(_ADCMTestCase, django.test.TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

        cls.bundle = cls.uc.upload_bundle(BUNDLES_DIR / "cluster_lookup_config_groups")
        cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name="Cluster With Groups")

    def setUp(self) -> None:
        super().setUp()

        self.host_group = self.uc.add_config_host_group(owner=self.cluster, name="group")

    def test_create_group(self) -> None:
        """Group's config repeats owner's one, group keys are added to attributes"""
        owner_config = ConfigLog.objects.get(id=self.cluster.config.current)
        group_config = ConfigLog.objects.get(id=self.host_group.config.current)

        self.assertDictEqual(group_config.config, owner_config.config)
        self.assertDictEqual(owner_config.attr, {"activatable_group": {"active": True}})
        self.assertDictEqual(
            group_config.attr,
            {
                "activatable_group": {"active": True},
                "group_keys": {
                    "group": {"value": None, "fields": {"string": False}},
                    "activatable_group": {"value": False, "fields": {"integer": False}},
                    "customizable": False,
                    "not_customizable": False,
                    "not_customizable_group": {"value": None, "fields": {"customizable_field": False}},
                },
            },
        )

    def test_get_config_spec(self) -> None:
        spec = {
            "group": {
                "type": "group",
                "group_customization": True,
                "limits": {},
                "fields": {"string": {"type": "string", "group_customization": True, "limits": {}}},
            },
            "activatable_group": {
                "type": "group",
                "group_customization": True,
                "limits": {"activatable": True, "active": True},
                "fields": {"integer": {"type": "integer", "group_customization": True, "limits": {}}},
            },
            "customizable": {"type": "string", "group_customization": True, "limits": {}},
            "not_customizable": {"type": "integer", "group_customization": False, "limits": {}},
            "not_customizable_group": {
                "type": "group",
                "group_customization": False,
                "limits": {},
                "fields": {"customizable_field": {"type": "list", "group_customization": True, "limits": {}}},
            },
        }

        self.assertDictEqual(get_config_spec(group=self.host_group), spec)

    def test_create_group_keys(self) -> None:
        expected_group_keys = {
            "group": {"value": None, "fields": {"string": False}},
            "activatable_group": {"value": False, "fields": {"integer": False}},
            "customizable": False,
            "not_customizable": False,
            "not_customizable_group": {"value": None, "fields": {"customizable_field": False}},
        }
        expected_custom_group_keys = {
            "group": {"value": True, "fields": {"string": True}},
            "activatable_group": {"value": True, "fields": {"integer": True}},
            "customizable": True,
            "not_customizable": False,
            "not_customizable_group": {"value": False, "fields": {"customizable_field": True}},
        }

        group_keys, custom_group_keys = create_group_keys(
            group=self.host_group, config_spec=get_config_spec(group=self.host_group)
        )

        self.assertDictEqual(group_keys, expected_group_keys)
        self.assertDictEqual(custom_group_keys, expected_custom_group_keys)

    def test_group_of_another_owner_is_not_affected(self) -> None:
        another_cluster = self.uc.add_cluster(bundle=self.bundle, name="Another Cluster With Groups")
        another_group = self.uc.add_config_host_group(owner=another_cluster, name="group")

        self.assertEqual(ConfigHostGroup.objects.filter(object_id=self.cluster.pk).count(), 1)
        self.assertNotEqual(another_group.config_id, self.host_group.config_id)
