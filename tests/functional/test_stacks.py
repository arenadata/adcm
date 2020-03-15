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
import json
import os
import random

import allure
import coreapi
import pytest
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker import DockerWrapper
from jsonschema import validate

# pylint: disable=W0611, W0621
from tests.library import errorcodes, steps

BUNDLES = os.path.join(os.path.dirname(__file__), "stacks/")
SCHEMAS = os.path.join(os.path.dirname(__file__), "schemas/")


@pytest.fixture(scope="function")
def adcm(image, request):
    repo, tag = image
    dw = DockerWrapper()
    adcm = dw.run_adcm(image=repo, tag=tag, pull=False)
    adcm.api.auth(username='admin', password='admin')

    def fin():
        adcm.stop()

    request.addfinalizer(fin)
    return adcm


@pytest.fixture(scope="function")
def client(adcm):
    return adcm.api.objects


def test_didnot_load_stack(client):
    stack_dir = BUNDLES + 'did_not_load'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)
    errorcodes.STACK_LOAD_ERROR.equal(e, 'no config files in stack directory')


def test_service_wo_name(client):
    stack_dir = BUNDLES + 'service_wo_name'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'No name in service definition:')


def test_wo_version(client):
    stack_dir = BUNDLES + 'service_wo_version'
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'No version in service')


def test_service_wo_actions(client):
    stack_dir = BUNDLES + 'service_wo_action'
    steps.upload_bundle(client, stack_dir)

    service_prototype = client.stack.service.list()[0]
    schema = json.load(open(SCHEMAS + '/stack_list_item_schema.json'))
    assert validate(service_prototype, schema) is None


def test_cluster_proto_wo_actions(client):
    stack_dir = BUNDLES + 'cluster_proto_wo_actions'

    steps.upload_bundle(client, stack_dir)
    cluster_prototype = client.stack.cluster.list()[0]
    schema = json.load(open(SCHEMAS + '/stack_list_item_schema.json'))
    assert validate(cluster_prototype, schema) is None


def test_host_proto_wo_actions(client):
    stack_dir = BUNDLES + 'host_proto_wo_action'
    steps.upload_bundle(client, stack_dir)
    host_prototype = client.stack.host.list()[0]
    schema = json.load(open(SCHEMAS + '/stack_list_item_schema.json'))
    assert validate(host_prototype, schema) is None


def test_stack_wo_type(client):
    stack_dir = BUNDLES + 'stack_wo_type'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'No type in object definition:')


def test_stack_unknown_type(client):
    stack_dir = BUNDLES + 'unknown_type'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'Unknown type')


def test_yaml_parser_error(client):
    stack_dir = BUNDLES + 'yaml_parser_error'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)
    errorcodes.STACK_LOAD_ERROR.equal(e, 'YAML decode')


def test_toml_parser_error(client):
    stack_dir = BUNDLES + 'toml_parser_error'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)
    errorcodes.STACK_LOAD_ERROR.equal(e, 'TOML decode')


def test_stack_hasnt_script_mandatory_key(client):
    stack_dir = BUNDLES + 'script_mandatory_key'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.DEFINITION_KEY_ERROR.equal(e, 'has no mandatory \"script\"')


def test_stack_hasnt_scripttype_mandatory_key(client):
    stack_dir = BUNDLES + 'scripttype_mandatory_key'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.DEFINITION_KEY_ERROR.equal(e, 'has no mandatory \"script_type\"')


def test_playbook_path(client):
    stack_dir = BUNDLES + 'playbook_path_test'

    steps.upload_bundle(client, stack_dir)
    assert client.stack.service.list() is not None


def test_empty_default_config_value(client):
    stack_dir = BUNDLES + 'empty_default_config_value'
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)
    errorcodes.CONFIG_VALUE_ERROR.equal(e, 'Default value of config key', 'should be not empty')


def test_load_stack_w_empty_config_field(client):
    stack_dir = BUNDLES + 'empty_config_field'

    steps.upload_bundle(client, stack_dir)
    cluster_proto = client.stack.cluster.list()[0]
    schema = json.load(open(SCHEMAS + '/stack_list_item_schema.json'))

    assert validate(cluster_proto, schema) is None


