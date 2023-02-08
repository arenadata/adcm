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

"""Tests for /stack related objects ans stuff"""

import json
from typing import List, Tuple

import allure
import coreapi
import pytest
from _pytest.mark import ParameterSet
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils
from jsonschema import validate

from tests.library import errorcodes
from tests.library.errorcodes import ADCMError

SCHEMAS = utils.get_data_dir(__file__, "schemas/")


def test_service_wo_name(sdk_client_fs: ADCMClient):
    """Test upload service without name"""
    stack_dir = utils.get_data_dir(__file__, "service_wo_name")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: no name in service definition"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'There is no required key "name" in map.')


def test_service_wo_version(sdk_client_fs: ADCMClient):
    """Test upload service without version"""
    stack_dir = utils.get_data_dir(__file__, "service_wo_version")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: no version in service"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'There is no required key "version" in map.')


def test_service_wo_actions(sdk_client_fs: ADCMClient):
    """Test upload service without action"""
    stack_dir = utils.get_data_dir(__file__, "service_wo_action")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Get service without actions"):
        service_prototype = sdk_client_fs.service_prototype()._data  # pylint: disable=protected-access
        with open(SCHEMAS + "/stack_list_item_schema.json", encoding="utf_8") as file:
            schema = json.load(file)
    with allure.step("Check service"):
        assert validate(service_prototype, schema) is None


def test_cluster_proto_wo_actions(sdk_client_fs: ADCMClient):
    """Test validate cluster proto without action"""
    stack_dir = utils.get_data_dir(__file__, "cluster_proto_wo_actions")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Get cluster without actions"):
        cluster_prototype = sdk_client_fs.cluster_prototype()._data  # pylint: disable=protected-access
        with open(SCHEMAS + "/stack_list_item_schema.json", encoding="utf_8") as file:
            schema = json.load(file)
    with allure.step("Check cluster"):
        assert validate(cluster_prototype, schema) is None


def test_host_proto_wo_actions(sdk_client_fs: ADCMClient):
    """Test validate host proto without action"""
    stack_dir = utils.get_data_dir(__file__, "host_proto_wo_action")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Get host without actions"):
        host_prototype = sdk_client_fs.host_prototype()._data  # pylint: disable=protected-access
        with open(SCHEMAS + "/stack_list_item_schema.json", encoding="utf_8") as file:
            schema = json.load(file)
    with allure.step("Check host prototype"):
        assert validate(host_prototype, schema) is None


def test_service_wo_type(sdk_client_fs: ADCMClient):
    """Test upload service without type"""
    stack_dir = utils.get_data_dir(__file__, "service_wo_type")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: No type in object definition"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'There is no key "type" in map.')


def test_service_unknown_type(sdk_client_fs: ADCMClient):
    """Test upload service with unknown type"""
    stack_dir = utils.get_data_dir(__file__, "service_unknown_type")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: Unknown type"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'Value "unknown" is not allowed')


def test_stack_hasnt_script_mandatory_key(sdk_client_fs: ADCMClient):
    """Test upload bundle with action without script field"""
    stack_dir = utils.get_data_dir(__file__, "script_mandatory_key")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: has no mandatory"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'There is no required key "script" in map.')


def test_stack_hasnt_scripttype_mandatory_key(sdk_client_fs: ADCMClient):
    """Test upload bundle with action without script_type field"""
    stack_dir = utils.get_data_dir(__file__, "scripttype_mandatory_key")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: has no mandatory"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'There is no required key "script_type" in map.')


def test_playbook_path(sdk_client_fs: ADCMClient):
    """Test upload bundle with action with playbook path"""
    stack_dir = utils.get_data_dir(__file__, "playbook_path_test")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check service prototype list"):
        assert sdk_client_fs.service_prototype_list() is not None


def test_empty_default_config_value(sdk_client_fs: ADCMClient):
    """Test upload bundle with empty default config value"""
    stack_dir = utils.get_data_dir(__file__, "empty_default_config_value")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check service prototype list"):
        assert sdk_client_fs.service_prototype_list() is not None


def test_load_stack_w_empty_config_field(sdk_client_fs: ADCMClient):
    """Test upload bundle with empty config field"""
    stack_dir = utils.get_data_dir(__file__, "empty_config_field")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: config field should not be empty"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'None of the variants for rule "config_obj" match')


def test_shouldn_load_config_with_wrong_name(sdk_client_fs: ADCMClient):
    """Test should not load bundle with wrong config name"""
    stack_dir = utils.get_data_dir(__file__, "parsing_scalar_wrong_name")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: Config key is incorrect"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'There is no key "type" in map')


def test_load_stack_wo_type_in_config_key(sdk_client_fs: ADCMClient):
    """Test upload bundle without type field"""
    stack_dir = utils.get_data_dir(__file__, "no_type_in_config_key")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: No type in config key"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'There is no key "type" in map.')


