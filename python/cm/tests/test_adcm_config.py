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

from typing import Any
from unittest.mock import Mock, call, patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from tests.base import BaseTestCase

from cm.errors import AdcmEx
from cm.legacy.adcm_config.config import (
    get_full_display_name_from_spec,
    get_spec_flat_spec_config_attr_from_prototype_configs,
    process_config,
    process_json_config,
)
from cm.models import ADCM, ConfigLog
from cm.tests.utils import gen_bundle, gen_cluster, gen_config, gen_group, gen_prototype, gen_prototype_config


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

    @patch("cm.legacy.adcm_config.config.cook_file_type_name")
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

    def test_get_full_display_names_of_spec_parameters(self):
        full_display_name_root = "Root Display"
        full_display_name_group = "Group Display"
        full_display_name_sub_int = "Group Display/Sub Display"
        full_name_param = "param_no_displ_name"

        prototype = gen_prototype(bundle=gen_bundle(), proto_type="cluster")
        root = gen_prototype_config(
            prototype=prototype, name="root_technical", field_type="string", display_name=full_display_name_root
        )
        group = gen_prototype_config(
            prototype=prototype, name="group_technical", field_type="group", display_name=full_display_name_group
        )
        sub_int = gen_prototype_config(
            prototype=prototype,
            name="group_technical",
            subname="sub_technical",
            field_type="integer",
            display_name="Sub Display",
        )
        param_no_displ = gen_prototype_config(prototype=prototype, name=full_name_param, field_type="string")

        spec, flat_spec, config, attr = get_spec_flat_spec_config_attr_from_prototype_configs(
            prototype=prototype, prototype_configs=(root, group, sub_int, param_no_displ)
        )

        self.assertEqual(spec["root_technical"]["full_display_name"], full_display_name_root)
        self.assertEqual(spec["group_technical"]["sub_technical"]["full_display_name"], full_display_name_sub_int)
        self.assertEqual(spec["param_no_displ_name"]["full_display_name"], full_name_param)

        # check a display name of a group
        group_displ_name = get_full_display_name_from_spec(spec=spec, flat_spec=flat_spec, key="group_technical")
        self.assertEqual(group_displ_name, full_display_name_group)


