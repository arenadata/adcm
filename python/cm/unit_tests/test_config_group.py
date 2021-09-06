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

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from cm.models import GroupConfig, ConfigLog
from cm.unit_tests import utils


class GroupConfigTest(TestCase):
    """Tests `GroupConfig` model"""

    def setUp(self) -> None:
        config = {'group': {'string': 'string'}, 'activatable_group': {'integer': 1}}
        attr = {'activatable_group': {'active': True}}
        self.cluster = utils.gen_cluster()
        utils.gen_prototype_config(
            prototype=self.cluster.prototype, name='group', field_type='group', display_name='group'
        )
        utils.gen_prototype_config(
            prototype=self.cluster.prototype,
            name='group',
            field_type='string',
            subname='string',
            display_name='string',
        )
        utils.gen_prototype_config(
            prototype=self.cluster.prototype,
            name='activatable_group',
            field_type='group',
            display_name='activatable_group',
        )
        utils.gen_prototype_config(
            prototype=self.cluster.prototype,
            name='activatable_group',
            field_type='integer',
            subname='integer',
            display_name='integer',
        )
        self.cluster.config = utils.gen_config(config=config, attr=attr)
        self.cluster.save()

    @staticmethod
    def create_group(name, object_id, model_name):
        return GroupConfig.objects.create(
            object_id=object_id, object_type=ContentType.objects.get(model=model_name), name=name
        )

    def test_create_group(self):
        """Test create groups for objects"""
        group = self.create_group('group', self.cluster.id, 'cluster')
        parent_cl = ConfigLog.objects.get(id=self.cluster.config.current)
        parent_cl.save()
        cl = ConfigLog.objects.get(id=group.config.current)
        self.assertDictEqual(parent_cl.config, cl.config)
        self.assertDictEqual(parent_cl.attr, {'activatable_group': {'active': True}})
        cl_attr = {
            'activatable_group': {'active': True},
            'group_keys': {'group': {'string': False}, 'activatable_group': {'integer': False}},
            'custom_group_keys': {
                'group': {'string': False},
                'activatable_group': {'integer': False},
            },
        }
        self.assertDictEqual(cl.attr, cl_attr)

    def test_get_group_config(self):
        """Test get_group_config() method"""
        group = self.create_group('group', self.cluster.id, 'cluster')
        self.assertDictEqual(group.get_group_config(), {})
        cl = ConfigLog.objects.get(id=group.config.current)
        cl.config = {'group': {'string': 'str'}, 'activatable_group': {'integer': 1}}
        cl.attr = {
            'activatable_group': {'active': True},
            'group_keys': {'group': {'string': True}, 'activatable_group': {'integer': False}},
        }
        cl.save()
        self.assertDictEqual(group.get_group_config(), {'group': {'string': 'str'}})

    def test_get_config_spec(self):
        """Test get_config_spec() method"""
        group = self.create_group('group', self.cluster.id, 'cluster')
        spec = {
            'group': {
                'type': 'group',
                'group_customization': False,
                'fields': {
                    'string': {
                        'type': 'string',
                        'group_customization': False,
                    }
                },
            },
            'activatable_group': {
                'type': 'group',
                'group_customization': False,
                'fields': {
                    'integer': {
                        'type': 'integer',
                        'group_customization': False,
                    }
                },
            },
        }
        self.assertDictEqual(group.get_config_spec(), spec)

    def test_create_group_keys(self):
        """Test create_group_keys() method"""
        group = self.create_group('group', self.cluster.id, 'cluster')
        config = {'level1_1': 'str', 'level1_2': 1, 'level1_3': {'level2_1': [1, 2, 3]}}
        utils.gen_prototype_config(
            prototype=self.cluster.prototype,
            name='level1_1',
            field_type='string',
            group_customization=True,
        )
        utils.gen_prototype_config(
            prototype=self.cluster.prototype,
            name='level1_2',
            field_type='integer',
            group_customization=False,
        )
        utils.gen_prototype_config(
            prototype=self.cluster.prototype,
            name='level1_3',
            field_type='group',
            group_customization=False,
        )
        utils.gen_prototype_config(
            prototype=self.cluster.prototype,
            name='level1_3',
            subname='level2_1',
            field_type='list',
            group_customization=True,
        )
        test_group_keys = {'level1_1': False, 'level1_2': False, 'level1_3': {'level2_1': False}}
        test_custom_group_keys = {
            'level1_1': True,
            'level1_2': False,
            'level1_3': {'level2_1': True},
        }
        group_keys, custom_group_keys = group.create_group_keys(config, group.get_config_spec())
        self.assertDictEqual(test_group_keys, group_keys)
        self.assertDictEqual(test_custom_group_keys, custom_group_keys)

    def test_update_parent_config(self):
        """Test update config group"""
        group = self.create_group('group', self.cluster.id, 'cluster')
        cl = ConfigLog.objects.get(id=group.config.current)
        cl.config = {'group': {'string': 'str'}, 'activatable_group': {'integer': 1}}
        cl.attr = {
            'activatable_group': {'active': True},
            'group_keys': {'group': {'string': True}, 'activatable_group': {'integer': False}},
        }
        cl.save()
        parent_cl = ConfigLog.objects.get(id=self.cluster.config.current)
        parent_cl.config = {'group': {'string': 'string'}, 'activatable_group': {'integer': 100}}
        parent_cl.save()

        group.refresh_from_db()
        cl = ConfigLog.objects.get(id=group.config.current)
        self.assertDictEqual(
            cl.config, {'group': {'string': 'str'}, 'activatable_group': {'integer': 100}}
        )

        parent_cl.config = {'group': {'string': 'string'}, 'activatable_group': {'integer': 100}}
        parent_cl.attr = {'activatable_group': {'active': False}}
        parent_cl.save()

        group.refresh_from_db()
        cl = ConfigLog.objects.get(id=group.config.current)
        self.assertDictEqual(
            cl.config, {'group': {'string': 'str'}, 'activatable_group': {'integer': 100}}
        )
        self.assertDictEqual(
            cl.attr,
            {
                'activatable_group': {'active': True},
                'group_keys': {'group': {'string': True}, 'activatable_group': {'integer': False}},
                'custom_group_keys': {
                    'group': {'string': False},
                    'activatable_group': {'integer': False},
                },
            },
        )
