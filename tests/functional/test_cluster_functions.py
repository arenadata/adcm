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
import os
import random
import time

import allure
import coreapi
import pytest

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker import DockerWrapper

# pylint: disable=E0401, W0601, W0611, W0621
from tests.library import errorcodes as err
from tests.library import steps

BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")


@pytest.fixture(scope="module")
def adcm(image, request):
    repo, tag = image
    dw = DockerWrapper()
    adcm = dw.run_adcm(image=repo, tag=tag, pull=False)
    adcm.api.auth(username='admin', password='admin')

    def fin():
        adcm.stop()

    request.addfinalizer(fin)
    return adcm


@pytest.fixture(scope="module")
def client(adcm):
    steps.upload_bundle(adcm.api.objects, get_data_dir(__file__, 'hostprovider_bundle'))
    steps.upload_bundle(adcm.api.objects, get_data_dir(__file__, 'cluster_bundle'))
    return adcm.api.objects


@pytest.fixture(scope="module")
def client_action_bundle(adcm):
    steps.upload_bundle(adcm.api.objects, get_data_dir(__file__, 'cluster_action_bundle'))
    return adcm.api.objects


class TestCluster:

    def test_create_cluster_wo_description(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        actual = bundle.cluster_create(utils.random_string())
        cluster_list = bundle.cluster_list()
        if cluster_list:
            for cluster in cluster_list:
                cluster_id = cluster.id
                proto_id = cluster.prototype_id
            actual.reread()
            assert actual.id == cluster_id
            assert actual.prototype_id == proto_id

    def test_create_cluster_with_description(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        actual = bundle.cluster_create(utils.random_string(), "description")
        cluster_list = bundle.cluster_list()
        if cluster_list:
            for cluster in cluster_list:
                cluster_id = cluster.id
                proto_id = cluster.prototype_id
            actual.reread()
            assert actual.id == cluster_id
            assert actual.prototype_id == proto_id
            assert cluster.description == 'description'

    def test_shouldnt_create_duplicate_cluster(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle.cluster_create("duplicate")
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            bundle.cluster_create("duplicate")
        err.CLUSTER_CONFLICT.equal(e, 'duplicate cluster')

    def test_shouldnt_create_cluster_wo_proto(self, client):
        with pytest.raises(coreapi.exceptions.ParameterError) as e:
            client.cluster.create(name=utils.random_string())
        assert str(e.value) == "{'prototype_id': 'This parameter is required.'}"
        steps.delete_all_data(client)

    def test_shouldnt_create_cluster_w_blank_prototype(self, client):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.create(prototype_id='', name=utils.random_string())
        assert e.value.error.title == '400 Bad Request'
        assert e.value.error['prototype_id'][0] == 'A valid integer is required.'
        steps.delete_all_data(client)

    def test_shouldnt_create_cluster_when_proto_is_string(self, client):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.create(prototype_id=utils.random_string(), name=utils.random_string())
        assert e.value.error.title == '400 Bad Request'
        assert e.value.error['prototype_id'][0] == 'A valid integer is required.'
        steps.delete_all_data(client)

    def test_shouldnt_create_cluster_if_proto_not_find(self, client):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.create(prototype_id=random.randint(900, 950), name=utils.random_string())
        err.PROTOTYPE_NOT_FOUND.equal(e, 'prototype doesn\'t exist')
        steps.delete_all_data(client)

    def test_shouldnt_create_cluster_wo_name(self, client):
        prototype = utils.get_random_cluster_prototype(client)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.create(prototype_id=prototype['id'], name='')
        assert e.value.error.title == '400 Bad Request'
        assert e.value.error['name'] == ['This field may not be blank.']
        steps.delete_all_data(client)

    def test_shoulndt_create_cluster_when_desc_is_null(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            bundle.cluster_create(name=utils.random_string(), description='')
        assert e.value.error.title == '400 Bad Request'
        assert e.value.error['description'] == ["This field may not be blank."]

    def test_get_cluster_list(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        expectedlist = []
        actuallist = []
        # Create list of clusters and fill expected list
        for name in utils.random_string_list():
            bundle.cluster_create(name)
            expectedlist.append(name)
        for cluster in bundle.cluster_list():
            actuallist.append(cluster.name)
        assert all([a == b for a, b in zip(actuallist, expectedlist)])

    def test_get_cluster_info(self, client):
        actual = steps.create_cluster(client)
        expected = steps.read_cluster(client, actual['id'])
        # status is a variable, so it is no good to compare it
        assert 'status' in actual
        assert 'status' in expected
        del actual['status']
        del expected['status']
        assert actual == expected
        steps.delete_all_data(client)

    def test_partial_update_cluster_name(self, client):
        name = utils.random_string()
        cluster = steps.create_cluster(client)
        with allure.step('Trying to update cluster'):
            expected = steps.partial_update_cluster(client, cluster, name)
        with allure.step('Take actual data about cluster'):
            actual = steps.read_cluster(client, cluster['id'])
        with allure.step('Check actual and expected result'):
            assert expected == actual
        steps.delete_all_data(client)

    def test_partial_update_cluster_name_and_desc(self, client):
        name = utils.random_string()
        desc = utils.random_string()
        with allure.step('Create cluster'):
            cluster = steps.create_cluster(client)
        with allure.step('Trying to update cluster name and description'):
            expected = steps.partial_update_cluster(client, cluster, name, desc)
        with allure.step('Take actual data about cluster'):
            actual = steps.read_cluster(client, cluster['id'])
        with allure.step('Check actual and expected result'):
            assert expected['name'] == name
            assert expected == actual
        steps.delete_all_data(client)

    def test_partial_update_duplicate_cluster_name(self, client):  # ADCM-74
        name = utils.random_string()
        cluster_one = steps.create_cluster(client)
        steps.partial_update_cluster(client, cluster_one, name)
        cluster_two = steps.create_cluster(client)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.partial_update_cluster(client, cluster_two, name)
        err.CLUSTER_CONFLICT.equal(e, 'cluster with name', 'already exists')
        steps.delete_all_data(client)

    def test_delete_cluster(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        expected = None
        cluster = bundle.cluster_create(utils.random_string())
        with allure.step('Delete cluster'):
            actual = cluster.delete()
        with allure.step('Check result is None'):
            assert actual == expected

    def test_should_return_correct_error_when_delete_nonexist(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        cluster = bundle.cluster_create(utils.random_string())
        cluster.delete()
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            cluster.delete()
        err.CLUSTER_NOT_FOUND.equal(e, 'cluster doesn\'t exist')

    def test_correct_error_when_user_try_to_read_nonexist_cluster(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        cluster = bundle.cluster_create(utils.random_string())
        cluster.delete()
        with allure.step('Try to get unknown cluster'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                cluster.reread()
            err.CLUSTER_NOT_FOUND.equal(e, 'cluster doesn\'t exist')

    def test_correct_error_when_user_try_to_get_incorrect_cluster(self, client):
        with allure.step('Try to get unknown cluster'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.read(cluster_id=random.randint(500, 999))
            err.CLUSTER_NOT_FOUND.equal(e, 'cluster doesn\'t exist')
        steps.delete_all_data(client)

    def test_try_to_create_cluster_with_unknown_prototype(self, client):
        with allure.step('Try to create cluster with unknown prototype'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.create(prototype_id=random.randint(100, 500),
                                      name=utils.random_string())
            err.PROTOTYPE_NOT_FOUND.equal(e, 'prototype doesn\'t exist')
        steps.delete_all_data(client)

    def test_run_cluster_action(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_action_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        cluster.config_set({"required": 10})
        cluster.service_add(name="ZOOKEEPER")
        result = cluster.action_run()
        assert result.status == 'running'


class TestClusterHost:

    def test_adding_host_to_cluster(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        hp = bundle_hp.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        with allure.step('Create mapping between cluster and host'):
            actual = cluster.host_add(host)
        with allure.step('Get cluster host info'):
            expected = cluster.host_list()[0]
        with allure.step('Check mapping'):
            assert actual.fqdn == expected.fqdn
            assert actual.id == expected.id

    def test_get_cluster_hosts_list(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        hp = bundle_hp.provider_create(utils.random_string())
        host_list = []
        actual_list = []
        with allure.step('Create host list in cluster'):
            for fqdn in utils.random_string_list():
                host = hp.host_create(fqdn)
                time.sleep(3)
                cluster.host_add(host)
                host_list.append(host.id)
        for host in cluster.host_list():
            actual_list.append(host.id)
        with allure.step('Check test data'):
            assert host_list == actual_list

    def test_get_cluster_host_info(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        hp = bundle_hp.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        with allure.step('Create mapping between cluster and host'):
            expected = cluster.host_add(host)
        with allure.step('Get cluster host info'):
            host.reread()
            actual = host
        with allure.step('Check test results'):
            assert expected.fqdn == actual.fqdn
            assert expected.host_id == actual.host_id
            assert expected.cluster_id == actual.cluster_id

    def test_delete_host_from_cluster(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        hp = bundle_hp.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        expected = cluster.host_list()
        with allure.step('Create mapping between cluster and host'):
            cluster.host_add(host)
        with allure.step('Deleting host from cluster'):
            cluster.host_delete(host)
        actual = cluster.host_list()
        with allure.step('Check host removed from cluster'):
            assert actual == expected

    def test_shouldnt_create_duplicate_host_in_cluster(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        hp = bundle_hp.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        with allure.step('Create mapping between cluster and host'):
            cluster.host_add(host)
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                cluster.host_add(host)
            err.HOST_CONFLICT.equal(e, 'duplicate host in cluster')

    def test_add_unknown_host_to_cluster(self, client):
        cluster = steps.create_cluster(client)
        with allure.step('Create mapping between cluster and unknown host'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.host.create(cluster_id=cluster['id'],
                                           host_id=random.randint(900, 950))
            err.HOST_NOT_FOUND.equal(e, 'host doesn\'t exist')
        steps.delete_all_data(client)

    def test_add_host_in_two_diff_clusters(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        with allure.step('Create cluster1'):
            cluster_one = bundle.cluster_create("cluster1")
        with allure.step('Create cluster2'):
            cluster_two = bundle.cluster_create("cluster2")
        with allure.step('Create host'):
            hp = bundle_hp.provider_create(utils.random_string())
            host = hp.host_create("new.host.net")
        with allure.step('Create mapping between cluster1 and host'):
            cluster_one.host_add(host)
        with allure.step('Try adding host to cluster2'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                cluster_two.host_add(host)
            err.FOREIGN_HOST.equal(e, 'Host', 'belong to cluster ' + str(cluster_one.id))

    def test_host_along_to_cluster_shouldnt_deleted(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        hp = bundle_hp.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        cluster.host_add(host)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            host.delete()
        err.HOST_CONFLICT.equal(e, 'Host', 'belong to cluster')


class TestClusterService:
    def test_cluster_service_create(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        cluster = bundle.cluster_create(utils.random_string())
        with allure.step('Create a new service in the cluster'):
            actual = cluster.service_add(name="ZOOKEEPER")
        with allure.step('Get service data'):
            expected = cluster.service_list()[0]
        with allure.step('Check expected and actual value'):
            assert actual.id == expected.id
            assert actual.name == expected.name

    def test_get_cluster_service_list(self, client):
        cluster = steps.create_cluster(client)
        expected = []
        with allure.step('Create a list of services in the cluster'):
            for service in client.stack.service.list():
                expected.append(client.cluster.service.create(cluster_id=cluster['id'],
                                                              prototype_id=service['id']))
        with allure.step('Get a service list in cluster'):
            actual = client.cluster.service.list(cluster_id=cluster['id'])
        with allure.step('Check expected and actual value'):
            assert expected == actual
        steps.delete_all_data(client)

    def test_shouldnt_create_service_w_id_eq_negative_number(self, client):
        cluster = steps.create_cluster(client)
        with allure.step('Try to create service with id as a negative number'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.create(
                    cluster_id=cluster['id'],
                    prototype_id=(utils.get_random_service(client)['id'] * -1))
            err.PROTOTYPE_NOT_FOUND.equal(e, 'prototype doesn\'t exist')
        steps.delete_all_data(client)

    def test_souldnt_create_service_w_id_as_string(self, client):
        cluster = steps.create_cluster(client)
        with allure.step('Try to create service with id as a negative number'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.create(cluster_id=cluster['id'],
                                              prototype_id=utils.random_string())
            assert e.value.error.title == '400 Bad Request'
            assert e.value.error['prototype_id'][0] == 'A valid integer is required.'
        steps.delete_all_data(client)

    def test_shouldnt_add_two_identical_service_in_cluster(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_simple'))
        cluster = bundle.cluster_create(utils.random_string())
        with allure.step('Create service in cluster'):
            cluster.service_add(name="ZOOKEEPER")
        with allure.step('Try to add identical service in cluster'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                cluster.service_add(name="ZOOKEEPER")
            err.SERVICE_CONFLICT.equal(e, 'service already exists in specified cluster')

    @pytest.mark.skip(reason="Task is non production right now")
    def test_that_task_generator_function_with_the_only_one_reqiured_parameter(self, client):
        cluster = steps.create_cluster(client)
        client.cluster.config.history.create(cluster_id=cluster['id'], config={"required": 10})
        with allure.step('Create service in cluster'):
            service = steps.create_random_service(client, cluster['id'])
        action = client.cluster.service.action.list(cluster_id=cluster['id'],
                                                    service_id=service['id'])
        with allure.step('Try to run service action'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.action.run.create(cluster_id=cluster['id'],
                                                         service_id=service['id'],
                                                         action_id=action[0]['id'])
            err.TASK_GENERATOR_ERROR.equal(
                e, 'task_generator() takes 1 positional argument but 2 were given')
        steps.delete_all_data(client)

    def test_cluster_action_runs_task(self, sdk_client_fs: ADCMClient):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_action_bundle'))
        cluster = bundle.cluster_create(utils.random_string())
        cluster.config_set({"required": 10})
        with allure.step('Create service in cluster'):
            cluster.service_add(name="ZOOKEEPER")
        task = cluster.action_run(name='check-file-type')
        assert task.status == 'running'
