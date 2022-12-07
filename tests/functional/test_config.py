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

# pylint:disable=redefined-outer-name

"""Tests for config"""

import os
from typing import Tuple

import allure
import coreapi
import pytest
import yaml
from _pytest.fixtures import SubRequest
from adcm_client.base import ActionHasIssues
from adcm_client.objects import ADCMClient, Cluster, Host, Provider, Service
from adcm_pytest_plugin.utils import fixture_parametrized_by_data_subdirs, get_data_dir
from coreapi.exceptions import ErrorMessage
from tests.functional.plugin_utils import AnyADCMObject
from tests.library.errorcodes import CONFIG_KEY_ERROR, CONFIG_NOT_FOUND, ADCMError


def get_value(path, entity, value_type):
    """Get bundle path"""
    if isinstance(entity, Cluster):
        file_name = os.path.join(path, 'cluster', 'cluster_action.yaml')
    elif isinstance(entity, Service):
        file_name = os.path.join(path, 'cluster', 'service_action.yaml')
    elif isinstance(entity, Provider):
        file_name = os.path.join(path, 'provider', 'provider_action.yaml')
    elif isinstance(entity, Host):
        file_name = os.path.join(path, 'provider', 'host_action.yaml')
    else:
        raise ValueError(f"Incorrect type of entity {entity}")

    with open(file_name, 'r', encoding='utf_8') as file:
        data = yaml.full_load(file)
        playbook_vars = data[0]['vars']
        return playbook_vars[value_type]


def processing_data(sdk_client_fs, request, variant):
    """Process data for test"""
    path = request.param
    config_type = os.path.split(path)[1]
    cluster_bundle = sdk_client_fs.upload_from_fs(os.path.join(path, 'cluster'))
    provider_bundle = sdk_client_fs.upload_from_fs(os.path.join(path, 'provider'))

    cluster = cluster_bundle.cluster_create(f'cluster {config_type} {variant}'.replace('_', ' '))
    service = cluster.service_add(name=f'service_{config_type}_{variant}')

    provider = provider_bundle.provider_create(f'provider_{config_type}_{variant}')
    host = provider.host_create(f'host-{config_type}-{variant}'.replace('_', '-'))
    cluster.host_add(host)
    return path, config_type, [cluster, provider, service, host]


def assert_config_value_error(entity, sent_data):
    """Assert error is CONFIG_VALUE_ERROR"""
    with pytest.raises(coreapi.exceptions.ErrorMessage) as error:
        entity.config_set(sent_data)
    assert error.value.error['code'] == 'CONFIG_VALUE_ERROR'


def assert_action_has_issues(entity):
    """Assert action has issues"""
    with pytest.raises(ActionHasIssues):
        entity.action(name='job').run().wait()