def test_when_config_has_two_identical_service_proto(sdk_client_fs: ADCMClient):
    """Test upload bundle without two identical services"""
    stack_dir = utils.get_data_dir(__file__, "two_identical_services")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: Duplicate definition of service"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, "Duplicate definition of service")


@pytest.mark.parametrize("entity", ["host", "provider"])
def test_config_has_one_definition_and_two_diff_types(sdk_client_fs: ADCMClient, entity):
    """Test upload bundle with dsl and type mismatch"""
    name = "cluster_has_a_" + entity + "_definition"
    stack_dir = utils.get_data_dir(__file__, name)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: definition in cluster type bundle"):
        errorcodes.BUNDLE_ERROR.equal(e, entity + " definition in cluster type bundle")


def test_check_cluster_bundle_versions_as_a_string(sdk_client_fs: ADCMClient):
    """Test upload cluster bundle with versions"""
    stack_dir = utils.get_data_dir(__file__, "cluster_service_versions_as_a_string")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check bundle versions"):
        prototype = sdk_client_fs.service_prototype()
        assert isinstance(prototype.version, str)


def test_check_host_bundle_versions_as_a_string(sdk_client_fs: ADCMClient):
    """Test upload hostprovider bundle with versions"""
    stack_dir = utils.get_data_dir(__file__, "host_version_as_a_string")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check host versions"):
        prototype = sdk_client_fs.host_prototype()
        assert isinstance(prototype.version, str)


def test_cluster_bundle_can_be_on_any_level(sdk_client_fs: ADCMClient):
    """Test upload cluster bundle lower that in directory root"""
    stack_dir = utils.get_data_dir(__file__, "cluster_bundle_on_any_level")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check cluster bundle"):
        assert sdk_client_fs.service_prototype_list()
        assert sdk_client_fs.cluster_prototype_list()


def test_host_bundle_can_be_on_any_level(sdk_client_fs: ADCMClient):
    """Test upload hostprovider bundle lower that in directory root"""
    stack_dir = utils.get_data_dir(__file__, "host_bundle_on_any_level")
    sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check host bundle"):
        assert sdk_client_fs.host_prototype_list()


@allure.issue("https://jira.arenadata.io/browse/ADCM-184")
def test_cluster_config_without_required_parent_key(sdk_client_fs: ADCMClient):
    """Test some config related stuff"""
    stack_dir = utils.get_data_dir(__file__, "cluster_config_without_required_parent_key")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step('Set config "str-key": "string"'):
        config = cluster.config_set({"str-key": "string"})
    with allure.step("Check config"):
        expected = cluster.config()
        assert config == expected


def test_cluster_bundle_definition_shouldnt_contain_host(sdk_client_fs: ADCMClient):
    """Test cluster bundle definition should not contain host"""
    stack_dir = utils.get_data_dir(__file__, "cluster_bundle_with_host_definition")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: There are 1 host definition in cluster type"):
        errorcodes.BUNDLE_ERROR.equal(e, "There are 1 host definition in cluster type")


def test_when_cluster_config_must_contains_some_subkeys(sdk_client_fs: ADCMClient):
    """Test cluster config subkeys should not be empty"""
    stack_dir = utils.get_data_dir(__file__, "cluster_config_with_empty_subkeys")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    bad_config = {"str-key": "bluh", "subkeys": {}}
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step("Set bad config"):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            cluster.config_set(bad_config)
    with allure.step("Check error: should contains some subkeys"):
        errorcodes.CONFIG_KEY_ERROR.equal(e, "should contains some subkeys")


def test_when_host_config_must_contains_some_subkeys(sdk_client_fs: ADCMClient):
    """Test hostprovider config subkeys should not be empty"""
    stack_dir = utils.get_data_dir(__file__, "host_config_with_empty_subkeys")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Create provider"):
        bad_config = {"str-key": "bluh", "subkeys": {}}
        provider = bundle.provider_create(utils.random_string())
    with allure.step("Create host"):
        host = provider.host_create(utils.random_string())
    with allure.step('Set bad config: "str-key": "bluh", "subkeys": {}'):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            host.config_set(bad_config)
    with allure.step("Check error: should contains some subkeys"):
        errorcodes.CONFIG_KEY_ERROR.equal(e, "should contains some subkeys")


def test_host_bundle_shouldnt_contains_service_definition(sdk_client_fs: ADCMClient):
    """Test hostprovider bundle should not contain cluster definition"""
    stack_dir = utils.get_data_dir(__file__, "host_bundle_with_service_definition")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: service definition in host provider type bundle"):
        errorcodes.BUNDLE_ERROR.equal(e, "service definition in host provider type bundle")


def test_service_job_should_run_success(sdk_client_fs: ADCMClient):
    """Test run service action success"""
    stack_dir = utils.get_data_dir(__file__, "job_should_run_success")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step("Add service"):
        service = cluster.service_add(name="zookeeper")
    with allure.step("Run action: install"):
        action_run = service.action(name="install").run()
        action_run.try_wait()
    with allure.step("Check if state is success"):
        assert action_run.status == "success"


