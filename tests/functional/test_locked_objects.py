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
from time import sleep

import allure
import coreapi
import pytest
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker_utils import DockerWrapper

# pylint: disable=W0611, W0621
from tests.library import steps
from tests.library.errorcodes import TASK_ERROR
from tests.library.utils import get_action_by_name, filter_action_by_name, wait_until


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


@pytest.fixture()
def prepared_cluster(client):
    bundle = utils.get_data_dir(__file__, 'locked_when_action_running')
    steps.upload_bundle(client, bundle)
    return client.cluster.create(prototype_id=client.stack.cluster.list()[0]['id'],
                                 name=utils.random_string())


@pytest.fixture()
def hostprovider(client):
    steps.upload_bundle(client, utils.get_data_dir(__file__, 'host_bundle_on_any_level'))
    return steps.create_hostprovider(client)


@pytest.fixture()
def host(client):
    host_bundle = utils.get_data_dir(__file__, 'host_bundle_on_any_level')
    steps.upload_bundle(client, host_bundle)
    return steps.create_host_w_default_provider(client, 'localhost')


def test_cluster_must_be_locked_when_action_running(client, prepared_cluster):
    with allure.step('Run action: lock cluster'):
        cluster = prepared_cluster
        client.cluster.action.run.create(
            action_id=get_action_by_name(client, cluster, 'lock-cluster')['id'],
            cluster_id=cluster['id'])
    with allure.step('Check if cluster is locked'):
        assert client.cluster.read(cluster_id=cluster['id'])['state'] == 'locked'


def test_run_new_action_on_locked_cluster_must_throws_exception(client, prepared_cluster):
    with allure.step('Run action: lock cluster'):
        cluster = prepared_cluster
        lock_action = get_action_by_name(client, cluster, 'lock-cluster')
        install_action = get_action_by_name(client, cluster, 'install')
        client.cluster.action.run.create(
            action_id=lock_action['id'],
            cluster_id=cluster['id'])
    with allure.step('Run new action install'):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.action.run.create(
                action_id=install_action['id'],
                cluster_id=cluster['id'])
    with allure.step('Check error that object is locked'):
        TASK_ERROR.equal(e)
        assert "object is locked" in e.value.error['desc']


def test_service_in_cluster_must_be_locked_when_cluster_action_running(client, prepared_cluster):
    with allure.step('Run action: lock cluster'):
        cluster = prepared_cluster
        service = client.cluster.service.create(cluster_id=cluster['id'],
                                                prototype_id=client.stack.service.list()[0]['id'])
        client.cluster.action.run.create(
            action_id=get_action_by_name(client, cluster, 'lock-cluster')['id'],
            cluster_id=cluster['id'])
    with allure.step('Check if service is locked'):
        assert client.cluster.service.read(cluster_id=cluster['id'],
                                           service_id=service['id'])['state'] == 'locked'


def test_host_in_cluster_must_be_locked_when_cluster_action_running(client, prepared_cluster, host):
    with allure.step('Run action: lock cluster'):
        cluster = prepared_cluster
        client.cluster.host.create(cluster_id=cluster['id'], host_id=host['id'])
        client.cluster.action.run.create(
            action_id=get_action_by_name(client, cluster, 'lock-cluster')['id'],
            cluster_id=cluster['id'])
    with allure.step('Check if host is locked'):
        assert client.cluster.host.read(cluster_id=cluster['id'],
                                        host_id=host['id'])['state'] == 'locked'


def test_host_must_be_locked_when_host_action_running(client, host):
    with allure.step('Run action: action locker'):
        client.host.action.run.create(
            action_id=filter_action_by_name(
                client.host.action.list(host_id=host['id']), 'action-locker'
            )[0]['id'],
            host_id=host['id']
        )
    with allure.step('Check if host is locked'):
        assert client.host.read(host_id=host['id'])['state'] == 'locked'


def test_cluster_must_be_locked_when_located_host_action_running(client, prepared_cluster, host):
    with allure.step('Run action: action locker'):
        client.cluster.host.create(cluster_id=prepared_cluster['id'], host_id=host['id'])
        client.host.action.run.create(
            action_id=filter_action_by_name(
                client.host.action.list(host_id=host['id']), 'action-locker')[0]['id'],
            host_id=host['id'])
    with allure.step('Check if host and cluster are locked'):
        assert client.cluster.host.read(cluster_id=prepared_cluster['id'],
                                        host_id=host['id'])['state'] == 'locked'
        assert client.cluster.read(cluster_id=prepared_cluster['id'])['state'] == 'locked'


