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

"""Tests for services and not only"""

import json
import os
from typing import Any

import allure
import coreapi
import pytest
from adcm_client.base import BaseAPIObject
from adcm_client.objects import ADCMClient, Bundle, Cluster, Provider, Service
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import ordered_dict_to_dict, random_string
from jsonschema import validate

# pylint: disable=redefined-outer-name
from tests.library import errorcodes as err

BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")
SCHEMAS = os.path.join(os.path.dirname(__file__), "schemas/")


@pytest.fixture()
def cluster_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(BUNDLES + "cluster_bundle")


@pytest.fixture()
def cluster(cluster_bundle: Bundle) -> Cluster:
    """Create cluster"""
    return cluster_bundle.cluster_create(name=random_string())


@pytest.fixture()
def cluster_with_service(cluster: Cluster) -> tuple[Cluster, Service]:
    """Create cluster and service"""
    service = cluster.service_add()
    return cluster, service


@pytest.fixture()
def provider_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    """Upload provider bundle"""
    return sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")


@pytest.fixture()
def provider(provider_bundle: Bundle) -> Provider:
    """Create provider"""
    return provider_bundle.provider_create(name=random_string())


def _get_prev_config(obj: BaseAPIObject, full=False):
    """Copy of config() method"""

    history_entry = obj._subcall("config", "previous", "list")  # pylint: disable=protected-access
    if full:
        return history_entry

    return history_entry["config"]


def _get_config_history(obj: BaseAPIObject):
    return obj._subcall("config", "history", "list")  # pylint: disable=protected-access


class TestClusterServiceConfig:
    """Tests for service config"""

    def test_create_cluster_service_config(self, cluster_with_service: tuple[Cluster, Service]):
        """Test service config"""
        cfg_json = {
            "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
            "zoo.cfg": {"autopurge.purgeInterval": 30, "dataDir": "/dev/0", "port": 80},
            "required-key": "value",
        }
        _, cluster_svc = cluster_with_service
        with allure.step("Create config"):
            cluster_svc.config_set(cfg_json)
        with allure.step("Check created config"):
            assert cluster_svc.config() == cfg_json

    INVALID_SERVICE_CONFIGS = [
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {"autopurge.purgeInterval": 34},
                "required-key": "110",
            },
            (err.CONFIG_KEY_ERROR, "There is no required subkey"),
            id="without_one_required_sub_key",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 34,
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
            },
            (err.CONFIG_KEY_ERROR, "There is no required key"),
            id="without_one_required_key",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {
                    "autopurge.purgeInterval": "blabla",
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "should be integer"),
            id="int_value_set_to_string",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzHyNTAAIbmzdHAyNTYAAA",
                "float-key": "blah",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 30,
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "should be float"),
            id="float_value_set_to_string",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTY",
                "float-key": 5.7,
                "zoo.cfg": {
                    "autopurge.purgeInterval": 30,
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
                "required-key": 500,
            },
            (err.CONFIG_VALUE_ERROR, "should be string"),
            id="string_value_set_to_int",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAIbmlzdHAyNTYAAA",
                "float-key": 4.5,
                "zoo.cfg": {
                    "autopurge.purgeInterval": 30,
                    "dataDir": "/zookeeper",
                    "port": 500,
                },
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "not in option list"),
            id="parameter_is_not_in_option_list",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 999,
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "should be less than"),
            id="int_value_greater_than_max",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 0,
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "should be more than"),
            id="int_value_less_than_min",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 24,
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
                "float-key": 50.5,
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "should be less than"),
            id="float_value_greater_than_max",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 24,
                    "dataDir": "/zookeeper",
                    "port": 80,
                },
                "float-key": 3.3,
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "should be more than"),
            id="float_value_less_than_min",
        ),
        pytest.param(
            {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA"},
            (err.CONFIG_KEY_ERROR, ""),
            id="without_all_required_params",
        ),
        pytest.param(
            {
                "ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 24,
                    "dataDir": "/zookeeper",
                    "portium": "http",
                },
                "required-key": "value",
            },
            (err.CONFIG_KEY_ERROR, "There is unknown subkey"),
            id="unknown_sub_key",
        ),
        pytest.param(
            {"name": "foo"},
            (err.CONFIG_KEY_ERROR, "There is unknown key"),
            id="unknown_param",
        ),
        pytest.param(
            {
                "ssh-key": {"key": "value"},
                "zoo.cfg": {
                    "autopurge.purgeInterval": "24",
                    "dataDir": "/zookeeper",
                    "port": "http",
                },
            },
            (err.CONFIG_KEY_ERROR, "input config should not have any subkeys"),
            id="unexpected_sub_key",
        ),
        pytest.param(
            {
                "ssh-key": "as32fKj14fT88",
                "zoo.cfg": {
                    "autopurge.purgeInterval": 24,
                    "dataDir": "/zookeeper",
                    "port": {"foo": "bar"},
                },
                "required-key": "value",
            },
            (err.CONFIG_VALUE_ERROR, "should be flat"),
            id="scalar_value_set_to_dict",
        ),
    ]

    @pytest.mark.parametrize(("service_config", "expected_error"), INVALID_SERVICE_CONFIGS)
    def test_should_not_set_invalid_service_config(
        self,
        cluster_with_service: tuple[Cluster, Service],
        service_config: Any,
        expected_error: tuple[err.ADCMError, str],
    ):
        """Test set invalid config for service"""
        _, cluster_svc = cluster_with_service
        adcm_error, expected_msg = expected_error
        with allure.step("Try to set invalid config"):
            allure.attach(json.dumps(service_config), "config.json", allure.attachment_type.JSON)
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                cluster_svc.config_set(service_config)
        with allure.step("Check error"):
            adcm_error.equal(e, expected_msg)

    def test_should_throws_exception_when_havent_previous_config(self, cluster_with_service: tuple[Cluster, Service]):
        """Test error when no previous config is present"""
        _, service = cluster_with_service
        with allure.step("Try to get previous version of the service config"):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                _get_prev_config(service)
        with allure.step("Check error that config version doesn't exist"):
            err.CONFIG_NOT_FOUND.equal(e, "config param doesn't exist")


