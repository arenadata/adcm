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
# pylint: disable=W0621, R0912, W0612
import os

import coreapi
import pytest
import yaml
from adcm_client.base import ActionHasIssues
from adcm_client.objects import ADCMClient, Cluster, Service, Provider, Host
from adcm_pytest_plugin.utils import fixture_parametrized_by_data_subdirs


def get_value(path, entity, value_type):
    if isinstance(entity, Cluster):
        file_name = os.path.join(path, 'cluster', 'cluster_action.yaml')
    if isinstance(entity, Service):
        file_name = os.path.join(path, 'cluster', 'service_action.yaml')
    if isinstance(entity, Provider):
        file_name = os.path.join(path, 'provider', 'provider_action.yaml')
    if isinstance(entity, Host):
        file_name = os.path.join(path, 'provider', 'host_action.yaml')

    with open(file_name, 'r') as f:
        data = yaml.full_load(f)
        playbook_vars = data[0]['vars']
        return playbook_vars[value_type]


def processing_data(sdk_client_ms, request, variant):
    path = request.param
    config_type = os.path.split(path)[1]
    cluster_bundle = sdk_client_ms.upload_from_fs(os.path.join(path, 'cluster'))
    provider_bundle = sdk_client_ms.upload_from_fs(os.path.join(path, 'provider'))

    cluster = cluster_bundle.cluster_create(f'cluster_{config_type}_{variant}')
    service = cluster.service_add(
        name=f'service_{config_type}_{variant}')

    provider = provider_bundle.provider_create(f'provider_{config_type}_{variant}')
    host = provider.host_create(f'host_{config_type}_{variant}')
    cluster.host_add(host)
    return path, config_type, [cluster, provider, service, host]


def assert_config_value_error(entity, sent_data):
    with pytest.raises(coreapi.exceptions.ErrorMessage) as error:
        entity.config_set(sent_data)
    assert error.value.error['code'] == 'CONFIG_VALUE_ERROR'


def assert_action_has_issues(entity):
    with pytest.raises(ActionHasIssues):
        entity.action_run(name='job').wait()


def assert_list_type(*args):
    """
    Type check "list"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if sent_value_type == 'null_value':
            assert_config_value_error(entity, sent_data)
        else:
            assert entity.config_set(sent_data) == sent_data

        if not is_default and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        else:
            if sent_value_type == 'null_value' and not is_default:
                assert_action_has_issues(entity)
            else:
                action_status = entity.action_run(name='job').wait()
                assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data
        action_status = entity.action_run(name='job').wait()
        assert action_status == 'success'


def assert_map_type(*args):
    """
    Type check "map"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if sent_value_type == 'null_value':
            assert_config_value_error(entity, sent_data)
        else:
            assert entity.config_set(sent_data) == sent_data
        if not is_default and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        else:
            if sent_value_type == 'null_value' and not is_default:
                assert_action_has_issues(entity)
            else:
                action_status = entity.action_run(name='job').wait()
                assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data
        action_status = entity.action_run(name='job').wait()
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

            action_status = entity.action_run(name='job').wait()
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
                    action_status = entity.action_run(name='job').wait()
                    assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data

        action_status = entity.action_run(name='job').wait()
        assert action_status == 'success'