def test_service_job_should_run_failed(sdk_client_fs: ADCMClient):
    """Test run service action fail"""
    stack_dir = utils.get_data_dir(__file__, "job_should_run_failed")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step("Add service"):
        service = cluster.service_add(name="zookeeper")
    with allure.step("Run action: should_be_failed"):
        action_run = service.action(name="should_be_failed").run()
        action_run.wait()
    with allure.step("Check if state is failed"):
        assert action_run.status == "failed"


def test_cluster_action_run_should_be_success(sdk_client_fs: ADCMClient):
    """Test run cluster action success"""
    stack_dir = utils.get_data_dir(__file__, "cluster_action_run_should_be_success")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step("Run action: install"):
        action_run = cluster.action(name="install").run()
        action_run.try_wait()
    with allure.step("Check if state is success"):
        assert action_run.status == "success"


def test_cluster_action_run_should_be_failed(sdk_client_fs: ADCMClient):
    """Test run cluster action fail"""
    stack_dir = utils.get_data_dir(__file__, "cluster_action_run_should_be_success")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step("Run action: run_fail"):
        action_run = cluster.action(name="run_fail").run()
        action_run.wait()
    with allure.step("Check if state is failed"):
        assert action_run.status == "failed"


def test_should_return_job_log_files(sdk_client_fs: ADCMClient):
    """Test job log files"""
    stack_dir = utils.get_data_dir(__file__, "return_job_log_files")
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step("Run action"):
        action_run = cluster.action().run()
        action_run.wait()
        job = action_run.job()
    with allure.step("Check log iles"):
        log_files_list = job.log_files
        log_list = job.log_list()
        assert log_files_list is not None, log_files_list
        for log in log_list:
            expected_file = job.log(id=log.id)
            assert expected_file.content


def test_load_bundle_with_undefined_config_parameter(sdk_client_fs: ADCMClient):
    """Test upload bundle with unknown param"""
    stack_dir = utils.get_data_dir(__file__, "param_not_defined")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(stack_dir)
    with allure.step("Check error: should be a map"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, "None of the variants", 'for rule "config_dict_obj" match')


def test_when_import_has_unknown_config_parameter_shouldnt_be_loaded(
    sdk_client_fs: ADCMClient,
):
    """Test upload bundle with unknown import param"""
    bundledir = utils.get_data_dir(__file__, "import_has_unknown_parameter")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(bundledir)
    with allure.step("Check error: does not has config group"):
        errorcodes.INVALID_OBJECT_DEFINITION.equal(e, "cluster ", " does not has ", " config group")


def test_when_bundle_hasnt_only_host_definition(sdk_client_fs: ADCMClient):
    """Test upload bundle without cluster or provider definition"""
    bundledir = utils.get_data_dir(__file__, "host_wo_provider")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(bundledir)
    with allure.step("Check error: There isnt any cluster or host provider definition in bundle"):
        errorcodes.BUNDLE_ERROR.equal(e, "There isn't any cluster or host provider definition in bundle")


def _get_invalid_bundle_config_params() -> List[ParameterSet]:
    def _get_pytest_param(bundle_name, adcm_err: ADCMError, msg: str):
        return pytest.param(utils.get_data_dir(__file__, bundle_name), (adcm_err, msg), id=bundle_name)

    return [
        _get_pytest_param(
            "did_not_load",
            errorcodes.STACK_LOAD_ERROR,
            "no config files in stack directory",
        ),
        _get_pytest_param("yaml_parser_error", errorcodes.STACK_LOAD_ERROR, "YAML decode"),
        _get_pytest_param(
            "yaml_decode_duplicate_anchor",
            errorcodes.STACK_LOAD_ERROR,
            "found duplicate anchor",
        ),
        _get_pytest_param("expected_colon", errorcodes.STACK_LOAD_ERROR, "could not find expected ':'"),
        _get_pytest_param(
            "missed_whitespace",
            errorcodes.STACK_LOAD_ERROR,
            "mapping values are not allowed here",
        ),
        _get_pytest_param(
            "expected_block_end",
            errorcodes.STACK_LOAD_ERROR,
            "expected <block end>, but found '-'",
        ),
        _get_pytest_param(
            "incorrect_option_definition",
            errorcodes.INVALID_OBJECT_DEFINITION,
            "Value of map key \"required\" should be a <class 'bool'>",
        ),
    ]


@pytest.mark.parametrize(
    ("bundle_archive", "expected_error"),
    _get_invalid_bundle_config_params(),
    indirect=["bundle_archive"],
)
def test_invalid_bundle_config(sdk_client_fs: ADCMClient, bundle_archive, expected_error: Tuple[ADCMError, str]):
    """Test upload bundle with invalid config"""
    (adcm_error, expected_msg) = expected_error
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(bundle_archive)
    with allure.step("Check error"):
        adcm_error.equal(e, expected_msg)