def test_yaml_decode_duplicate_anchor(client):
    stack_dir = BUNDLES + 'yaml_decode_duplicate_anchor'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)
    errorcodes.STACK_LOAD_ERROR.equal(e, 'found duplicate anchor')


def test_raises_error_expected_colon(client):
    stack_dir = BUNDLES + 'expected_colon'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)
    errorcodes.STACK_LOAD_ERROR.equal(e, 'could not find expected \':\'')


def test_shouldn_load_config_with_wrong_name(client):
    stack_dir = BUNDLES + 'parsing_scalar_wrong_name'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.WRONG_NAME.equal(e, 'Config key', ' is incorrect')


def test_load_stack_with_lost_whitespace(client):
    stack_dir = BUNDLES + 'missed_whitespace'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.STACK_LOAD_ERROR.equal(e, 'mapping values are not allowed here')


def test_load_stack_expected_block_end(client):

    stack_dir = BUNDLES + 'expected_block_end'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)
    errorcodes.STACK_LOAD_ERROR.equal(e, 'expected <block end>, but found \'-\'')


def test_load_stack_wo_type_in_config_key(client):

    stack_dir = BUNDLES + 'no_type_in_config_key'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.INVALID_CONFIG_DEFINITION.equal(e, 'No type in config key')


def test_when_config_has_incorrect_option_definition(client):

    stack_dir = BUNDLES + 'incorrect_option_definition'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.STACK_LOAD_ERROR.equal(e, 'found unhashable key')


def test_when_config_has_two_identical_service_proto(client):

    stack_dir = BUNDLES + 'two_identical_services'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'Duplicate definition of service')


@pytest.mark.parametrize('entity', [('host'), ('provider')])
def test_config_has_one_definition_and_two_diff_types(client, entity):

    stack_dir = BUNDLES + 'cluster_has_a_' + entity + '_definition'
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.BUNDLE_ERROR.equal(e, entity + ' definition in cluster type bundle')
    # TODO: Fix assertion after completed ADCM-146


@pytest.mark.skip(reason="no way of currently testing this")
def test_add_config_parameter_in_cluster_proto_and_update(client):
    volumes = {BUNDLES + 'add_param_in_cluster_proto': {'bind': '/adcm/stack/', 'mode': 'rw'}}

    path = next(iter(volumes))
    config = path + '/config.yaml'
    updated = path + '/updated_config.yaml'

    # Load default stack
    client.stack.load.update()
    proto_list = client.stack.cluster.list()
    # Rename files
    os.rename(config, path + '/config.bak')
    os.rename(updated, config)
    client.stack.load.update()
    updated_cluster = client.stack.cluster.read(prototype_id=proto_list[0]['id'])
    expected = [d['name'] for d in updated_cluster['config']]
    assert ('test_key' in expected) is True


@pytest.mark.skip(reason="no way of currently testing this")
def test_add_config_parameter_in_host_proto_and_update(client):
    volumes = {BUNDLES + 'add_param_in_host_proto': {'bind': '/adcm/stack/', 'mode': 'rw'}}

    path = next(iter(volumes))
    config = path + '/config.yaml'
    updated = path + '/updated_config.yaml'

    client.stack.load.update()
    proto_list = client.stack.host.list()
    os.rename(config, path + '/config.bak')
    os.rename(updated, config)
    client.stack.load.update()
    updated_proto = client.stack.host.read(prototype_id=proto_list[0]['id'])
    expected = [d['name'] for d in updated_proto['config']]
    assert ('test_key' in expected) is True


@pytest.mark.skip(reason="no way of currently testing this")
def test_add_config_parameter_in_service_prototype_and_update(client):
    volumes = {BUNDLES + 'add_param_in_service_proto': {'bind': '/adcm/stack/', 'mode': 'rw'}}
    path = next(iter(volumes))
    config = path + '/config.yaml'
    updated = path + '/updated_config.yaml'

    client.stack.load.update()
    proto_list = client.stack.service.list()
    os.rename(config, path + '/config.bak')
    os.rename(updated, config)
    client.stack.load.update()
    updated_proto = client.stack.service.read(service_id=proto_list[0]['id'])
    expected = [d['name'] for d in updated_proto['config']]
    assert ('test_key' in expected) is True