class TestAdcmConfigErrorMessages(TestCase):
    def setUp(self) -> None:
        self.prototype = gen_prototype(bundle=gen_bundle(), proto_type="cluster", name="error_messages")
        gen_prototype_config(
            prototype=self.prototype,
            name="root_string",
            field_type="string",
            display_name="Root String",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="root_integer",
            field_type="integer",
            display_name="Root Integer",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="root_patterned_string",
            field_type="string",
            display_name="Root Patterned String",
            limits={"pattern": "^valid$"},
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="not_customizable_root_string",
            field_type="string",
            display_name="Not Customizable Root String",
            group_customization=False,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="required_group",
            field_type="group",
            display_name="Required Group",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="required_group",
            subname="required_string",
            field_type="string",
            display_name="Required String",
            required=True,
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="required_group",
            subname="integer_param",
            field_type="integer",
            display_name="Integer Param",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="required_group",
            subname="list_param",
            field_type="list",
            display_name="List Param",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="required_group",
            subname="patterned_string",
            field_type="string",
            display_name="Patterned String",
            limits={"pattern": "^valid$"},
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="active_group",
            field_type="group",
            display_name="Active Group",
            limits={"activatable": True, "active": True},
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="active_group",
            subname="switch",
            field_type="boolean",
            display_name="Switch",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="sync_group",
            field_type="group",
            group_customization=True,
        )
        gen_prototype_config(
            prototype=self.prototype,
            name="sync_group",
            subname="sync_string",
            field_type="string",
            display_name="Sync String",
            group_customization=True,
        )
        self.valid_config = {
            "root_string": "value",
            "root_integer": 10,
            "root_patterned_string": "valid",
            "not_customizable_root_string": "value",
            "required_group": {
                "required_string": "value",
                "integer_param": 10,
                "list_param": ["first", "second"],
                "patterned_string": "valid",
            },
            "active_group": {"switch": True},
            "sync_group": {"sync_string": "value"},
        }
        self.valid_attr = {"active_group": {"active": True}}
        self.cluster = gen_cluster(
            prototype=self.prototype,
            config=gen_config(config=self.valid_config, attr=self.valid_attr),
        )
        self.config_host_group = gen_group("error_messages_group", self.cluster.pk, "cluster")

    def _assert_config_error_message(self, obj, config, attr, expected_message):
        with self.assertRaises(AdcmEx) as error:
            process_json_config(
                prototype=self.prototype,
                obj=obj,
                new_config=config,
                new_attr=attr,
                current_attr=attr,
            )

        self.assertEqual(error.exception.msg, expected_message)

    def _add_params_in_config(self, group_name: str, **config: Any) -> dict:
        return self.valid_config | {group_name: self.valid_config[group_name] | config}

    def _get_group_keys_with_root_values(self, **root_values: bool) -> dict:
        group_keys, _ = self.config_host_group.create_group_keys(config_spec=self.config_host_group.get_config_spec())
        return group_keys | root_values

    def test_check_config_type_error_messages_with_display_names(self):
        cases = (
            (
                "check tmpl1",
                self._add_params_in_config("required_group", required_string=None),
                "Required Group/Required String",
                'Value of config key "{full_display_name}" is required (cluster "error_messages" 1.0.0)',
            ),
            (
                "check tmpl2",
                self._add_params_in_config("required_group", integer_param="not-integer"),
                "Required Group/Integer Param",
                'Value ("not-integer") of config key "{full_display_name}" should be integer '
                '(cluster "error_messages" 1.0.0)',
            ),
            (
                "check check_str()",
                self._add_params_in_config("required_group", list_param=["first", 2]),
                "Required Group/List Param",
                'Value ("2") of element "1" of config key "{full_display_name}" should be string '
                '(cluster "error_messages" 1.0.0)',
            ),
            (
                "check wrong pattern message",
                self._add_params_in_config("required_group", patterned_string="invalid"),
                "Required Group/Patterned String",
                "The value of {full_display_name} config parameter does not match pattern: ^valid$",
            ),
            (
                "check tmpl2 with root param",
                self.valid_config | {"root_integer": "not-integer"},
                "Root Integer",
                'Value ("not-integer") of config key "{full_display_name}" should be integer '
                '(cluster "error_messages" 1.0.0)',
            ),
            (
                "check wrong pattern message with root param",
                self.valid_config | {"root_patterned_string": "invalid"},
                "Root Patterned String",
                "The value of {full_display_name} config parameter does not match pattern: ^valid$",
            ),
        )

        for case_name, config, full_display_name, expected_message_template in cases:
            with self.subTest(case_name=case_name):
                self._assert_config_error_message(
                    obj=self.cluster,
                    config=config,
                    attr=self.valid_attr,
                    expected_message=expected_message_template.format(full_display_name=full_display_name),
                )

    def test_check_attr_error_messages_with_display_names(self):
        cases = (
            (
                "missing activatable group attribute",
                self.cluster,
                {},
                "Active Group",
                "there isn't `{full_display_name}` group in the `attr`",
            ),
            (
                "invalid active type",
                self.cluster,
                {"active_group": {"active": "yes"}},
                "Active Group",
                "value of key `active` of attribute `{full_display_name}` should be boolean "
                '(cluster "error_messages" 1.0.0)',
            ),
            (
                "attribute key references non-group config key",
                self.cluster,
                {"root_string": {}},
                "Root String",
                'config key `{full_display_name}` is not a group (cluster "error_messages" 1.0.0)',
            ),
            (
                "activatable group attribute value is not a map",
                self.cluster,
                {"active_group": True},
                "Active Group",
                'value of attribute `{full_display_name}` should be a map (cluster "error_messages" 1.0.0)',
            ),
            (
                "not allowed activatable group attribute key",
                self.cluster,
                {"active_group": {"unexpected": True}},
                "Active Group",
                "not allowed key `unexpected` of attribute `{full_display_name}` " '(cluster "error_messages" 1.0.0)',
            ),
            (
                "invalid group_keys group value type",
                self.config_host_group,
                {
                    "active_group": {"active": True},
                    "group_keys": {
                        "required_group": {
                            "value": True,
                            "fields": {},
                        },
                    },
                },
                "Required Group",
                "invalid type `value` field in `{full_display_name}`",
            ),
            (
                "invalid group_keys field type",
                self.config_host_group,
                {
                    "active_group": {"active": True},
                    "group_keys": {
                        "required_group": {
                            "value": None,
                            "fields": {"required_string": "yes"},
                        },
                    },
                },
                "Required Group/Required String",
                "invalid type `{full_display_name}` field in `group_keys`",
            ),
            (
                "invalid root group_keys field type",
                self.config_host_group,
                {
                    "active_group": {"active": True},
                    "group_keys": {"root_string": "yes"},
                },
                "Root String",
                "invalid type `{full_display_name}` field in `group_keys`",
            ),
            (
                "not customizable root field included in group",
                self.config_host_group,
                {
                    "active_group": {"active": True},
                    "group_keys": self._get_group_keys_with_root_values(not_customizable_root_string=True),
                },
                "Not Customizable Root String",
                "the `{full_display_name}` field cannot be included in the group",
            ),
        )

        for case_name, obj, attr, full_display_name, expected_message_template in cases:
            with self.subTest(case_name=case_name):
                self._assert_config_error_message(
                    obj=obj,
                    config=self.valid_config,
                    attr=attr,
                    expected_message=expected_message_template.format(full_display_name=full_display_name),
                )
