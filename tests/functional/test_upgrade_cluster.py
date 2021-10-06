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

"""Tests for cluster upgrade"""
import json
from collections import OrderedDict

import allure
import coreapi
import pytest
from adcm_client.objects import ADCMClient, GroupConfig
from adcm_pytest_plugin.utils import get_data_dir, ordered_dict_to_dict
from allure_commons.types import AttachmentType

from tests.library.errorcodes import UPGRADE_ERROR


def test_upgrade_with_two_clusters(sdk_client_fs: ADCMClient):
    """Upgrade cluster when we have two created clusters from one bundle
    Scenario:
    1. Create two clusters from one bundle
    2. Upload upgradable bundle
    3. Upgrade first cluster
    4. Check that only first cluster was upgraded
    """
    with allure.step('Create two clusters from one bundle'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
        cluster_first = bundle.cluster_create("test")
        cluster_second = bundle.cluster_create("test2")
        service = cluster_first.service_add(name="zookeeper")
    with allure.step('Upgrade first cluster'):
        upgr_cl = cluster_first.upgrade(name='upgrade to 1.6')
        upgr_cl.do()
    with allure.step('Check that only first cluster was upgraded'):
        cluster_first.reread()
        service.reread()
        cluster_second.reread()
        assert cluster_first.prototype().version == '1.6'
        assert service.prototype().version == '3.4.11'
        assert cluster_second.prototype().version == '1.5'


def test_check_prototype(sdk_client_fs: ADCMClient):
    """Check prototype for service and cluster after upgrade"""
    with allure.step('Create test cluster'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
        cluster = bundle.cluster_create("test")
        cl_id_before = cluster.id
        service = cluster.service_add(name="zookeeper")
        serv_id_before = service.id
        cluster_proto_before = cluster.prototype()
        service_proto_before = service.prototype()
    with allure.step('Upgrade test cluster to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check prototype'):
        cluster.reread()
        service.reread()
        cluster_proto_after = cluster.prototype()
        service_proto_after = service.prototype()
        assert cl_id_before == cluster.id
        assert serv_id_before == service.id
        assert cluster_proto_before.id != cluster_proto_after.id
        assert service_proto_before.id != service_proto_after.id


def test_check_config(sdk_client_fs: ADCMClient):
    """Check default service and cluster config fields after upgrade"""
    with allure.step('Create upgradable cluster'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
        cluster_config_before = cluster.config()
        service_config_before = service.config()
    with allure.step('Upgrade cluster to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check config'):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert cluster.prototype().version == '1.6'
        assert service.prototype().version == '3.4.11'
        for variable in cluster_config_before:
            assert cluster_config_before[variable] == cluster_config_after[variable]
        for variable in service_config_before:
            assert service_config_before[variable] == service_config_after[variable]


def test_with_new_default_values(sdk_client_fs: ADCMClient):
    """Upgrade cluster with new default fields. Old and new config values should be presented"""
    with allure.step('Create upgradable cluster with new default values'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        upgr_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_new_default_values'))
        upgr_cluster_prototype = upgr_bundle.cluster_prototype().config
        upgr_service_prototype = upgr_bundle.service_prototype().config
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step('Upgrade cluster with new default fields to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check old and new config'):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        for variable in upgr_cluster_prototype:
            assert variable['value'] == cluster_config_after[variable['name']]
        for variable in upgr_service_prototype:
            assert variable['value'] == service_config_after[variable['name']]


def test_with_new_default_variables(sdk_client_fs: ADCMClient):
    """Upgrade cluster with new default fields. Old and new config variables should be presented"""
    with allure.step('Create upgradable cluster new default variables'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        upgr_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_new_default_variables'))
        upgr_cluster_prototype = upgr_bundle.cluster_prototype().config
        upgr_service_prototype = upgr_bundle.service_prototype().config
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step('Upgrade cluster with new default variables to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check old and new config'):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        for variable in upgr_cluster_prototype:
            assert variable['name'] in cluster_config_after.keys()
        for variable in upgr_service_prototype:
            assert variable['name'] in service_config_after.keys()


def test_decrease_config(sdk_client_fs: ADCMClient):
    """Upgrade cluster with config without old values in config. Deleted lines not presented"""
    with allure.step('Create upgradable cluster with decrease variables'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_decrease_variables'))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
        cluster_config_before = cluster.config()
        service_config_before = service.config()
    with allure.step('Upgrade cluster with config without old values in config to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check that deleted lines not presented'):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert len(cluster_config_after.keys()) == 1
        assert len(service_config_after.keys()) == 1
        for key in cluster_config_after:
            assert cluster_config_before[key] == cluster_config_after[key]
        for key in service_config_after:
            assert service_config_before[key] == service_config_after[key]


def test_changed_variable_type(sdk_client_fs: ADCMClient):
    """Change config variable type for upgrade"""
    with allure.step('Create upgradable cluster with change variable type'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_change_variable_type'))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
        cluster_config_before = cluster.config()
        service_config_before = service.config()
    with allure.step('Upgrade cluster with change variable type to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check changed variable type'):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert isinstance(cluster_config_after['required'], str)
        assert isinstance(service_config_after['required_service'], str)
        assert int(cluster_config_after['required']) == cluster_config_before['required']
        assert int(service_config_after['required_service']) == service_config_before['required_service']


def test_multiple_upgrade_bundles(sdk_client_fs: ADCMClient):
    """Upgrade cluster multiple time from version to another"""
    with allure.step('Create upgradable cluster for multiple upgrade'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
        cluster = bundle.cluster_create("test")
    with allure.step('Upgrade cluster multiple time from version to another to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Upgrade second time cluster to 2'):
        cluster.reread()
        upgr = cluster.upgrade(name='upgrade 2')
        upgr.do()
    with allure.step('Check upgraded cluster'):
        cluster.reread()
        assert cluster.state == 'upgradated'


def test_change_config(sdk_client_fs: ADCMClient):
    """Upgrade cluster with other config"""
    with allure.step('Create upgradable cluster with new change values'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_new_change_values'))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step('Set cluster and service config'):
        cluster_config_before = cluster.config()
        service_config_before = service.config()
        cluster_config_before['required'] = 25
        cluster_config_before['int_key'] = 245
        cluster_config_before['str-key'] = "new_value"
        service_config_before['required_service'] = 20
        service_config_before['int_key_service'] = 333
        cluster.config_set(cluster_config_before)
        service.config_set(service_config_before)
    with allure.step('Upgrade cluster with new change values to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check upgraded cluster and service'):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert len(cluster_config_before.keys()) == len(cluster_config_after.keys())
        for key in cluster_config_before:
            assert cluster_config_before[key] == cluster_config_after[key]
        for key in service_config_before:
            assert service_config_before[key] == service_config_after[key]


@allure.issue("https://arenadata.atlassian.net/browse/ADCM-1971")
def test_upgrade_cluster_with_config_groups(sdk_client_fs):
    """Test upgrade cluster config groups"""
    with allure.step('Create cluster with different groups on config'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_with_groups'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_with_groups'))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step('Upgrade cluster with new change values to 1.6'):
        upgrade = cluster.upgrade(name='upgrade to 1.6')
        upgrade.do()
    with allure.step('Assert that configs save success after upgrade'):
        cluster.config_set(
            {
                **cluster.config(),
                "activatable_group_with_ro": {"readonly-key": "value"},
                "activatable_group": {"required": 10, "writable-key": "value"},
            }
        )
        service.config_set(
            {
                **cluster.config(),
                "activatable_group_with_ro": {"readonly-key": "value"},
                "activatable_group": {"required": 10, "writable-key": "value"},
            }
        )


def test_cannot_upgrade_with_state(sdk_client_fs: ADCMClient):
    """Test upgrade should not be available ant stater"""
    with allure.step('Create upgradable cluster with unsupported state'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_unsupported_state'))
        cluster = bundle.cluster_create("test")
    with allure.step('Upgrade cluster to 1.6 and then to 2'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
        cluster.reread()
        upgr = cluster.upgrade(name='upgrade 2')
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            upgr.do()
    with allure.step('Check error: cluster state is not in available states list'):
        UPGRADE_ERROR.equal(e, 'cluster state', 'is not in available states list')


###############################
# Upgrade with group configs
###############################


def _update_config_and_attr_for_new_field_test(config: OrderedDict, attr: OrderedDict):
    config["new_float"] = 0.3
    config["new_boolean"] = False
    config["new_integer"] = 34
    config["new_string"] = "string_new"
    config["new_list"] = ["/dev/sda", "/dev/rda"]
    config["new_file"] = "other file content\n"
    config["new_option"] = "NOTTOBE"
    config["new_text"] = "text_new"
    config["new_group"] = {}
    config["new_group"]["new_port"] = 9201
    config["new_structure"] = [
        OrderedDict({"name": "John", "surname": "Doe"}),
        OrderedDict({"name": "Allice", "surname": "Cooper"}),
    ]
    config["new_map"] = {"time": "12", "range": "super long"}

    attr["new_group"] = {}
    attr["new_group"]["active"] = True

    attr["group_keys"]["new_float"] = False
    attr["group_keys"]["new_boolean"] = False
    attr["group_keys"]["new_integer"] = False
    attr["group_keys"]["new_string"] = False
    attr["group_keys"]["new_list"] = False
    attr["group_keys"]["new_file"] = False
    attr["group_keys"]["new_option"] = False
    attr["group_keys"]["new_text"] = False
    attr["group_keys"]["new_group"] = {}
    attr["group_keys"]["new_group"]["new_port"] = False
    attr["group_keys"]["new_structure"] = False
    attr["group_keys"]["new_map"] = False

    attr["custom_group_keys"]["new_float"] = True
    attr["custom_group_keys"]["new_boolean"] = True
    attr["custom_group_keys"]["new_integer"] = True
    attr["custom_group_keys"]["new_string"] = True
    attr["custom_group_keys"]["new_list"] = True
    attr["custom_group_keys"]["new_file"] = True
    attr["custom_group_keys"]["new_option"] = True
    attr["custom_group_keys"]["new_text"] = True
    attr["custom_group_keys"]["new_group"] = {}
    attr["custom_group_keys"]["new_group"]["new_port"] = True
    attr["custom_group_keys"]["new_structure"] = True
    attr["custom_group_keys"]["new_map"] = True
    return config, attr


def _update_config_and_attr_for_new_default_value_test(config: OrderedDict, attr: OrderedDict):
    config["float"] = 0.2
    config["boolean"] = False
    config["integer"] = 25
    config["string"] = "new_string"
    config["list"] = ["/dev/fdisk0s1", "/dev/fdisk0s2", "/dev/fdisk0s3"]
    config["file"] = "other file content\n"
    config["option"] = "WEEKLY"
    config["text"] = "new_text"
    config["group"]["port"] = 9201
    config["group"]["transport_port"] = 9301
    config["structure"] = [OrderedDict({"code": 1, "country": "Test1_new"})]
    config["map"] = {"age": "25", "name": "Jane", "sex": "f"}
    return config, attr


def _update_config_and_attr_for_removed_field_test(config: OrderedDict, attr: OrderedDict):
    _, _ = config, attr
    config = {"float": 0.1}
    attr = {"group_keys": {"float": False}, "custom_group_keys": {"float": True}}
    return config, attr


class TestUpgradeWithGroupConfigs:  # pylint:disable=too-many-locals
    """Tests for cluster and provider upgrades with group configs"""

    @pytest.mark.parametrize(
        ("bundle_name", "update_func"),
        [
            ("upgradable_cluster_with_group_configs_with_new_fields", _update_config_and_attr_for_new_field_test),
            (
                "upgradable_cluster_with_group_configs_with_new_default_value",
                _update_config_and_attr_for_new_default_value_test,
            ),
            (
                "upgradable_cluster_with_group_configs_with_removed_field",
                _update_config_and_attr_for_removed_field_test,
            ),
        ],
    )
    def test_upgrade_cluster_with_group_configs(self, sdk_client_fs, bundle_name, update_func):
        """
        Test upgrade cluster with group configs enabled
        - Upload cluster bundle
        - Create cluster and add service
        - Create group configs for cluster, service, and component
        - Update cluster to the new version with new parameter/default value or removed parameter in config
        - Assert that new parameter/default value or removed parameter is presented/absent in all group configs
        """
        with allure.step('Upload cluster bundle'):
            cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_with_group_configs'))
        with allure.step('Create cluster and add service'):
            cluster = cluster_bundle.cluster_create("test")
            service = cluster.service_add(name="test_service")
            component = service.component(name="test_component")
        with allure.step("Create group configs for cluster, service, and component"):
            cluster_group_config = cluster.group_config_create(name="cluster_config_group")
            cluster_gc_ref_config, cluster_gc_ref_attr = self._get_config_and_attr(cluster_group_config)
            service_group_config = service.group_config_create(name="service_config_group")
            service_gc_ref_config, service_gc_ref_attr = self._get_config_and_attr(service_group_config)
            component_group_config = component.group_config_create(name="component_config_group")
            component_gc_ref_config, component_gc_ref_attr = self._get_config_and_attr(component_group_config)
        with allure.step('Upgrade cluster to new version with new fields in config'):
            sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_name))
            upgrade = cluster.upgrade(name='upgrade to 1.6')
            upgrade.do()
        with allure.step('Assert that group configs have been updated'):
            cluster_gc_ref_config, cluster_gc_ref_attr = update_func(cluster_gc_ref_config, cluster_gc_ref_attr)
            cluster_gc_new_config, cluster_gc_new_attr = self._get_config_and_attr(cluster_group_config)
            self._assert_configs(
                obj_type="cluster", actual_config=cluster_gc_new_config, expected_config=cluster_gc_ref_config
            )
            self._assert_attr(obj_type="cluster", actual_attr=cluster_gc_new_attr, expected_attr=cluster_gc_ref_attr)
            service_gc_ref_config, service_gc_ref_attr = update_func(service_gc_ref_config, service_gc_ref_attr)
            service_gc_new_config, service_gc_new_attr = self._get_config_and_attr(service_group_config)
            self._assert_configs(
                obj_type="service", actual_config=service_gc_new_config, expected_config=service_gc_ref_config
            )
            self._assert_attr(obj_type="service", actual_attr=service_gc_new_attr, expected_attr=service_gc_ref_attr)
            component_gc_ref_config, component_gc_ref_attr = update_func(component_gc_ref_config, component_gc_ref_attr)
            component_gc_new_config, component_gc_new_attr = self._get_config_and_attr(component_group_config)
            self._assert_configs(
                obj_type="component", actual_config=component_gc_new_config, expected_config=component_gc_ref_config
            )
            self._assert_attr(
                obj_type="component", actual_attr=component_gc_new_attr, expected_attr=component_gc_ref_attr
            )

    @pytest.mark.parametrize(
        ("bundle_name", "update_func"),
        [
            ("upgradable_provider_with_group_configs_with_new_fields", _update_config_and_attr_for_new_field_test),
            (
                "upgradable_provider_with_group_configs_with_new_default_value",
                _update_config_and_attr_for_new_default_value_test,
            ),
            (
                "upgradable_provider_with_group_configs_with_removed_field",
                _update_config_and_attr_for_removed_field_test,
            ),
        ],
    )
    def test_upgrade_provider_with_group_configs_add_param(self, sdk_client_fs, bundle_name, update_func):
        """
        Test upgrade provider with group configs enabled
        - Upload provider bundle
        - Create provider
        - Create group configs for provider
        - Update provider to the new version with new parameter in config
        - Assert that new parameter is presented in all group configs
        """
        with allure.step('Upload provider bundle'):
            provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'provider_with_group_configs'))
        with allure.step('Create provider'):
            provider = provider_bundle.provider_create("test")
        with allure.step("Create group config for provider"):
            provider_group_config = provider.group_config_create(name="provider_config_group")
            provider_gc_ref_config, provider_gc_ref_attr = self._get_config_and_attr(provider_group_config)
        with allure.step('Upgrade provider to new version with new fields in config'):
            sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_name))
            upgrade = provider.upgrade(name='upgrade to 1.6')
            upgrade.do()
        with allure.step('Assert that group configs have been updated'):
            provider_gc_ref_config, provider_gc_ref_attr = update_func(provider_gc_ref_config, provider_gc_ref_attr)
            provider_gc_new_config, provider_gc_new_attr = self._get_config_and_attr(provider_group_config)
            self._assert_configs(
                obj_type="provider", actual_config=provider_gc_new_config, expected_config=provider_gc_ref_config
            )
            self._assert_attr(obj_type="provider", actual_attr=provider_gc_new_attr, expected_attr=provider_gc_ref_attr)

    @staticmethod
    def _get_config_and_attr(obj: GroupConfig):
        full_conf = obj.config(full=True)
        return full_conf["config"], full_conf["attr"]

    @staticmethod
    @allure.step("Assert that group configs has been updated for {obj_type}")
    def _assert_configs(obj_type: str, actual_config: OrderedDict, expected_config: OrderedDict):
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
            raise AssertionError(f"Config for {obj_type} group is not as expected. See attachments for details")

    @staticmethod
    @allure.step("Assert that group configs has been updated for {obj_type}")
    def _assert_attr(obj_type: str, actual_attr: OrderedDict, expected_attr: OrderedDict):
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
            raise AssertionError(f"Attr for {obj_type} group is not as expected. See attachments for details")
