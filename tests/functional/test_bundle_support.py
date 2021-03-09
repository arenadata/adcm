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
import allure
import coreapi
import pytest
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker_utils import DockerWrapper

# pylint: disable=E0401, E0611, W0611, W0621
from tests.library import errorcodes as err
from tests.library import steps
from tests.library.utils import wait_until, filter_action_by_name


@pytest.fixture()
def adcm(image, request, adcm_credentials):
    repo, tag = image
    dw = DockerWrapper()
    adcm = dw.run_adcm(image=repo, tag=tag, pull=False)
    adcm.api.auth(**adcm_credentials)
    yield adcm
    adcm.stop()


@pytest.fixture()
def client(adcm):
    return adcm.api.objects


def test_bundle_should_have_any_cluster_definition(client):
    with allure.step('Upload cluster bundle with no definition'):
        bundle = utils.get_data_dir(__file__, "bundle_wo_cluster_definition")
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.upload_bundle(client, bundle)
    with allure.step('Check error message'):
        err.BUNDLE_ERROR.equal(e, "There isn't any cluster or host provider definition in bundle")


def test_bundle_cant_removed_when_some_object_associated_with(client):
    with allure.step('Upload cluster bundle'):
        bundle = utils.get_data_dir(__file__, "cluster_inventory_tests")
        steps.upload_bundle(client, bundle)
    with allure.step('Create cluster'):
        client.cluster.create(prototype_id=client.stack.cluster.list()[0]['id'], name=__file__)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.stack.bundle.delete(bundle_id=client.stack.bundle.list()[0]['id'])
    with allure.step('Check error message'):
        err.BUNDLE_CONFLICT.equal(e, "There is cluster", "of bundle ")


def test_bundle_can_be_removed_when_no_object_associated_with(client):
    with allure.step('Upload cluster bundle'):
        bundle = utils.get_data_dir(__file__, "cluster_inventory_tests")
        steps.upload_bundle(client, bundle)
    with allure.step('Remove cluster bundle'):
        client.stack.bundle.delete(bundle_id=client.stack.bundle.list()[0]['id'])
    with allure.step('Check cluster bundle is removed'):
        assert not client.stack.bundle.list()

# TODO: Make this test to cover ADCM-202
# def test_default_values_should_according_to_their_datatypes(client):
#     bundle = os.path.join(BUNDLES, "")


empty_bundles_fields = ['empty_success_cluster',
                        'empty_fail_cluster',
                        'empty_success_host',
                        'empty_fail_host'
                        ]


@pytest.mark.parametrize("empty_fields", empty_bundles_fields)
def test_that_check_empty_field_is(empty_fields, client):
    with allure.step('Upload cluster bundle'):
        bundle = utils.get_data_dir(__file__, "empty_states", empty_fields)
        steps.upload_bundle(client, bundle)
    with allure.step('Check cluster bundle'):
        assert client.stack.bundle.list() is not None


cluster_fields = [
    ('empty_success_cluster', 'failed'),
    ('empty_fail_cluster', 'installed'),
]


@pytest.mark.parametrize(('cluster_bundle', 'state'), cluster_fields)
def test_check_cluster_state_after_run_action_when_empty(cluster_bundle, state, client):
    with allure.step(f'Upload cluster bundle: {cluster_bundle}'):
        bundle = utils.get_data_dir(__file__, "empty_states", cluster_bundle)
        steps.upload_bundle(client, bundle)
    with allure.step('Create cluster'):
        cluster = client.cluster.create(prototype_id=client.stack.cluster.list()[0]['id'],
                                        name=utils.random_string())
    with allure.step('Run cluster'):
        action = client.cluster.action.run.create(
            action_id=filter_action_by_name(
                client.cluster.action.list(cluster_id=cluster['id']), 'install')[0]['id'],
            cluster_id=cluster['id'])
        wait_until(client, action)
    with allure.step(f'Check if cluster state is {state}'):
        assert client.cluster.read(cluster_id=cluster['id'])['state'] == state


host_fields = [
    ('empty_success_host', 'failed'),
    ('empty_fail_host', 'initiated'),
]