class TestClusterServiceConfigHistory:
    """Tests for service config history"""

    def test_get_config_from_nonexistent_cluster_service(self, cluster_with_service: tuple[Cluster, Service]):
        """Test get config for nonexistent cluster"""
        _, service = cluster_with_service
        with allure.step(f"Removing service id={service.id}"):
            service.delete()
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            service.config()
        with allure.step("Check error that service doesn't exist"):
            err.CLUSTER_SERVICE_NOT_FOUND.equal(e, "ClusterObject", "does not exist")


class TestClusterConfig:
    """Tests for cluster config"""

    def test_read_default_cluster_config(self, cluster: Cluster):
        """Validate default cluster config by schema"""
        config = cluster.config(full=True)
        config_json = ordered_dict_to_dict(config)
        with allure.step("Load schema"):
            with open(SCHEMAS + "/config_item_schema.json", encoding="utf_8") as file:
                schema = json.load(file)
        with allure.step("Check schema"):
            assert validate(config_json, schema) is None

    def test_create_new_config_version_with_one_req_parameter(self, cluster: Cluster):
        """Test create new cluster config with one parameter"""
        cfg = {"required": 42}
        expected = cluster.config_set(cfg)
        with allure.step("Check new config"):
            assert cluster.config() == expected

    @pytest.mark.xfail(reason="https://tracker.yandex.ru/ADCM-3524")
    def test_create_new_config_version_with_other_parameters(self, cluster: Cluster):
        """Test create new cluster config with many parameters"""
        cfg = {"required": 99, "str-key": random_string()}
        expected = ordered_dict_to_dict(cluster.config())
        expected.update(cfg)
        cluster.config_set(cfg)
        with allure.step("Check new config"):
            assert ordered_dict_to_dict(cluster.config()) == expected

    INVALID_CLUSTER_CONFIGS = [
        pytest.param(
            {"str-key": "value"},
            (err.CONFIG_KEY_ERROR, "There is no required key"),
            id="without_required_key",
        ),
        pytest.param(
            {"option": "bluh", "required": 10},
            (err.CONFIG_VALUE_ERROR, "not in option list"),
            id="param_not_in_option_list",
        ),
        pytest.param(
            {"new_key": "value"},
            (err.CONFIG_KEY_ERROR, "There is unknown key"),
            id="unknown_key",
        ),
        pytest.param(
            {"str-key": "{1bbb}", "option": {"http": "string"}, "sub": {"sub1": "f"}},
            (err.CONFIG_KEY_ERROR, "input config should not have any subkeys"),
            id="map_in_option",
        ),
    ]

    @pytest.mark.parametrize(("cluster_config", "expected_error"), INVALID_CLUSTER_CONFIGS)
    def test_should_not_set_invalid_cluster_config(
        self,
        cluster: Cluster,
        cluster_config: Any,
        expected_error: tuple[err.ADCMError, str],
    ):
        """Invalid cluster config should not be set"""
        adcm_error, expected_msg = expected_error
        with allure.step("Try to set invalid config"):
            allure.attach(json.dumps(cluster_config), "config.json", allure.attachment_type.JSON)
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                cluster.config_set(cluster_config)
        with allure.step("Check error"):
            adcm_error.equal(e, expected_msg)

    def test_get_nonexistent_cluster_config(self, cluster: Cluster):
        """Test get nonexistent cluster config"""
        # we try to get a nonexistant cluster config, test should raise exception
        with allure.step(f"Removing cluster id={cluster.id}"):
            cluster.delete()
        with allure.step("Get cluster config from non existent cluster"):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                cluster.config()
        with allure.step("Check that cluster doesn't exist"):
            err.CLUSTER_NOT_FOUND.equal(e, "Cluster", "does not exist")

    check_types = [
        ("file", "input_file"),
        ("text", "textarea"),
        ("password", "password_phrase"),
    ]

    @pytest.mark.parametrize(("datatype", "name"), check_types)
    def test_verify_that_supported_type_is(self, cluster_bundle: Bundle, datatype, name):
        """Some mysterious type checking test"""
        with allure.step("Check stack config"):
            for item in cluster_bundle.cluster_prototype().config:
                if item["name"] == name:
                    assert item["type"] == datatype

    def test_check_that_file_field_put_correct_data_in_file_inside_docker(self, cluster: Cluster):
        """Another mysterious type checking test"""
        test_data = "lorem ipsum"
        with allure.step("Create config data"):
            config_data = ordered_dict_to_dict(cluster.config())
            config_data["input_file"] = test_data
            config_data["required"] = 42
        with allure.step("Create config history"):
            cluster.config_set(config_data)
        with allure.step("Check file type"):
            run_cluster_action_and_assert_result(cluster=cluster, action="check-file-type")