def assert_list_type(*args):
    """
    Type check "list"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if sent_value_type in ['empty_value', 'null_value']:
            assert_config_value_error(entity, sent_data)
        else:
            assert entity.config_set(sent_data) == sent_data

        if not is_default and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        else:
            if sent_value_type in ['empty_value', 'null_value'] and not is_default:
                assert_action_has_issues(entity)
            else:
                action_status = entity.action(name='job').run().wait()
                assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_map_type(*args):
    """
    Type check "map"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if sent_value_type in ['empty_value', 'null_value']:
            assert_config_value_error(entity, sent_data)
        else:
            assert entity.config_set(sent_data) == sent_data
        if not is_default and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        else:
            if sent_value_type in ['empty_value', 'null_value'] and not is_default:
                assert_action_has_issues(entity)
            else:
                action_status = entity.action(name='job').run().wait()
                assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_string_type(*args):
    """
    Type check "string"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if is_default:
            if sent_value_type in ['empty_value', 'null_value']:
                assert_config_value_error(entity, sent_data)
            else:
                assert entity.config_set(sent_data) == sent_data

            action_status = entity.action(name='job').run().wait()
            assert action_status == 'success'
        else:
            if sent_value_type in ['empty_value', 'null_value']:
                assert_config_value_error(entity, sent_data)
            else:
                assert entity.config_set(sent_data) == sent_data

            if isinstance(entity, Cluster):
                assert_action_has_issues(entity)
            else:
                if sent_value_type in ['empty_value', 'null_value']:
                    assert_action_has_issues(entity)
                else:
                    action_status = entity.action(name='job').run().wait()
                    assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data

        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_password_type(*args):
    """
    Type check "password"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if sent_value_type in ['empty_value', 'null_value']:
            assert_config_value_error(entity, sent_data)
        else:
            assert entity.config_set(sent_data)['password'].startswith('$ANSIBLE_VAULT;1.1;AES256')
        if is_default:
            action_status = entity.action(name='job').run().wait()
            assert action_status == 'success'
        else:
            if isinstance(entity, Cluster):
                assert_action_has_issues(entity)
            else:
                if sent_value_type in ['empty_value', 'null_value']:
                    assert_action_has_issues(entity)
                else:
                    action_status = entity.action(name='job').run().wait()
                    assert action_status == 'success'
    else:
        if sent_value_type == 'correct_value':
            assert entity.config_set(sent_data)['password'].startswith('$ANSIBLE_VAULT;1.1;AES256')
        else:
            assert entity.config_set(sent_data) == sent_data

        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_text_type(*args):
    """
    Type check "text"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if is_default:
            if sent_value_type in ['empty_value', 'null_value']:
                assert_config_value_error(entity, sent_data)
            else:
                assert entity.config_set(sent_data) == sent_data

            action_status = entity.action(name='job').run().wait()
            assert action_status == 'success'
        else:
            if sent_value_type in ['empty_value', 'null_value']:
                assert_config_value_error(entity, sent_data)
            else:
                assert entity.config_set(sent_data) == sent_data

            if isinstance(entity, Cluster):
                assert_action_has_issues(entity)
            else:
                if sent_value_type in ['empty_value', 'null_value']:
                    assert_action_has_issues(entity)
                else:
                    action_status = entity.action(name='job').run().wait()
                    assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data

        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_file_type(*args):
    """
    Type check "file"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required and sent_value_type == 'null_value':
        assert_config_value_error(entity, sent_data)
    elif sent_value_type == 'empty_value':
        assert_config_value_error(entity, sent_data)
    else:
        assert entity.config_set(sent_data) == sent_data

    if is_default:
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'
    else:
        if is_required and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        else:
            if is_required and sent_value_type in ['empty_value', 'null_value']:
                assert_action_has_issues(entity)
            else:
                action_status = entity.action(name='job').run().wait()
                assert action_status == 'success'


def assert_structure_type(*args):
    """
    Type check "structure"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if sent_value_type == 'null_value':
        if is_required:
            if is_default:
                assert_config_value_error(entity, sent_data)
                action_status = entity.action(name='job').run().wait()
                assert action_status == 'success'
            else:
                assert_config_value_error(entity, sent_data)
                assert_action_has_issues(entity)

    elif is_required and not is_default and isinstance(entity, Cluster):
        assert entity.config_set(sent_data) == sent_data
        assert_action_has_issues(entity)
    else:
        assert entity.config_set(sent_data) == sent_data
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_boolean_type(*args):
    """
    Type check "boolean"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required and sent_value_type == 'null_value':
        assert_config_value_error(entity, sent_data)
    else:
        assert entity.config_set(sent_data) == sent_data

    if is_required and not is_default:
        if sent_value_type == 'correct_value' and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        if sent_value_type == 'null_value':
            assert_action_has_issues(entity)
    else:
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_integer_type(*args):
    """
    Type check "integer"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required and sent_value_type == 'null_value':
        assert_config_value_error(entity, sent_data)
    else:
        assert entity.config_set(sent_data) == sent_data

    if is_required and not is_default:
        if sent_value_type == 'correct_value' and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        if sent_value_type == 'null_value':
            assert_action_has_issues(entity)
    else:
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_float_type(*args):
    """
    Type check "float"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required and sent_value_type == 'null_value':
        assert_config_value_error(entity, sent_data)
    else:
        assert entity.config_set(sent_data) == sent_data

    if is_required and not is_default:
        if sent_value_type == 'correct_value' and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        if sent_value_type == 'null_value':
            assert_action_has_issues(entity)
    else:
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


