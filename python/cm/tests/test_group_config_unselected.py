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
# pylint: disable=wrong-import-order

from cm.adcm_config import check_value_unselected_field
from cm.errors import AdcmEx
from cm.models import GroupConfig
from cm.tests.utils import gen_cluster, gen_config, gen_prototype_config
from django.contrib.contenttypes.models import ContentType

from adcm.tests.base import BaseTestCase


class TestUnselectedFields(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.cluster_config = {
            "list": None,
            "string": None,
            "map": None,
            "structure": None,
            "json": None,
        }
        self.cluster_attr = {}
        self.cluster = gen_cluster()
        self.cluster.config = gen_config(config=self.cluster_config, attr=self.cluster_attr)
        self.cluster.save()
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="list",
            field_type="list",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="map",
            field_type="map",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="string",
            field_type="string",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="structure",
            field_type="structure",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="json",
            field_type="json",
            group_customization=True,
        )
        self.group = GroupConfig.objects.create(
            object_id=self.cluster.id,
            object_type=ContentType.objects.get(model="cluster"),
            name="Group_config",
        )
        self.spec = self.group.get_config_spec()
        self.new_attr = {
            "group_keys": {
                "string": False,
                "list": False,
                "map": False,
                "structure": False,
                "json": False,
            },
        }
        self.group_keys = self.new_attr.get("group_keys")

    def test_empty_list_string_map(self):
        config_with_empty_values = {
            "list": [],
            "string": "",
            "map": {},
            "structure": {},
            "json": None,
        }
        check_value_unselected_field(
            self.cluster_config,
            config_with_empty_values,
            self.cluster_attr,
            self.new_attr,
            self.group_keys,
            self.spec,
            self.cluster,
        )

        check_value_unselected_field(
            config_with_empty_values,
            self.cluster_config,
            self.cluster_attr,
            self.new_attr,
            self.group_keys,
            self.spec,
            self.cluster,
        )
        new_config = {"list": None, "string": None, "map": None, "structure": None, "json": {}}
        with self.assertRaisesRegex(AdcmEx, r"Value of `json` field is different in current and new config."):
            check_value_unselected_field(
                self.cluster_config,
                new_config,
                self.cluster_attr,
                self.new_attr,
                self.group_keys,
                self.spec,
                self.cluster,
            )

        new_config = {
            "list": None,
            "string": None,
            "map": None,
            "structure": {"test": []},
            "json": None,
        }
        with self.assertRaisesRegex(AdcmEx, r"Value of `structure` field is different in current and new config."):
            check_value_unselected_field(
                self.cluster_config,
                new_config,
                self.cluster_attr,
                self.new_attr,
                self.group_keys,
                self.spec,
                self.cluster,
            )

    def test_unequal_values(self):
        cluster_config = {"list": [], "string": "", "map": {}, "structure": {}, "json": {}}
        self.cluster.config = gen_config(config=cluster_config, attr=self.cluster_attr)
        self.cluster.save()

        new_config = {"list": [], "string": "wow", "map": {}, "structure": {}, "json": {}}
        with self.assertRaisesRegex(AdcmEx, r"Value of `string` field is different in current and new config."):
            check_value_unselected_field(
                self.cluster_config,
                new_config,
                self.cluster_attr,
                self.new_attr,
                self.group_keys,
                self.spec,
                self.cluster,
            )

        new_config = {"list": [1, 2, 3], "string": "", "map": {}, "structure": {}, "json": {}}
        with self.assertRaisesRegex(AdcmEx, r"Value of `list` field is different in current and new config."):
            check_value_unselected_field(
                self.cluster_config,
                new_config,
                self.cluster_attr,
                self.new_attr,
                self.group_keys,
                self.spec,
                self.cluster,
            )

        new_config = {"list": [], "string": "", "map": {"key": 1}, "structure": {}, "json": {}}
        with self.assertRaisesRegex(AdcmEx, r"Value of `map` field is different in current and new config."):
            check_value_unselected_field(
                self.cluster_config,
                new_config,
                self.cluster_attr,
                self.new_attr,
                self.group_keys,
                self.spec,
                self.cluster,
            )

        new_config = {"list": [], "string": "", "map": {}, "structure": {"key": 1}, "json": {}}
        with self.assertRaisesRegex(AdcmEx, r"Value of `structure` field is different in current and new config."):
            check_value_unselected_field(
                self.cluster_config,
                new_config,
                self.cluster_attr,
                self.new_attr,
                self.group_keys,
                self.spec,
                self.cluster,
            )

        new_config = {"list": [], "string": "", "map": {}, "structure": {}, "json": {"key": 1}}
        with self.assertRaisesRegex(AdcmEx, r"Value of `json` field is different in current and new config."):
            check_value_unselected_field(
                self.cluster_config,
                new_config,
                self.cluster_attr,
                self.new_attr,
                self.group_keys,
                self.spec,
                self.cluster,
            )
