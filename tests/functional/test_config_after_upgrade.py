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

"""Tests for cluster and provider configs after upgrade"""
import json
from collections import OrderedDict
from typing import Callable, Tuple, Union

import allure
import pytest
from adcm_client.objects import GroupConfig
from adcm_pytest_plugin.utils import get_data_dir, ordered_dict_to_dict
from allure_commons.types import AttachmentType

from tests.functional.plugin_utils import AnyADCMObject

###############################
# Tools
###############################


def _update_config_and_attr_for_new_field_test(
    config: OrderedDict, attr: OrderedDict, group_config=False
) -> Tuple[dict, dict]:
    config["new_float"] = 0.3
    config["new_boolean"] = False
    config["new_integer"] = 34
    config["new_string"] = "string_new"
    config["new_list"] = ["/dev/sda", "/dev/rda"]
    config["new_file"] = "other file content\n"
    config["new_option"] = "NOTTOBE"
    config["new_text"] = "text_new"
    config["group"]["new_text"] = "text_new"
    del config["group"]["transport_port"]
    config["new_group"] = {"new_port": 9201}
    config["new_structure"] = [
        OrderedDict({"name": "John", "surname": "Doe"}),
        OrderedDict({"name": "Allice", "surname": "Cooper"}),
    ]
    config["new_map"] = {"time": "12", "range": "super long"}
    config["new_json"] = {"key": "value", "integer": 52}

    attr["new_group"] = {"active": True}

    if group_config:
        attr["group_keys"]["new_float"] = False
        attr["group_keys"]["new_boolean"] = False
        attr["group_keys"]["new_integer"] = False
        attr["group_keys"]["new_string"] = False
        attr["group_keys"]["new_list"] = False
        attr["group_keys"]["new_file"] = False
        attr["group_keys"]["new_option"] = False
        attr["group_keys"]["new_text"] = False
        attr["group_keys"]["group"]["fields"]["new_text"] = False
        del attr["group_keys"]["group"]["fields"]["transport_port"]
        attr["group_keys"]["new_group"] = {"value": False, "fields": {"new_port": False}}
        attr["group_keys"]["new_structure"] = False
        attr["group_keys"]["new_map"] = False
        attr["group_keys"]["new_json"] = False

        attr["custom_group_keys"]["new_float"] = True
        attr["custom_group_keys"]["new_boolean"] = True
        attr["custom_group_keys"]["new_integer"] = True
        attr["custom_group_keys"]["new_string"] = True
        attr["custom_group_keys"]["new_list"] = True
        attr["custom_group_keys"]["new_file"] = True
        attr["custom_group_keys"]["new_option"] = True
        attr["custom_group_keys"]["new_text"] = True
        attr["custom_group_keys"]["group"]["fields"]["new_text"] = True
        del attr["custom_group_keys"]["group"]["fields"]["transport_port"]
        attr["custom_group_keys"]["new_group"] = {"value": True, "fields": {"new_port": True}}
        attr["custom_group_keys"]["new_structure"] = True
        attr["custom_group_keys"]["new_map"] = True
        attr["custom_group_keys"]["new_json"] = True
    return config, attr


def _update_config_and_attr_for_new_default_value_test(
    config: OrderedDict, attr: OrderedDict, group_config=False
) -> Tuple[dict, dict]:
    config["float"] = 0.2
    config["boolean"] = False
    config["integer"] = 25
    config["string"] = "new_string"
    config["list"] = ["/dev/fdisk0s1", "/dev/fdisk0s2", "/dev/fdisk0s3"]
    config["file"] = "other file content\n"
    config["option"] = "WEEKLY"
    config["text"] = "new_text"
    config["group"] = {"port": 9201, "transport_port": 9301}
    config["structure"] = [OrderedDict({"code": 1, "country": "Test1_new"})]
    config["map"] = {"age": "25", "name": "Jane", "sex": "f"}
    config["json"] = {"key": "initial value", "float": 3.25}
    _ = group_config
    return config, attr


