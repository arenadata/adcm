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


from cm.models import ConfigLog
from cm.tests.utils import gen_cluster, gen_config, gen_group, gen_prototype_config

from adcm.tests.base import BaseTestCase


class GroupConfigTest(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_config = {"group": {"string": "string"}, "activatable_group": {"integer": 1}}
        self.cluster_attr = {"activatable_group": {"active": True}}
        self.cluster = gen_cluster()
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="group",
            field_type="group",
            display_name="group",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="group",
            field_type="string",
            subname="string",
            display_name="string",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="activatable_group",
            field_type="group",
            display_name="activatable_group",
            limits="{'activatable': true, 'active': true}",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="activatable_group",
            field_type="integer",
            subname="integer",
            display_name="integer",
            group_customization=True,
        )
        self.cluster.config = gen_config(config=self.cluster_config, attr=self.cluster_attr)
        self.cluster.save()

    def test_create_group(self):
        """Test create groups for objects"""
        group = gen_group("group", self.cluster.id, "cluster")
        parent_cl = ConfigLog.objects.get(id=self.cluster.config.current)
        config_log = ConfigLog.objects.get(id=group.config.current)

        self.assertDictEqual(parent_cl.config, config_log.config)
        self.assertDictEqual(parent_cl.attr, {"activatable_group": {"active": True}})

        cl_attr = {
            "activatable_group": {"active": True},
            "group_keys": {
                "group": {"value": None, "fields": {"string": False}},
                "activatable_group": {"value": False, "fields": {"integer": False}},
            },
            "custom_group_keys": {
                "group": {"value": True, "fields": {"string": True}},
                "activatable_group": {"value": True, "fields": {"integer": True}},
            },
        }

        self.assertDictEqual(config_log.attr, cl_attr)

    def test_get_config_spec(self):
        group = gen_group("group", self.cluster.id, "cluster")
        spec = {
            "group": {
                "type": "group",
                "group_customization": True,
                "limits": {},
                "fields": {
                    "string": {
                        "type": "string",
                        "group_customization": True,
                        "limits": {},
                    },
                },
            },
            "activatable_group": {
                "type": "group",
                "group_customization": True,
                "limits": "{'activatable': true, 'active': true}",
                "fields": {
                    "integer": {
                        "type": "integer",
                        "group_customization": True,
                        "limits": {},
                    },
                },
            },
        }

        self.assertDictEqual(group.get_config_spec(), spec)

    def test_create_group_keys(self):
        group = gen_group("group", self.cluster.id, "cluster")
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="level1_1",
            field_type="string",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="level1_2",
            field_type="integer",
            group_customization=False,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="level1_3",
            field_type="group",
            group_customization=False,
        )
        gen_prototype_config(
            prototype=self.cluster.prototype,
            name="level1_3",
            subname="level2_1",
            field_type="list",
            group_customization=True,
        )
        test_group_keys = {
            "activatable_group": {
                "value": False,
                "fields": {"integer": False},
            },
            "group": {
                "value": None,
                "fields": {"string": False},
            },
            "level1_1": False,
            "level1_2": False,
            "level1_3": {
                "value": None,
                "fields": {"level2_1": False},
            },
        }
        test_custom_group_keys = {
            "activatable_group": {
                "value": True,
                "fields": {"integer": True},
            },
            "group": {
                "value": True,
                "fields": {"string": True},
            },
            "level1_1": True,
            "level1_2": False,
            "level1_3": {
                "value": False,
                "fields": {"level2_1": True},
            },
        }
        group_keys, custom_group_keys = group.create_group_keys(group.get_config_spec())

        self.assertDictEqual(test_group_keys, group_keys)
        self.assertDictEqual(test_custom_group_keys, custom_group_keys)
