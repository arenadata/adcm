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

from unittest.mock import patch, Mock, call

from django.test import TestCase

import cm.inventory
from cm.models import (
    ObjectConfig, ConfigLog, ADCM, Prototype, Bundle, Cluster
)


class TestInventory(TestCase):

    def setUp(self):
        self.bundle = Bundle.objects.create(
            version='1.0',
            hash='2232f33c6259d44c23046fce4382f16c450f8ba5')
        self.prototype = Prototype.objects.create(
            bundle=self.bundle,
            type='adcm',
            version='1.0'
        )
        self.cluster = Cluster.objects.create(
            prototype=self.prototype
        )
        self.object_config = ObjectConfig.objects.create(
            current=1,
            previous=1
        )
        self.config_log = ConfigLog.objects.create(
            obj_ref=self.object_config,
            config='{}'
        )
        self.adcm = ADCM.objects.create(
            prototype=self.prototype
        )

    @patch('cm.inventory.cook_file_type_name')
    @patch('cm.inventory.get_prototype_config')
    def test_process_config(self, mock_get_prototype_config, mock_cook_file_type_name):
        mock_cook_file_type_name.return_value = 'data_from_file'
        obj_mock = Mock()
        obj_mock.prototype = Mock()

        test_data = [
            (
                {'global': ''},
                ({'global': {'type': 'file'}}, {}, {}, {}),
                None,
                {'global': 'data_from_file'}
            ),
            (
                {'global': {'test': ''}},
                ({'global': {'test': {'type': 'file'}}}, {}, {}, {}),
                None,
                {'global': {'test': 'data_from_file'}}
            ),
            (
                {},
                ({}, {}, {}, {}),
                '{"global": {"active": false}}',
                {'global': None}
            ),
        ]

        for conf, spec, attr, test_conf in test_data:
            with self.subTest(conf=conf, spec=spec, attr=attr):
                mock_get_prototype_config.return_value = spec

                config = cm.inventory.process_config(obj_mock, conf, attr)

                self.assertDictEqual(config, test_conf)

        mock_get_prototype_config.assert_has_calls([
            call(obj_mock.prototype),
            call(obj_mock.prototype),
            call(obj_mock.prototype),
        ])
        mock_cook_file_type_name.assert_has_calls([
            call(obj_mock, 'global', ''),
            call(obj_mock, 'global', 'test'),
        ])

    def test_get_import(self):
        pass

    def test_get_obj_config(self):
        pass