def _update_config_and_attr_for_changed_types(
    config: OrderedDict, attr: OrderedDict, group_config=False
) -> Tuple[dict, dict]:
    config["boolean"] = 0.1
    config["float"] = True
    config["string"] = 16
    config["integer"] = "string"
    config["file"] = ["/dev/rdisk0s1", "/dev/rdisk0s2", "/dev/rdisk0s3"]
    config["list"] = "file content\n"
    config["text"] = "DAILY"
    config["option"] = "text"
    config["structure"] = {"port": 9200, "transport_port": 9300}
    config["group"] = [
        OrderedDict({"code": 1, "country": "Test1"}),
        OrderedDict({"code": 2, "country": "Test2"}),
    ]

    attr["structure"] = {"active": True}
    del attr["group"]

    if group_config:
        attr["group_keys"]["structure"] = {"port": False, "transport_port": False}
        attr["group_keys"]["group"] = False

        attr["custom_group_keys"]["structure"] = {"port": True, "transport_port": True}
        attr["custom_group_keys"]["group"] = True

    return config, attr


def _update_config_and_attr_for_removed_field_test(
    config: OrderedDict, attr: OrderedDict, group_config=False
) -> Tuple[dict, dict]:
    _, _ = config, attr
    attr = {}
    config = {"float": 0.1}
    if group_config:
        attr = {"group_keys": {"float": False}, "custom_group_keys": {"float": True}}
    return config, attr


def _update_config_and_attr_for_changed_group_customisation_test(
    config: OrderedDict, attr: OrderedDict, group_config=False
) -> Tuple[dict, dict]:
    if group_config:
        attr["custom_group_keys"]["boolean"] = False
        attr["custom_group_keys"]["password"] = False
        attr["custom_group_keys"]["list"] = False
        attr["custom_group_keys"]["option"] = False
        attr["custom_group_keys"]["group"] = {
            "value": False,
            "fields": {"port": False, "transport_port": False},
        }
        attr["custom_group_keys"]["map"] = False
        attr["custom_group_keys"]["json"] = False
        attr["custom_group_keys"]["secrettext"] = True

    return config, attr


@allure.step("Assert that configs has been updated for {obj_type}")
def _assert_configs(obj_type: str, actual_config: OrderedDict, expected_config: OrderedDict, group_config=False):
    actual_config = ordered_dict_to_dict(actual_config)
    expected_config = ordered_dict_to_dict(expected_config)
    if actual_config != expected_config:
        allure.attach(
            json.dumps(expected_config, indent=2),
            name="Expected config",
            attachment_type=AttachmentType.JSON,
        )
        allure.attach(
            json.dumps(actual_config, indent=2),
            name="Actual config",
            attachment_type=AttachmentType.JSON,
        )
        raise AssertionError(
            f"Config of {obj_type} {'group config' if group_config else 'config'} "
            "is not as expected. See attachments for details"
        )


@allure.step("Assert that attrs has been updated for {obj_type}")
def _assert_attr(obj_type: str, actual_attr: OrderedDict, expected_attr: OrderedDict, group_config=False):
    actual_attr = ordered_dict_to_dict(actual_attr)
    expected_attr = ordered_dict_to_dict(expected_attr)
    if actual_attr != expected_attr:
        allure.attach(
            json.dumps(expected_attr, indent=2),
            name="Expected attr",
            attachment_type=AttachmentType.JSON,
        )
        allure.attach(
            json.dumps(actual_attr, indent=2),
            name="Actual attr",
            attachment_type=AttachmentType.JSON,
        )
        raise AssertionError(
            f"Attr of {obj_type} {'group config' if group_config else 'config'} "
            "is not as expected. See attachments for details"
        )


def _get_config_and_attr(obj: Union[GroupConfig, AnyADCMObject]):
    full_conf = obj.config(full=True)
    return full_conf["config"], full_conf["attr"]


##################################
# Upgrade with ordinary configs
##################################