def assert_option_type(*args):
    """
    Type check "option"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required and sent_value_type == 'null_value':
        assert_config_value_error(entity, sent_data)
    else:
        assert entity.config_set(sent_data) == sent_data

    if is_required and not is_default:
        if sent_value_type == 'correct_value' and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        if sent_value_type == 'null_value':
            assert_action_has_issues(entity)
    else:
        action_status = entity.action(name='job').run().wait()
        assert action_status == 'success'


ASSERT_TYPE = {
    'list': assert_list_type,
    'map': assert_map_type,
    'string': assert_string_type,
    'password': assert_password_type,
    'text': assert_text_type,
    'file': assert_file_type,
    'structure': assert_structure_type,
    'boolean': assert_boolean_type,
    'integer': assert_integer_type,
    'float': assert_float_type,
    'option': assert_option_type,
}


def assert_config_type(path, config_type, entities, is_required, is_default, sent_value_type):
    """
    Running test scenario for cluster, service, provider and host
    """
    for entity in entities:
        with allure.step(f"Assert that {entity} config works expected"):
            ASSERT_TYPE[config_type](path, config_type, entity, is_required, is_default, sent_value_type)


@fixture_parametrized_by_data_subdirs(__file__, 'not_required', 'with_default', 'sent_correct_value')
def nr_wd_cv(sdk_client_fs: ADCMClient, request):
    """Process data for not_required_with_default_sent_correct_value"""
    return processing_data(sdk_client_fs, request, 'not_required_with_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(__file__, 'not_required', 'with_default', 'sent_empty_value')
def nr_wd_ev(sdk_client_fs: ADCMClient, request):
    """Process data for not_required_with_default_sent_empty_value"""
    return processing_data(sdk_client_fs, request, 'not_required_with_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(__file__, 'not_required', 'with_default', 'sent_null_value')
def nr_wd_nv(sdk_client_fs: ADCMClient, request):
    """Process data for not_required_with_default_sent_null_value"""
    return processing_data(sdk_client_fs, request, 'not_required_with_default_sent_null_value')


def test_not_required_with_default_sent_correct_value(nr_wd_cv):
    """
    A test for each type, provided that the parameter is not required, and contains a
    default value. Trying to send the correct value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       not_required/with_default/sent_correct_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending correct value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*nr_wd_cv, False, True, 'correct_value')


def test_not_required_with_default_sent_empty_value(nr_wd_ev):
    """
    A test for each type, provided that the parameter is not required, and contains a
    default value. Trying to send the empty value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       not_required/with_default/sent_empty_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending empty value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*nr_wd_ev, False, True, 'empty_value')


def test_not_required_with_default_sent_null_value(nr_wd_nv):
    """
    A test for each type, provided that the parameter is not required, and contains a
    default value. Trying to send the null value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       not_required/with_default/sent_null_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending null value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*nr_wd_nv, False, True, 'null_value')


@fixture_parametrized_by_data_subdirs(__file__, 'not_required', 'without_default', 'sent_correct_value')
def nr_wod_cv(sdk_client_fs: ADCMClient, request):
    """Process data for not_required_without_default_sent_correct_value"""
    return processing_data(sdk_client_fs, request, 'not_required_without_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(__file__, 'not_required', 'without_default', 'sent_empty_value')
def nr_wod_ev(sdk_client_fs: ADCMClient, request):
    """Process data for not_required_without_default_sent_empty_value"""
    return processing_data(sdk_client_fs, request, 'not_required_without_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(__file__, 'not_required', 'without_default', 'sent_null_value')
def nr_wod_nv(sdk_client_fs: ADCMClient, request):
    """Process data for not_required_without_default_sent_null_value"""
    return processing_data(sdk_client_fs, request, 'not_required_without_default_sent_null_value')


def test_not_required_without_default_sent_correct_value(nr_wod_cv):
    """
    A test for each type, provided that the parameter is not required, and not contains a
    default value. Trying to send the correct value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       not_required/without_default/sent_correct_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending correct value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*nr_wod_cv, False, False, 'correct_value')


def test_not_required_without_default_sent_empty_value(nr_wod_ev):
    """
    A test for each type, provided that the parameter is not required, and not contains a
    default value. Trying to send the empty value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       not_required/without_default/sent_empty_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending empty value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*nr_wod_ev, False, False, 'empty_value')


def test_not_required_without_default_sent_null_value(nr_wod_nv):
    """
    A test for each type, provided that the parameter is not required, and not contains a
    default value. Trying to send the null value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       not_required/without_default/sent_null_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending null value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*nr_wod_nv, False, False, 'null_value')


@fixture_parametrized_by_data_subdirs(__file__, 'required', 'with_default', 'sent_correct_value')
def r_wd_cv(sdk_client_fs: ADCMClient, request):
    """Process data for required_with_default_sent_correct_value"""
    return processing_data(sdk_client_fs, request, 'required_with_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(__file__, 'required', 'with_default', 'sent_empty_value')
def r_wd_ev(sdk_client_fs: ADCMClient, request):
    """Process data for required_with_default_sent_empty_value"""
    return processing_data(sdk_client_fs, request, 'required_with_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(__file__, 'required', 'with_default', 'sent_null_value')
def r_wd_nv(sdk_client_fs: ADCMClient, request):
    """Process data for required_with_default_sent_null_value"""
    return processing_data(sdk_client_fs, request, 'required_with_default_sent_null_value')


def test_required_with_default_sent_correct_value(r_wd_cv):
    """
    A test for each type, provided that the parameter is required, and contains a
    default value. Trying to send the correct value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       required/with_default/sent_correct_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending correct value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*r_wd_cv, True, True, 'correct_value')


