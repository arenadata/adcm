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

from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from cm.models import Cluster, Prototype, ObjectConfig, Bundle
import cm.api as api_module


class TestApi(TestCase):

    def setUp(self):
        self.bundle = Bundle.objects.create(**{
            'name': 'ADB',
            'version': '2.5',
            'version_order': 4,
            'edition': 'community',
            'license': 'absent',
            'license_path': None,
            'license_hash': None,
            'hash': '2232f33c6259d44c23046fce4382f16c450f8ba5',
            'description': '',
            'date': timezone.now()
        })

        self.prototype = Prototype.objects.create(**{
            'bundle_id': self.bundle.id,
            'type': 'cluster',
            'name': 'ADB',
            'display_name': 'ADB',
            'version': '2.5',
            'version_order': 11,
            'required': False,
            'shared': False,
            'adcm_min_version': None,
            'monitoring': 'active',
            'description': ''
        })
        self.object_config = ObjectConfig.objects.create(**{
            'current': 1,
            'previous': 1
        })

        self.cluster = Cluster.objects.create(**{
            'prototype_id': self.prototype.id,
            'name': 'Fear Limpopo',
            'description': '',
            'config_id': self.object_config.id,
            'state': 'installed',
            'stack': '[]',
            'issue': '{}'
        })

    def test_push_obj(self):
        stack = self.cluster.stack

        cluster = api_module.push_obj(self.cluster, 'started')

        self.assertEqual(cluster.id, self.cluster.id)
        self.assertEqual(cluster.prototype_id, self.cluster.prototype_id)
        self.assertEqual(cluster.name, self.cluster.name)
        self.assertEqual(cluster.description, self.cluster.description)
        self.assertEqual(cluster.config_id, self.cluster.config_id)
        self.assertEqual(cluster.state, self.cluster.state)
        self.assertTrue(cluster.stack != stack)
        self.assertEqual(cluster.issue, self.cluster.issue)

    @patch('cm.status_api.set_obj_state')
    def test_set_object_state(self, mock_set_obj_state):
        state = self.cluster.state

        cluster = api_module.set_object_state(self.cluster, 'created')

        self.assertEqual(cluster.id, self.cluster.id)
        self.assertEqual(cluster.prototype_id, self.cluster.prototype_id)
        self.assertEqual(cluster.name, self.cluster.name)
        self.assertEqual(cluster.description, self.cluster.description)
        self.assertEqual(cluster.config_id, self.cluster.config_id)
        self.assertTrue(cluster.state != state)
        self.assertEqual(cluster.state, 'created')
        self.assertEqual(cluster.stack,  self.cluster.stack)
        self.assertEqual(cluster.issue, self.cluster.issue)

        self.assertEqual(mock_set_obj_state.call_count, 1)
        self.assertEqual(mock_set_obj_state.call_args.args,
                         (self.cluster.prototype.type, self.cluster.id, 'created'))