class TestUpgradeWithConfigs:
    """Tests for cluster and provider upgrades with ordinary configs"""

    @pytest.mark.parametrize(
        ("bundle_name", "update_func"),
        [
            pytest.param(
                "cluster_for_upgrade_with_configs_with_new_fields",
                _update_config_and_attr_for_new_field_test,
                id="new_fields",
            ),
            pytest.param(
                "cluster_for_upgrade_with_configs_with_new_default_value",
                _update_config_and_attr_for_new_default_value_test,
                id="new_default_values",
            ),
            pytest.param(
                "cluster_for_upgrade_with_configs_with_removed_field",
                _update_config_and_attr_for_removed_field_test,
                id="removed_fields",
            ),
            pytest.param(
                "cluster_for_upgrade_with_configs_with_changed_types",
                _update_config_and_attr_for_changed_types,
                id="changed_types",
            ),
        ],
    )
    def test_upgrade_cluster_with_ordinary_configs(self, sdk_client_fs, bundle_name, update_func: Callable):
        """
        Test upgrade cluster with ordinary configs
        - Upload cluster bundle
        - Create cluster and add service
        - Update cluster to the new version with new parameter/default value or removed parameter in config
        - Assert that new parameter/default value or removed parameter is presented/absent in configs
        """
        with allure.step("Upload cluster bundle"):
            cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_configs"))
        with allure.step("Create cluster and add service"):
            cluster = cluster_bundle.cluster_create("test")
            service = cluster.service_add(name="test_service")
            component = service.component(name="test_component")
            cluster_ref_config_and_attr = _get_config_and_attr(cluster)
            service_ref_config_and_attr = _get_config_and_attr(service)
            component_ref_config_and_attr = _get_config_and_attr(component)
        with allure.step("Upgrade cluster to new version with new fields in config"):
            sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_name))
            upgrade = cluster.upgrade(name="upgrade to 1.6")
            upgrade.do()
        with allure.step("Assert that configs have been updated"):
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=cluster_ref_config_and_attr,
                obj=cluster,
            )
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=service_ref_config_and_attr,
                obj=service,
            )
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=component_ref_config_and_attr,
                obj=component,
            )

    @pytest.mark.parametrize(
        ("bundle_name", "update_func"),
        [
            pytest.param(
                "provider_for_upgrade_with_configs_with_new_fields",
                _update_config_and_attr_for_new_field_test,
                id="new_fields",
            ),
            pytest.param(
                "provider_for_upgrade_with_configs_with_new_default_value",
                _update_config_and_attr_for_new_default_value_test,
                id="new_default_values",
            ),
            pytest.param(
                "provider_for_upgrade_with_configs_with_removed_field",
                _update_config_and_attr_for_removed_field_test,
                id="removed_fields",
            ),
            pytest.param(
                "provider_for_upgrade_with_configs_with_changed_types",
                _update_config_and_attr_for_changed_types,
                id="changed_types",
            ),
        ],
    )
    def test_upgrade_provider_with_ordinary_configs(self, sdk_client_fs, bundle_name, update_func: Callable):
        """
        Test upgrade provider with ordinary configs
        - Upload provider bundle
        - Create provider
        - Update provider to the new version with new parameter/default value or removed parameter in config
        - Assert that new parameter/default value or removed parameter is presented/absent in config
        """
        with allure.step("Upload provider bundle"):
            provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider_with_configs"))
        with allure.step("Create provider"):
            provider = provider_bundle.provider_create("test")
            provider_ref_config_and_attr = _get_config_and_attr(provider)
        with allure.step("Upgrade provider to new version with new fields in config"):
            sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_name))
            upgrade = provider.upgrade(name="upgrade to 1.6")
            upgrade.do()
        with allure.step("Assert that configs have been updated"):
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=provider_ref_config_and_attr,
                obj=provider,
            )

    @staticmethod
    def _update_and_assert_config(update_func: Callable, ref_config_and_attr, obj: AnyADCMObject):
        ref_config, ref_attr = update_func(*ref_config_and_attr, group_config=False)
        new_config, new_attr = _get_config_and_attr(obj)
        _assert_configs(
            obj_type=obj.__class__.__name__,
            actual_config=new_config,
            expected_config=ref_config,
            group_config=False,
        )
        _assert_attr(
            obj_type=obj.__class__.__name__,
            actual_attr=new_attr,
            expected_attr=ref_attr,
            group_config=False,
        )


##################################
# Upgrade with group configs
##################################