@pytest.mark.parametrize(('host_bundle', 'state'), host_fields)
def test_check_host_state_after_run_action_when_empty(host_bundle, state, client):
    with allure.step(f'Upload cluster bundle: {host_bundle}'):
        bundle = utils.get_data_dir(__file__, "empty_states", host_bundle)
        steps.upload_bundle(client, bundle)
    with allure.step('Create provider and host'):
        provider = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                          name=utils.random_string())
        host = client.host.create(prototype_id=client.stack.host.list()[0]['id'],
                                  provider_id=provider['id'],
                                  fqdn=utils.random_string())
    with allure.step('Run host'):
        action = client.host.action.run.create(
            action_id=filter_action_by_name(
                client.host.action.list(host_id=host['id']), 'init')[0]['id'],
            host_id=host['id'])
        wait_until(client, action)
    with allure.step(f'Check if host state is {state}'):
        assert client.host.read(host_id=host['id'])['state'] == state


def test_loading_provider_bundle_must_be_pass(client):
    with allure.step('Upload cluster bundle'):
        bundle = utils.get_data_dir(__file__, "hostprovider_loading_pass")
        steps.upload_bundle(client, bundle)
    with allure.step('Check that hostprovider loading pass'):
        host_provider = client.stack.provider.list()
        assert host_provider is not None


def test_run_parametrized_action_must_be_runned(client):
    with allure.step('Upload cluster bundle'):
        bundle = utils.get_data_dir(__file__, "run_parametrized_action")
        steps.upload_bundle(client, bundle)
    with allure.step('Create cluster'):
        cluster = client.cluster.create(prototype_id=client.stack.cluster.list()[0]['id'],
                                        name=utils.random_string())
    with allure.step('Run cluster'):
        action = client.cluster.action.run.create(
            action_id=filter_action_by_name(
                client.cluster.action.list(cluster_id=cluster['id']),
                'install')[0]['id'],
            cluster_id=cluster['id'], config={"param": "test test test test test"})
        wait_until(client, action)
    with allure.step('Check if state is success'):
        assert client.job.read(job_id=client.job.list()[0]['id'])['status'] == 'success'


state_cases = [
    ('cluster', 'on_success', 'was_dict'),
    ('cluster', 'on_success', 'was_list'),
    ('cluster', 'on_success', 'was_sequence'),
    ('cluster', 'on_fail', 'was_dict'),
    ('cluster', 'on_fail', 'was_list'),
    ('cluster', 'on_fail', 'was_sequence'),
    ('provider', 'on_success', 'was_dict'),
    ('provider', 'on_success', 'was_list'),
    ('provider', 'on_success', 'was_sequence'),
    ('provider', 'on_fail', 'was_dict'),
    ('provider', 'on_fail', 'was_list'),
    ('provider', 'on_fail', 'was_sequence'),
    ('host', 'on_success', 'was_dict'),
    ('host', 'on_success', 'was_list'),
    ('host', 'on_success', 'was_sequence'),
    ('host', 'on_fail', 'was_dict'),
    ('host', 'on_fail', 'was_list'),
    ('host', 'on_fail', 'was_sequence'),
]


@pytest.mark.parametrize(('entity', 'state', 'case'), state_cases)
def test_load_should_fail_when(client, entity, state, case):
    with allure.step(f'Upload {entity} bundle with {case}'):
        bundle = utils.get_data_dir(__file__, 'states', entity, state, case)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.upload_bundle(client, bundle)
    with allure.step(f'Check if state is {state}'):
        err.INVALID_ACTION_DEFINITION.equal(e, state, entity, 'should be string')


@allure.link('https://jira.arenadata.io/browse/ADCM-580')
def test_provider_bundle_shouldnt_load_when_has_export_section(client):
    with allure.step('Upload cluster bundle'):
        bundle = utils.get_data_dir(__file__, 'hostprovider_with_export')
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.upload_bundle(client, bundle)
    with allure.step('Check error'):
        err.INVALID_OBJECT_DEFINITION.equal(e, 'Only cluster or service can have export section')