def assert_password_type(*args):
    """
    Type check "password"
    """
    path, config_type, entity, is_required, is_default, sent_value_type = args
    sent_data = {config_type: get_value(path, entity, 'sent_value')}

    if is_required:
        if is_default:
            if sent_value_type in ['empty_value', 'null_value']:
                assert_config_value_error(entity, sent_data)
            else:
                assert entity.config_set(
                    sent_data)['password'].startswith('$ANSIBLE_VAULT;1.1;AES256')

            action_status = entity.action_run(name='job').wait()
            assert action_status == 'success'
        else:
            if sent_value_type in ['empty_value', 'null_value']:
                assert_config_value_error(entity, sent_data)
            else:
                assert entity.config_set(
                    sent_data)['password'].startswith('$ANSIBLE_VAULT;1.1;AES256')

            if isinstance(entity, Cluster):
                assert_action_has_issues(entity)
            else:
                if sent_value_type in ['empty_value', 'null_value']:
                    assert_action_has_issues(entity)
                else:
                    action_status = entity.action_run(name='job').wait()
                    assert action_status == 'success'
    else:
        if sent_value_type == 'correct_value':
            assert entity.config_set(sent_data)['password'].startswith('$ANSIBLE_VAULT;1.1;AES256')
        else:
            assert entity.config_set(sent_data) == sent_data

        action_status = entity.action_run(name='job').wait()
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

            action_status = entity.action_run(name='job').wait()
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
                    action_status = entity.action_run(name='job').wait()
                    assert action_status == 'success'
    else:
        assert entity.config_set(sent_data) == sent_data

        action_status = entity.action_run(name='job').wait()
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
        action_status = entity.action_run(name='job').wait()
        assert action_status == 'success'
    else:
        if is_required and isinstance(entity, Cluster):
            assert_action_has_issues(entity)
        else:
            if is_required and sent_value_type in ['empty_value', 'null_value']:
                assert_action_has_issues(entity)
            else:
                action_status = entity.action_run(name='job').wait()
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
                action_status = entity.action_run(name='job').wait()
                assert action_status == 'success'
            else:
                assert_config_value_error(entity, sent_data)
                assert_action_has_issues(entity)

    elif is_required and not is_default and isinstance(entity, Cluster):
        assert entity.config_set(sent_data) == sent_data
        assert_action_has_issues(entity)
    else:
        assert entity.config_set(sent_data) == sent_data
        action_status = entity.action_run(name='job').wait()
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
        action_status = entity.action_run(name='job').wait()
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
        action_status = entity.action_run(name='job').wait()
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
        action_status = entity.action_run(name='job').wait()
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
        action_status = entity.action_run(name='job').wait()
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
        ASSERT_TYPE[config_type](
            path, config_type, entity, is_required, is_default, sent_value_type)


@fixture_parametrized_by_data_subdirs(
    __file__, 'not_required', 'with_default', 'sent_correct_value', scope='module')
def nr_wd_cv(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'not_required_with_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'not_required', 'with_default', 'sent_empty_value', scope='module')
def nr_wd_ev(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'not_required_with_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'not_required', 'with_default', 'sent_null_value', scope='module')
def nr_wd_nv(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'not_required_with_default_sent_null_value')


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


@fixture_parametrized_by_data_subdirs(
    __file__, 'not_required', 'without_default', 'sent_correct_value', scope='module')
def nr_wod_cv(sdk_client_ms: ADCMClient, request):
    return processing_data(
        sdk_client_ms, request, 'not_required_without_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'not_required', 'without_default', 'sent_empty_value', scope='module')
def nr_wod_ev(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'not_required_without_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'not_required', 'without_default', 'sent_null_value', scope='module')
def nr_wod_nv(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'not_required_without_default_sent_null_value')


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


@fixture_parametrized_by_data_subdirs(
    __file__, 'required', 'with_default', 'sent_correct_value', scope='module')
def r_wd_cv(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'required_with_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'required', 'with_default', 'sent_empty_value', scope='module')
def r_wd_ev(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'required_with_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'required', 'with_default', 'sent_null_value', scope='module')
def r_wd_nv(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'required_with_default_sent_null_value')


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


@fixture_parametrized_by_data_subdirs(
    __file__, 'required', 'without_default', 'sent_correct_value', scope='module')
def r_wod_cv(sdk_client_ms: ADCMClient, request):
    return processing_data(
        sdk_client_ms, request, 'required_without_default_sent_correct_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'required', 'without_default', 'sent_empty_value', scope='module')
def r_wod_ev(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'required_without_default_sent_empty_value')


@fixture_parametrized_by_data_subdirs(
    __file__, 'required', 'without_default', 'sent_null_value', scope='module')
def r_wod_nv(sdk_client_ms: ADCMClient, request):
    return processing_data(sdk_client_ms, request, 'required_without_default_sent_null_value')


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
