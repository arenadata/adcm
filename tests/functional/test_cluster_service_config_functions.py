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
from adcm_pytest_plugin.docker_utils import DockerWrapper
from jsonschema import validate

# pylint: disable=E0401, W0601, W0611, W0621
from tests.library import errorcodes as err
from tests.library import steps
from tests.library.utils import (
    get_random_service,
    get_random_cluster_service_component,
    get_action_by_name, wait_until
)

BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")
SCHEMAS = os.path.join(os.path.dirname(__file__), "schemas/")


@pytest.fixture(scope="module")
def adcm(image, request, adcm_credentials):
    repo, tag = image
    dw = DockerWrapper()
    adcm = dw.run_adcm(image=repo, tag=tag, pull=False)
    adcm.api.auth(**adcm_credentials)
    yield adcm
    adcm.stop()


@pytest.fixture(scope="module")
def client(adcm):
    steps.upload_bundle(adcm.api.objects, BUNDLES + "cluster_bundle")
    steps.upload_bundle(adcm.api.objects, BUNDLES + "hostprovider_bundle")
    return adcm.api.objects


class TestClusterServiceConfig:
    def test_create_cluster_service_config(self, client):
        cluster = steps.create_cluster(client)
        cfg_json = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                    "zoo.cfg": {"autopurge.purgeInterval": 30, "dataDir": "/dev/0", "port": 80},
                    "required-key": "value"}
        with allure.step('Create service'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Create config'):
            config = client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                                  service_id=cluster_svc['id'],
                                                                  description='simple desc',
                                                                  config=cfg_json)
        with allure.step('Check created config'):
            expected = client.cluster.service.config.history.read(cluster_id=cluster['id'],
                                                                  service_id=cluster_svc['id'],
                                                                  version=config['id'])
            assert config == expected
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_not_json(self, client):
        cluster = steps.create_cluster(client)
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config from non-json string'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=utils.random_string())
        with allure.step('Check error that config should not be just one string'):
            err.JSON_ERROR.equal(e, 'config should not be just one string')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_is_number(self, client):  # ADCM-86
        cluster = steps.create_cluster(client)
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config from a number'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=random.randint(0, 9))
        with allure.step('Check error that config should not be just one int or float'):
            err.JSON_ERROR.equal(e, 'should not be just one int or float')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_doesnt_have_one_req_sub(self, client):
        cluster = steps.create_cluster(client)
        config_wo_required_sub = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                  "zoo.cfg": {"autopurge.purgeInterval": 34},
                                  "required-key": "110"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when config doesn\'t have required'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_wo_required_sub)
        with allure.step('Check error about no required subkey'):
            err.CONFIG_KEY_ERROR.equal(e, 'There is no required subkey')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_doesnt_have_one_req_key(self, client):
        cluster = steps.create_cluster(client)
        config_wo_required_key = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                  "zoo.cfg": {"autopurge.purgeInterval": 34,
                                              "dataDir": "/zookeeper", "port": 80}}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config without required key'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_wo_required_key)
        with allure.step('Check error about no required key'):
            err.CONFIG_KEY_ERROR.equal(e, 'There is no required key')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_parameter_is_not_integer(self, client):
        cluster = steps.create_cluster(client)
        config_w_illegal_param = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                  "zoo.cfg": {"autopurge.purgeInterval": "blabla",
                                              "dataDir": "/zookeeper", "port": 80},
                                  "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when parameter is not integer'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_w_illegal_param)
        with allure.step('Check error that parameter is not integer'):
            err.CONFIG_VALUE_ERROR.equal(e, 'should be integer')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_parameter_is_not_float(self, client):
        cluster = steps.create_cluster(client)
        config_w_illegal_param = {"ssh-key": "TItbmlzHyNTAAIbmzdHAyNTYAAA", "float-key": "blah",
                                  "zoo.cfg": {"autopurge.purgeInterval": 30,
                                              "dataDir": "/zookeeper", "port": 80},
                                  "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when param is not float'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_w_illegal_param)
        with allure.step('Check error that parameter is not float'):
            err.CONFIG_VALUE_ERROR.equal(e, 'should be float')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_parameter_is_not_string(self, client):
        cluster = steps.create_cluster(client)
        config_w_illegal_param = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTY", "float-key": 5.7,
                                  "zoo.cfg": {"autopurge.purgeInterval": 30,
                                              "dataDir": "/zookeeper", "port": 80},
                                  "required-key": 500}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when param is not float'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_w_illegal_param)
        with allure.step('Check error that parameter is not string'):
            err.CONFIG_VALUE_ERROR.equal(e, 'should be string')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_parameter_is_not_in_option_list(self, client):
        cluster = steps.create_cluster(client)
        config_w_illegal_param = {"ssh-key": "TItbmlzdHAyNTYAIbmlzdHAyNTYAAA", "float-key": 4.5,
                                  "zoo.cfg": {"autopurge.purgeInterval": 30,
                                              "dataDir": "/zookeeper", "port": 500},
                                  "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config has not option in a list'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_w_illegal_param)
        with allure.step('Check CONFIG_VALUE_ERROR'):
            assert e.value.error.title == '400 Bad Request'
            assert e.value.error['code'] == 'CONFIG_VALUE_ERROR'
            assert ('not in option list' in e.value.error['desc']) is True
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_integer_param_bigger_than_boundary(self, client):
        cluster = steps.create_cluster(client)
        config_int_bigger_boundary = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                      "zoo.cfg": {"autopurge.purgeInterval": 999,
                                                  "dataDir": "/zookeeper", "port": 80},
                                      "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when integer bigger than boundary'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_int_bigger_boundary)
        with allure.step('Check error that integer bigger than boundary'):
            err.CONFIG_VALUE_ERROR.equal(e, 'Value', 'should be less than')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_integer_param_less_than_boundary(self, client):
        cluster = steps.create_cluster(client)
        config_int_less_boundary = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                    "zoo.cfg": {"autopurge.purgeInterval": 0,
                                                "dataDir": "/zookeeper", "port": 80},
                                    "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when integer less than boundary'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_int_less_boundary)
        with allure.step('Check error that integer less than boundary'):
            err.CONFIG_VALUE_ERROR.equal(e, 'Value', 'should be more than')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_float_param_bigger_than_boundary(self, client):
        cluster = steps.create_cluster(client)
        config_float_bigger_boundary = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                        "zoo.cfg": {"autopurge.purgeInterval": 24,
                                                    "dataDir": "/zookeeper", "port": 80},
                                        "float-key": 50.5, "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when float bigger than boundary'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_float_bigger_boundary)
        with allure.step('Check error that float bigger than boundary'):
            err.CONFIG_VALUE_ERROR.equal(e, 'Value', 'should be less than')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_float_param_less_than_boundary(self, client):
        cluster = steps.create_cluster(client)
        config_float_less_boundary = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                      "zoo.cfg": {"autopurge.purgeInterval": 24,
                                                  "dataDir": "/zookeeper", "port": 80},
                                      "float-key": 3.3, "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when float less than boundary'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_float_less_boundary)
        with allure.step('Check error that float less than boundary'):
            err.CONFIG_VALUE_ERROR.equal(e, 'Value', 'should be more than')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_doesnt_have_all_req_param(self, client):
        cluster = steps.create_cluster(client)
        config_wo_required_param = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config when config doesnt have all params'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_wo_required_param)
        with allure.step('Check error about params'):
            err.CONFIG_KEY_ERROR.equal(e)
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_have_unknown_subkey(self, client):
        cluster = steps.create_cluster(client)
        config_w_unknown_subkey = {"ssh-key": "TItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAA",
                                   "zoo.cfg": {"autopurge.purgeInterval": 24,
                                               "dataDir": "/zookeeper", "portium": "http"},
                                   "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config with unknown subkey'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_w_unknown_subkey)
        with allure.step('Check error about unknown subkey'):
            err.CONFIG_KEY_ERROR.equal(e, 'There is unknown subkey')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_have_unknown_param(self, client):
        cluster = steps.create_cluster(client)
        config_w_unknown_param = {"name": "foo"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config with unknown parameter'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_w_unknown_param)
        with allure.step('Check error about unknown key'):
            err.CONFIG_KEY_ERROR.equal(e, 'There is unknown key')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_key_shouldnt_have_any_subkeys(self, client):
        cluster = steps.create_cluster(client)
        config_shouldnt_have_subkeys = {"ssh-key": {"key": "value"},
                                        "zoo.cfg": {"autopurge.purgeInterval": "24",
                                                    "dataDir": "/zookeeper", "port": "http"}}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config where param shouldn\'t have any subkeys'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config_shouldnt_have_subkeys)
        with allure.step('Check error about unknown subkey'):
            err.CONFIG_KEY_ERROR.equal(e, 'input config should not have any subkeys')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_try_to_put_dictionary_in_flat_key(self, client):
        cluster = steps.create_cluster(client)
        config = {"ssh-key": "as32fKj14fT88",
                  "zoo.cfg": {"autopurge.purgeInterval": 24, "dataDir": "/zookeeper",
                              "port": {"foo": "bar"}}, "required-key": "value"}
        with allure.step('Create service on the cluster'):
            cluster_svc = client.cluster.service.create(
                cluster_id=cluster['id'], prototype_id=get_random_service(client)['id'])
        with allure.step('Try to create config where in flat param we put a dictionary'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                             service_id=cluster_svc['id'],
                                                             config=config)
        with allure.step('Check error about flat param'):
            err.CONFIG_VALUE_ERROR.equal(e, 'should be flat')
        steps.delete_all_data(client)

    def test_when_delete_host_all_children_cannot_be_deleted(self, client):
        # Should be faild if random service has not components
        cluster = steps.create_cluster(client)
        with allure.step('Create provider'):
            provider = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                              name=utils.random_string())
        with allure.step('Create host'):
            host = client.host.create(prototype_id=client.stack.host.list()[0]['id'],
                                      provider_id=provider['id'],
                                      fqdn=utils.random_string())
        steps.add_host_to_cluster(client, host, cluster)
        with allure.step('Create random service'):
            service = steps.create_random_service(client, cluster['id'])
        with allure.step('Create random service component'):
            component = get_random_cluster_service_component(client, cluster, service)
        with allure.step('Create hostcomponent'):
            steps.create_hostcomponent_in_cluster(client, cluster, host, service, component)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.host.delete(host_id=host['id'], cluster_id=cluster['id'])
        with allure.step('Check host conflict'):
            err.HOST_CONFLICT.equal(e)

    def test_should_throws_exception_when_havent_previous_config(self, client):
        cluster = steps.create_cluster(client)
        service = steps.create_random_service(client, cluster['id'])
        with allure.step('Try to get previous version of the service config'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.service.config.previous.list(cluster_id=cluster['id'],
                                                            service_id=service['id'])
        with allure.step('Check error that config version doesn\'t exist'):
            err.CONFIG_NOT_FOUND.equal(e, 'config version doesn\'t exist')
        steps.delete_all_data(client)


class TestClusterServiceConfigHistory:
    def test_config_history_url_must_point_to_the_service_config(self, client):
        cluster = steps.create_cluster(client)
        service = steps.create_random_service(client, cluster['id'])
        config_str = {"ssh-key": "eulav", "integer-key": 23, "required-key": "10",
                      "float-key": 38.5, "zoo.cfg": {"autopurge.purgeInterval": 40,
                                                     "dataDir": "/opt/data", "port": 80}}
        i = 0
        while i < random.randint(0, 10):
            client.cluster.service.config.history.create(cluster_id=cluster['id'],
                                                         service_id=service['id'],
                                                         description=utils.random_string(),
                                                         config=config_str)
            i += 1
        history = client.cluster.service.config.history.list(cluster_id=cluster['id'],
                                                             service_id=service['id'])
        with allure.step('Check config history'):
            for conf in history:
                assert ('cluster/{0}/service/'.format(cluster['id']) in conf['url']) is True
        steps.delete_all_data(client)

    def test_get_config_from_nonexistant_cluster_service(self, client):
        cluster = steps.create_cluster(client)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.cluster.service.config.list(cluster_id=cluster['id'],
                                               service_id=random.randint(100, 500))
        with allure.step('Check error that service doesn\'t exist'):
            err.SERVICE_NOT_FOUND.equal(e, "service doesn\'t exist")
        steps.delete_all_data(client)


class TestClusterConfig:
    def test_config_history_url_must_point_to_the_cluster_config(self, client):
        cluster = steps.create_cluster(client)
        config_str = {"required": 10, "int_key": 50, "bool": False, "str-key": "eulav"}
        i = 0
        with allure.step('Create config history'):
            while i < random.randint(0, 10):
                client.cluster.config.history.create(cluster_id=cluster['id'],
                                                     description=utils.random_string(),
                                                     config=config_str)
                i += 1
            history = client.cluster.config.history.list(cluster_id=cluster['id'])
        with allure.step('Check config history'):
            for conf in history:
                assert ('api/v1/cluster/{0}/config/'.format(cluster['id']) in conf['url']) is True
        steps.delete_all_data(client)

    def test_read_default_cluster_config(self, client):
        cluster = steps.create_cluster(client)
        config = client.cluster.config.current.list(cluster_id=cluster['id'])
        if config:
            config_json = utils.ordered_dict_to_dict(config)
        with allure.step('Load schema'):
            schema = json.load(open(SCHEMAS + '/config_item_schema.json'))
        with allure.step('Check schema'):
            assert validate(config_json, schema) is None
        steps.delete_all_data(client)

    def test_create_new_config_version_with_one_req_parameter(self, client):
        cluster = steps.create_cluster(client)
        cfg = {"required": random.randint(0, 9)}
        with allure.step('Create new config'):
            new_config = client.cluster.config.history.create(cluster_id=cluster['id'], config=cfg)
        with allure.step('Create config history'):
            expected = client.cluster.config.history.read(cluster_id=cluster['id'],
                                                          version=new_config['id'])
        with allure.step('Check new config'):
            assert new_config == expected
        steps.delete_all_data(client)

    def test_create_new_config_version_with_other_parameters(self, client):
        cluster = steps.create_cluster(client)
        cfg = {"required": 99, "str-key": utils.random_string()}
        with allure.step('Create new config'):
            new_config = client.cluster.config.history.create(cluster_id=cluster['id'], config=cfg)
        with allure.step('Create config history'):
            expected = client.cluster.config.history.read(cluster_id=cluster['id'],
                                                          version=new_config['id'])
        with allure.step('Check new config'):
            assert new_config == expected
        steps.delete_all_data(client)

    def test_shouldnt_create_cluster_config_when_config_not_json(self, client):
        cluster = steps.create_cluster(client)
        with allure.step('Try to create the cluster config from non-json string'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.config.history.create(cluster_id=cluster['id'],
                                                     config=utils.random_string())
        with allure.step('Check that config should not be just one string'):
            err.JSON_ERROR.equal(e, 'config should not be just one string')
        steps.delete_all_data(client)

    def test_shouldnt_create_service_config_when_config_is_number(self, client):  # ADCM-86
        cluster = steps.create_cluster(client)
        with allure.step('Try to create config from number'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.config.history.create(cluster_id=cluster['id'],
                                                     config=random.randint(0, 9))
        with allure.step('Check that config should not be just one int or float'):
            err.JSON_ERROR.equal(e, 'config should not be just one int or float')
        steps.delete_all_data(client)

    def test_shouldnt_create_config_when_config_doesnt_have_required_key(self, client):
        cluster = steps.create_cluster(client)
        config_wo_required_key = {"str-key": "value"}
        with allure.step('Try to create config wo required key'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.config.history.create(cluster_id=cluster['id'],
                                                     config=config_wo_required_key)
        with allure.step('Check that no required key'):
            err.CONFIG_KEY_ERROR.equal(e, 'There is no required key')
        steps.delete_all_data(client)

    def test_shouldnt_create_config_when_key_is_not_in_option_list(self, client):
        cluster = steps.create_cluster(client)
        config_key_not_in_list = {"option": "bluh", "required": 10}
        with allure.step('Try to create config has not option in a list'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.config.history.create(cluster_id=cluster['id'],
                                                     config=config_key_not_in_list)
        with allure.step('Check that not in option list'):
            err.CONFIG_VALUE_ERROR.equal(e, 'Value', 'not in option list')
        steps.delete_all_data(client)

    def test_shouldnt_create_config_with_unknown_key(self, client):
        # config has key that not defined in prototype
        cluster = steps.create_cluster(client)
        config = {"new_key": "value"}
        with allure.step('Try to create config with unknown key'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.config.history.create(cluster_id=cluster['id'], config=config)
        with allure.step('Check that unknown key'):
            err.CONFIG_KEY_ERROR.equal(e, 'There is unknown key')
        steps.delete_all_data(client)

    def test_shouldnt_create_config_when_try_to_put_map_in_option(self, client):
        # we try to put key:value in a parameter with the option datatype
        cluster = steps.create_cluster(client)
        config_with_deep_depth = {"str-key": "{1bbb}", "option": {"http": "string"},
                                  "sub": {"sub1": "f"}}
        with allure.step('Try to create config with map in flat key'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.config.history.create(cluster_id=cluster['id'],
                                                     config=config_with_deep_depth)
        with allure.step('Check that input config should not have any subkeys'):
            err.CONFIG_KEY_ERROR.equal(e, 'input config should not have any subkeys')
        steps.delete_all_data(client)

    def test_get_nonexistant_cluster_config(self, client):
        # we try to get a nonexistant cluster config, test should raise exception
        with allure.step('Get cluster config from non existant cluster'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.cluster.config.list(cluster_id=random.randint(100, 500))
        with allure.step('Check that cluster doesn\'t exist'):
            err.CLUSTER_NOT_FOUND.equal(e, 'cluster doesn\'t exist')
        steps.delete_all_data(client)

    check_types = [
        ('file', 'input_file'),
        ('text', 'textarea'),
        ('password', 'password_phrase'),
    ]

    @pytest.mark.parametrize(('datatype', 'name'), check_types)
    def test_verify_that_supported_type_is(self, client, datatype, name):
        with allure.step('Create stack'):
            stack = client.stack.cluster.read(prototype_id=client.stack.cluster.list()[0]['id'])
        with allure.step('Check stack config'):
            for item in stack['config']:
                if item['name'] == name:
                    assert item['type'] == datatype
        steps.delete_all_data(client)

    def test_check_that_file_field_put_correct_data_in_file_inside_docker(self, client):
        cluster = steps.create_cluster(client)
        test_data = "lorem ipsum"
        with allure.step('Create config data'):
            config_data = utils.ordered_dict_to_dict(
                client.cluster.config.current.list(cluster_id=cluster['id'])['config'])
            config_data['input_file'] = test_data
            config_data['required'] = random.randint(0, 99)
        with allure.step('Create config history'):
            client.cluster.config.history.create(cluster_id=cluster['id'], config=config_data)
        with allure.step('Check file type'):
            action = client.cluster.action.run.create(
                action_id=get_action_by_name(client, cluster, 'check-file-type')['id'],
                cluster_id=cluster['id']
            )
            wait_until(client, action)
        with allure.step('Check that state is success'):
            expected = client.task.read(task_id=action['id'])
            assert expected['status'] == 'success'