class TestUpgradeWithGroupConfigs:
    """Tests for cluster and provider upgrades with group configs"""

    @pytest.mark.parametrize(
        ("bundle_name", "update_func"),
        [
            pytest.param(
                "cluster_for_upgrade_with_group_configs_with_new_fields",
                _update_config_and_attr_for_new_field_test,
                id="new_fields",
            ),
            pytest.param(
                "cluster_for_upgrade_with_group_configs_with_new_default_value",
                _update_config_and_attr_for_new_default_value_test,
                id="new_default_values",
            ),
            pytest.param(
                "cluster_for_upgrade_with_group_configs_with_removed_field",
                _update_config_and_attr_for_removed_field_test,
                id="removed_fields",
            ),
            pytest.param(
                "cluster_for_upgrade_with_group_configs_with_changed_types",
                _update_config_and_attr_for_changed_types,
                id="changed_types",
                marks=pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2172"),
            ),
            pytest.param(
                "cluster_for_upgrade_with_group_configs_with_changed_group_customisation",
                _update_config_and_attr_for_changed_group_customisation_test,
                id="changed_group_customisation",
            ),
        ],
    )
    def test_upgrade_cluster_with_group_configs(self, sdk_client_fs, bundle_name, update_func: Callable):
        """
        Test upgrade cluster with group configs enabled
        - Upload cluster bundle
        - Create cluster and add service
        - Create group configs for cluster, service, and component
        - Update cluster to the new version with new parameter/default value or removed parameter in config
        - Assert that new parameter/default value or removed parameter is presented/absent in all group configs
        """
        with allure.step("Upload cluster bundle"):
            cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_group_configs"))
        with allure.step("Create cluster and add service"):
            cluster = cluster_bundle.cluster_create("test")
            service = cluster.service_add(name="test_service")
            component = service.component(name="test_component")
        with allure.step("Create group configs for cluster, service, and component"):
            cluster_group_config = cluster.group_config_create(name="cluster_config_group")
            cluster_gc_ref_config_and_attr = _get_config_and_attr(cluster_group_config)
            service_group_config = service.group_config_create(name="service_config_group")
            service_gc_ref_config_and_attr = _get_config_and_attr(service_group_config)
            component_group_config = component.group_config_create(name="component_config_group")
            component_gc_ref_config_and_attr = _get_config_and_attr(component_group_config)
        with allure.step("Upgrade cluster to new version with new fields in config"):
            sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_name))
            upgrade = cluster.upgrade(name="upgrade to 1.6")
            upgrade.do()
        with allure.step("Assert that group configs have been updated"):
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=cluster_gc_ref_config_and_attr,
                group_config=cluster_group_config,
            )
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=service_gc_ref_config_and_attr,
                group_config=service_group_config,
            )
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=component_gc_ref_config_and_attr,
                group_config=component_group_config,
            )

    @pytest.mark.parametrize(
        ("bundle_name", "update_func"),
        [
            pytest.param(
                "provider_for_upgrade_with_group_configs_with_new_fields",
                _update_config_and_attr_for_new_field_test,
                id="new_fields",
            ),
            pytest.param(
                "provider_for_upgrade_with_group_configs_with_new_default_value",
                _update_config_and_attr_for_new_default_value_test,
                id="new_default_values",
            ),
            pytest.param(
                "provider_for_upgrade_with_group_configs_with_removed_field",
                _update_config_and_attr_for_removed_field_test,
                id="removed_fields",
            ),
            pytest.param(
                "provider_for_upgrade_with_group_configs_with_changed_types",
                _update_config_and_attr_for_changed_types,
                id="changed_types",
                marks=pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2172"),
            ),
            pytest.param(
                "provider_for_upgrade_with_group_configs_with_changed_group_customisation",
                _update_config_and_attr_for_changed_group_customisation_test,
                id="changed_group_customisation",
            ),
        ],
    )
    def test_upgrade_provider_with_group_configs(self, sdk_client_fs, bundle_name, update_func: Callable):
        """
        Test upgrade provider with group configs enabled
        - Upload provider bundle
        - Create provider
        - Create group config for provider
        - Update provider to the new version with new parameter/default value or removed parameter in config
        - Assert that new parameter/default value or removed parameter is presented/absent in group config
        """
        with allure.step("Upload provider bundle"):
            provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider_with_group_configs"))
        with allure.step("Create provider"):
            provider = provider_bundle.provider_create("test")
        with allure.step("Create group config for provider"):
            provider_group_config = provider.group_config_create(name="provider_config_group")
            provider_gc_ref_config_and_attr = _get_config_and_attr(provider_group_config)
        with allure.step("Upgrade provider to new version with new fields in config"):
            sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_name))
            upgrade = provider.upgrade(name="upgrade to 1.6")
            upgrade.do()
        with allure.step("Assert that group configs have been updated"):
            self._update_and_assert_config(
                update_func=update_func,
                ref_config_and_attr=provider_gc_ref_config_and_attr,
                group_config=provider_group_config,
            )

    @staticmethod
    def _update_and_assert_config(update_func: Callable, ref_config_and_attr, group_config: GroupConfig):
        ref_config, ref_attr = update_func(*ref_config_and_attr, group_config=True)
        new_config, new_attr = _get_config_and_attr(group_config)
        _assert_configs(
            obj_type=group_config.object_type,
            actual_config=new_config,
            expected_config=ref_config,
            group_config=True,
        )
        _assert_attr(
            obj_type=group_config.object_type,
            actual_attr=new_attr,
            expected_attr=ref_attr,
            group_config=True,
        )
