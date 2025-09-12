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

from unittest.mock import Mock, call, patch

from adcm.tests.base import BaseTestCase
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from cm.adcm_config.config import process_config
from cm.models import ADCM, ConfigLog


class TestAdcmConfig(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.adcm = ADCM.objects.first()
        self.config_log = ConfigLog.objects.get(obj_ref=self.adcm.config)
        self.config_log.config["ldap_integration"]["ldap_uri"] = "test_ldap_uri"
        self.config_log.config["ldap_integration"]["ldap_user"] = "test_ldap_user"
        self.config_log.config["ldap_integration"]["ldap_password"] = "test_ldap_password"
        self.config_log.config["ldap_integration"]["user_search_base"] = "test_ldap_user_search_base"
        self.config_log.config["global"]["adcm_url"] = "https://test_ldap.url"
        self.config_log.save(update_fields=["config"])

        self.no_rights_user.user_permissions.add(
            Permission.objects.get(
                codename="view_configlog", content_type=ContentType.objects.get_for_model(ConfigLog)
            ),
            Permission.objects.get(codename="add_configlog", content_type=ContentType.objects.get_for_model(ConfigLog)),
        )

    @patch("cm.adcm_config.config.cook_file_type_name")
    def test_process_config(self, mock_cook_file_type_name):
        mock_cook_file_type_name.return_value = "data_from_file"
        obj_mock = Mock()

        test_data = [
            ({"global": {"type": "file"}}, {"global": ""}, {"global": "data_from_file"}),
            (
                {"global": {"test": {"type": "file"}}},
                {"global": {"test": ""}},
                {"global": {"test": "data_from_file"}},
            ),
        ]

        for spec, conf, test_conf in test_data:
            with self.subTest(conf=conf, spec=spec):
                config = process_config(obj_mock, spec, conf)

                self.assertDictEqual(config, test_conf)

        mock_cook_file_type_name.assert_has_calls(
            [
                call(obj_mock, "global", ""),
                call(obj_mock, "global", "test"),
            ],
        )