def test_check_cluster_bundle_versions_as_a_string(client):

    stack_dir = BUNDLES + 'cluster_service_versions_as_a_string'

    steps.upload_bundle(client, stack_dir)

    assert isinstance(random.choice(client.stack.service.list())['version'], str) is True
    assert isinstance(random.choice(client.stack.cluster.list())['version'], str) is True


def test_check_host_bundle_versions_as_a_string(client):

    stack_dir = BUNDLES + 'host_version_as_a_string'

    steps.upload_bundle(client, stack_dir)

    assert isinstance(random.choice(client.stack.host.list())['version'], str) is True


def test_cluster_bundle_can_be_on_any_level(client):

    stack_dir = BUNDLES + 'cluster_bundle_on_any_level'

    steps.upload_bundle(client, stack_dir)

    assert (client.stack.service.list() is not None) is True
    assert (client.stack.cluster.list() is not None) is True


def test_host_bundle_can_be_on_any_level(client):

    stack_dir = BUNDLES + 'host_bundle_on_any_level'

    steps.upload_bundle(client, stack_dir)

    assert client.stack.host.list() is not None


@allure.issue('https://jira.arenadata.io/browse/ADCM-184')
def test_cluster_config_without_required_parent_key(client):

    stack_dir = BUNDLES + 'cluster_config_without_required_parent_key'

    steps.upload_bundle(client, stack_dir)
    cluster = client.cluster.create(
        prototype_id=random.choice(client.stack.cluster.list())['id'],
        name='cluster')
    config = client.cluster.config.history.create(cluster_id=cluster['id'],
                                                  description='desc',
                                                  config={"str-key": "string"})
    expected = client.cluster.config.current.list(cluster_id=cluster['id'])

    assert expected == config


def test_cluster_bundle_definition_shouldnt_contain_host(client):

    stack_dir = BUNDLES + 'cluster_bundle_with_host_definition'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.BUNDLE_ERROR.equal(e, 'There are 1 host definition in cluster type')


def test_when_cluster_config_must_contains_some_subkeys(client):

    stack_dir = BUNDLES + 'cluster_config_with_empty_subkeys'

    steps.upload_bundle(client, stack_dir)
    bad_config = {"str-key": "bluh", "subkeys": {}}
    cluster = client.cluster.create(
        prototype_id=random.choice(client.stack.cluster.list())['id'],
        name=utils.random_string())

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        client.cluster.config.history.create(cluster_id=cluster['id'],
                                             description=utils.random_string(),
                                             config=bad_config)

    errorcodes.CONFIG_KEY_ERROR.equal(e, 'should contains some subkeys')


def test_when_host_config_must_contains_some_subkeys(client):

    stack_dir = BUNDLES + 'host_config_with_empty_subkeys'

    steps.upload_bundle(client, stack_dir)
    bad_config = {"str-key": "bluh", "subkeys": {}}
    provider = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                      name=utils.random_string())
    host = client.host.create(prototype_id=random.choice(client.stack.host.list())['id'],
                              provider_id=provider['id'],
                              fqdn=utils.random_string())

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        client.host.config.history.create(host_id=host['id'],
                                          description=utils.random_string(),
                                          config=bad_config)

    errorcodes.CONFIG_KEY_ERROR.equal(e, 'should contains some subkeys')


def test_host_bundle_shouldnt_contains_service_definition(client):

    stack_dir = BUNDLES + 'host_bundle_with_service_definition'

    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.BUNDLE_ERROR.equal(e, 'service definition in host provider type bundle')


def test_service_job_should_run_success(client):
    stack_dir = BUNDLES + 'job_should_run_success'

    steps.upload_bundle(client, stack_dir)
    cluster = client.cluster.create(
        prototype_id=random.choice(client.stack.cluster.list())['id'],
        name=utils.random_string())
    service = client.cluster.service.create(cluster_id=cluster['id'],
                                            prototype_id=random.choice(
                                                client.stack.service.list())['id'])
    service_action_list = client.cluster.service.action.list(cluster_id=cluster['id'],
                                                             service_id=service['id'])
    action_run = client.cluster.service.action.run.create(
        action_id=service_action_list[0]['id'],
        cluster_id=cluster['id'],
        service_id=service['id'])
    utils.wait_until(client, action_run)
    job = client.job.read(job_id=action_run['id'])
    assert job['status'] == 'success'