def test_cluster_service_locked_when_located_host_action_running(client, prepared_cluster, host):
    with allure.step('Create host and service'):
        client.cluster.host.create(cluster_id=prepared_cluster['id'], host_id=host['id'])
        service = client.cluster.service.create(cluster_id=prepared_cluster['id'],
                                                prototype_id=client.stack.service.list()[0]['id'])
    with allure.step('Run action: action locker'):
        client.host.action.run.create(
            action_id=filter_action_by_name(
                client.host.action.list(host_id=host['id']), 'action-locker')[0]['id'],
            host_id=host['id'])
    with allure.step('Check if host, cluster and service are locked'):
        assert client.cluster.host.read(cluster_id=prepared_cluster['id'],
                                        host_id=host['id'])['state'] == 'locked'
        assert client.cluster.read(cluster_id=prepared_cluster['id'])['state'] == 'locked'
        assert client.cluster.service.read(cluster_id=prepared_cluster['id'],
                                           service_id=service['id'])['state'] == 'locked'


def test_run_service_action_locked_all_objects_in_cluster(client, prepared_cluster, host):
    with allure.step('Create host and service'):
        client.cluster.host.create(cluster_id=prepared_cluster['id'], host_id=host['id'])
        service = client.cluster.service.create(cluster_id=prepared_cluster['id'],
                                                prototype_id=client.stack.service.list()[0]['id'])
    with allure.step('Run action: service lock'):
        client.cluster.service.action.run.create(
            action_id=filter_action_by_name(
                client.cluster.service.action.list(cluster_id=prepared_cluster['id'],
                                                   service_id=service['id']),
                'service-lock')[0]['id'],
            cluster_id=prepared_cluster['id'],
            service_id=service['id'])
        sleep(1)
    with allure.step('Check if host, cluster and service are locked'):
        assert client.cluster.service.read(cluster_id=prepared_cluster['id'],
                                           service_id=service['id'])['state'] == 'locked'
        assert client.cluster.read(cluster_id=prepared_cluster['id'])['state'] == 'locked'
        assert client.cluster.host.read(cluster_id=prepared_cluster['id'],
                                        host_id=host['id'])['state'] == 'locked'


def test_cluster_should_be_unlocked_when_ansible_task_killed(client, prepared_cluster):
    with allure.step('Run action: lock terminate'):
        task = client.cluster.action.run.create(
            action_id=get_action_by_name(client, prepared_cluster, 'lock-terminate')['id'],
            cluster_id=prepared_cluster['id'])
    with allure.step('Check if cluster is locked and then terminate_failed'):
        assert client.cluster.read(cluster_id=prepared_cluster['id'])['state'] == 'locked'
        wait_until(client, task)
        assert client.cluster.read(cluster_id=prepared_cluster['id'])['state'] == 'terminate_failed'


def test_host_should_be_unlocked_when_ansible_task_killed(client, prepared_cluster, host):
    with allure.step('Create host'):
        client.cluster.host.create(cluster_id=prepared_cluster['id'], host_id=host['id'])
    with allure.step('Run action: lock terminate'):
        task = client.cluster.action.run.create(
            action_id=get_action_by_name(client, prepared_cluster, 'lock-terminate')['id'],
            cluster_id=prepared_cluster['id'])
    with allure.step('Check if host is locked and then created'):
        assert client.host.read(host_id=host['id'])['state'] == 'locked'
        wait_until(client, task)
        assert client.host.read(host_id=host['id'])['state'] == 'created'


def test_service_should_be_unlocked_when_ansible_task_killed(client, prepared_cluster):
    with allure.step('Create service'):
        service = client.cluster.service.create(cluster_id=prepared_cluster['id'],
                                                prototype_id=client.stack.service.list()[0]['id'])
    with allure.step('Run action: lock terminate'):
        task = client.cluster.action.run.create(
            action_id=get_action_by_name(client, prepared_cluster, 'lock-terminate')['id'],
            cluster_id=prepared_cluster['id'])
    with allure.step('Check if service is locked and then created'):
        assert client.cluster.service.read(cluster_id=prepared_cluster['id'],
                                           service_id=service['id'])['state'] == 'locked'
        wait_until(client, task)
        assert client.cluster.service.read(cluster_id=prepared_cluster['id'],
                                           service_id=service['id'])['state'] == 'created'


def test_hostprovider_must_be_unlocked_when_his_task_finished(client, hostprovider):
    with allure.step('Run action: action locker'):
        action_id = filter_action_by_name(
            client.provider.action.list(provider_id=hostprovider['id']), 'action-locker')[0]['id']
        task = client.provider.action.run.create(
            action_id=action_id,
            provider_id=hostprovider['id']
        )
    with allure.step('Check if provider is locked and then created'):
        assert client.provider.read(provider_id=hostprovider['id'])['state'] == 'locked'
        wait_until(client, task)
        assert client.provider.read(provider_id=hostprovider['id'])['state'] == 'created'