def test_required_with_default_sent_empty_value(r_wd_ev):
    """
    A test for each type, provided that the parameter is required, and contains a
    default value. Trying to send the empty value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       required/with_default/sent_empty_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending empty value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*r_wd_ev, True, True, 'empty_value')


def test_required_with_default_sent_null_value(r_wd_nv):
    """
    A test for each type, provided that the parameter is required, and contains a
    default value. Trying to send the null value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       required/with_default/sent_null_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending null value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*r_wd_nv, True, True, 'null_value')


@fixture_parametrized_by_data_subdirs(__file__, 'required', 'without_default', 'sent_correct_value')
def r_wod_cv(sdk_client_fs: ADCMClient, request):
    """Process data for required_without_default_sent_correct_value"""
    return processing_data(sdk_client_fs, request, 'required_without_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(__file__, 'required', 'without_default', 'sent_empty_value')
def r_wod_ev(sdk_client_fs: ADCMClient, request):
    """Process data for required_without_default_sent_empty_value"""
    return processing_data(sdk_client_fs, request, 'required_without_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(__file__, 'required', 'without_default', 'sent_null_value')
def r_wod_nv(sdk_client_fs: ADCMClient, request):
    """Process data for required_without_default_sent_null_value"""
    return processing_data(sdk_client_fs, request, 'required_without_default_sent_null_value')


def test_required_without_default_sent_correct_value(r_wod_cv):
    """
    A test for each type, provided that the parameter is required, and not contains a
    default value. Trying to send the correct value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       required/without_default/sent_correct_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending correct value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*r_wod_cv, True, False, 'correct_value')


def test_required_without_default_sent_empty_value(r_wod_ev):
    """
    A test for each type, provided that the parameter is required, and not contains a
    default value. Trying to send the empty value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       required/without_default/sent_empty_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending empty value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*r_wod_ev, True, False, 'empty_value')


def test_required_without_default_sent_null_value(r_wod_nv):
    """
    A test for each type, provided that the parameter is required, and not contains a
    default value. Trying to send the null value. Each action playbook contains the value
    to be sent, and the value that we expect in the config, after sending.
    Scenario:
    1. Uploading bundle for cluster and provider from
       required/without_default/sent_null_value for each type
    2. Creating cluster, provider and host. Adding service and host in cluster
    3. Updating config for cluster, service, provider and host. Sending null value for
       each type
    4. Running action for cluster, service, provider and host. Checking current config
       in action.
    """
    assert_config_type(*r_wod_nv, True, False, 'null_value')


@pytest.fixture()
def cluster(request: SubRequest, sdk_client_fs: ADCMClient) -> Cluster:
    """Upload cluster bundle, create cluster, add service"""
    bundle_subdir = request.param if hasattr(request, 'param') else "simple_config"
    bundle = sdk_client_fs.upload_from_fs(os.path.join(get_data_dir(__file__), bundle_subdir, "cluster"))
    cluster = bundle.cluster_create(name='test cluster')
    cluster.service_add(name='test_service')
    return cluster


@pytest.fixture()
def provider(request: SubRequest, sdk_client_fs: ADCMClient) -> Provider:
    """Upload provider bundle, create provider, add host"""
    bundle_subdir = request.param if hasattr(request, 'param') else "simple_config"
    bundle = sdk_client_fs.upload_from_fs(os.path.join(get_data_dir(__file__), bundle_subdir, "provider"))
    provider = bundle.provider_create(name='test_provider')
    provider.host_create(fqdn='test-host')
    return provider


# !===== Secret text config field type =====!


class TestConfigFieldTypes:
    """Test different types of fields"""

    # pylint: disable=too-many-locals
    @pytest.mark.parametrize('cluster', ["secret_text"], indirect=True)
    @pytest.mark.parametrize('provider', ["secret_text"], indirect=True)
    def test_secret_text_field(self, cluster: Cluster, provider: Provider):
        """Test "secrettext" config field type"""
        value_to_set = "verysimple\nI'am"
        default_value = "very\nsecret\ntext"
        fields = (
            'secret_required_default',
            'secret_not_required_default',
            'secret_not_required_no_default',
            'secret_required_no_default',
        )
        (
            required_default,
            not_required_default,
            not_required_no_default,
            required_no_default,
        ) = fields
        required_diff = {required_no_default: value_to_set}
        changed_diff = {field: value_to_set for field in fields if field != required_no_default}
        default_diff = {
            not_required_no_default: None,
            required_default: default_value,
            not_required_default: default_value,
        }

        service = cluster.service()
        component = service.component()
        host = provider.host()
        cluster.host_add(host)
        cluster.hostcomponent_set((host, component))
        objects_to_change = (cluster, service, component, provider, host)

        # to make actions available
        with allure.step(f'Set required fields that has no default to {value_to_set}'):
            for adcm_object in objects_to_change:
                adcm_object.config_set_diff(required_diff)
        with allure.step(f'Set other fields to {value_to_set} and check that config changed correctly'):
            self._change_config_and_check_changed_by_action(
                objects_to_change, changed_diff, 'check_default', 'check_changed'
            )
        with allure.step('Set default values for fields and check that config changed correctly'):
            self._change_config_and_check_changed_by_action(
                objects_to_change, default_diff, 'check_changed', 'check_default'
            )

    def _change_config_and_check_changed_by_action(
        self,
        objects_to_change: Tuple[AnyADCMObject],
        config_to_set: dict,
        action_before: str,
        action_after: str,
    ):
        """
        Loop over objects_to_change:
        1. Run `action_before` to ensure state before config change is correct
        2. Change config
        3. Run `action_after` to ensure config changed correctly
        """
        for adcm_object in objects_to_change:
            _run_action_and_assert_status(adcm_object, action_before)
            adcm_object.config_set_diff(config_to_set)
            _run_action_and_assert_status(adcm_object, action_after)


# !===== Negative scenarios =====!


@pytest.mark.parametrize("cluster", ["no_config"], indirect=True)
@pytest.mark.parametrize("provider", ["no_config"], indirect=True)
def test_config_absence(cluster: Cluster, provider: Provider):
    """Check that ADCM reacts adequate on passing config to bundle with no config"""
    _expect_correct_fail_on_config(cluster, provider, {'oh_no': 'config is absent'}, CONFIG_NOT_FOUND)


def test_pass_wrong_config_keys(cluster: Cluster, provider: Provider):
    """Check that ADCM reacts adequate on passing incorrect keys in config_set"""
    _expect_correct_fail_on_config(cluster, provider, {'no_such_key': 'okay'}, CONFIG_KEY_ERROR)


def _expect_correct_fail_on_config(cluster: Cluster, provider: Provider, config: dict, error: ADCMError):
    """Check that config_set fails with CONFIG_VALUE_ERROR"""
    component = (service := cluster.service()).component()
    host = provider.host()
    for obj in (cluster, service, component, provider, host):
        with allure.step(f'Try to change config of {obj.__class__.__name__} and expect {error}'):
            try:
                obj.config_set(config)
            except ErrorMessage as e:
                error.equal(e)
            else:
                raise AssertionError("Config set should've failed")


@allure.step("Run action '{action_name}' on {adcm_object} and expect status '{expected_status}'")
def _run_action_and_assert_status(adcm_object: AnyADCMObject, action_name: str, expected_status: str = 'success'):
    """
    Run action on any ADCM object and assert status
    """
    assert (
        actual_status := adcm_object.action(name=action_name).run().wait()
    ) == expected_status, (
        f"Actions '{action_name}' is expected to finish with status '{expected_status}', not '{actual_status}'"
    )