def test_service_job_should_run_failed(client):
    stack_dir = BUNDLES + 'job_should_run_failed'

    steps.upload_bundle(client, stack_dir)
    service_proto = random.choice(client.stack.service.list())
    cluster = client.cluster.create(
        prototype_id=random.choice(client.stack.cluster.list())['id'],
        name=utils.random_string())
    service = client.cluster.service.create(cluster_id=cluster['id'],
                                            prototype_id=service_proto['id'])
    service_action_list = client.cluster.service.action.list(cluster_id=cluster['id'],
                                                             service_id=service['id'])
    action_run = client.cluster.service.action.run.create(
        action_id=service_action_list[1]['id'],
        cluster_id=cluster['id'],
        service_id=service['id'])
    utils.wait_until(client, action_run)
    job = client.job.read(job_id=action_run['id'])
    assert job['status'] == 'failed'


def test_cluster_action_run_should_be_success(client):
    stack_dir = BUNDLES + 'cluster_action_run_should_be_success'

    steps.upload_bundle(client, stack_dir)
    cluster = client.cluster.create(
        prototype_id=random.choice(client.stack.cluster.list())['id'],
        name=utils.random_string())
    cluster_action_list = client.cluster.action.list(cluster_id=cluster['id'])
    action_run = client.cluster.action.run.create(
        action_id=cluster_action_list[0]['id'],
        cluster_id=cluster['id'])
    utils.wait_until(client, action_run)
    job = client.job.read(job_id=action_run['id'])
    assert job['status'] == 'success'


def test_cluster_action_run_should_be_failed(client):
    stack_dir = BUNDLES + 'cluster_action_run_should_be_success'

    steps.upload_bundle(client, stack_dir)
    cluster = client.cluster.create(
        prototype_id=random.choice(client.stack.cluster.list())['id'],
        name=utils.random_string())
    cluster_action_list = client.cluster.action.list(cluster_id=cluster['id'])
    action_run = client.cluster.action.run.create(
        action_id=cluster_action_list[1]['id'],
        cluster_id=cluster['id'])
    utils.wait_until(client, action_run)
    job = client.job.read(job_id=action_run['id'])
    assert job['status'] == 'failed'


@pytest.mark.skip(reason="Should be fixed in https://jira.arenadata.io/browse/ADCM-1182 ")
def test_should_return_job_log_files(client):
    stack_dir = BUNDLES + 'return_job_log_files'

    steps.upload_bundle(client, stack_dir)
    cluster = client.cluster.create(
        prototype_id=random.choice(client.stack.cluster.list())['id'],
        name=utils.random_string())
    cluster_action_list = client.cluster.action.list(cluster_id=cluster['id'])
    action_run = client.cluster.action.run.create(
        action_id=cluster_action_list[0]['id'],
        cluster_id=cluster['id'])
    utils.wait_until(client, action_run)
    job = client.job.read(job_id=action_run['id'])
    log_files_list = job['log_files']

    assert log_files_list is not None
    for log in log_files_list:
        expected_file = client.job.log.read(level=log['level'], log_type=log['type'],
                                            tag=log['tag'], job_id=job['id'])
        assert expected_file['content']


def test_load_bundle_with_undefined_config_parameter(client):
    stack_dir = BUNDLES + 'param_not_defined'
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, stack_dir)

    errorcodes.INVALID_CONFIG_DEFINITION.equal(e, 'Config definition of cluster', 'should be a map')


def test_when_import_has_unknown_config_parameter_shouldnt_be_loaded(client):
    bundledir = os.path.join(BUNDLES, 'import_has_unknown_parameter')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, bundledir)
    errorcodes.INVALID_OBJECT_DEFINITION.equal(e, 'cluster ', ' does not has ', ' config group')


def test_when_bundle_hasnt_only_host_definition(client):
    bundledir = os.path.join(BUNDLES, 'host_wo_provider')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        steps.upload_bundle(client, bundledir)
    errorcodes.BUNDLE_ERROR.equal(e,
                                  "There isn't any cluster or host provider definition in bundle")
