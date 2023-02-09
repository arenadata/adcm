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

"""Tests for host functions"""

import json
import os
import random

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, Provider
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.utils import get_data_dir
from jsonschema import validate

# pylint: disable=redefined-outer-name

SCHEMAS = os.path.join(os.path.dirname(__file__), "schemas/")


@pytest.fixture()
def provider_bundle(sdk_client_fs: ADCMClient) -> Bundle:
    """Path to provider bundle"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider_bundle"))


@pytest.fixture()
def provider(provider_bundle: Bundle) -> Provider:
    """Create provider"""
    return provider_bundle.provider_create(utils.random_string())


@pytest.fixture()
def host(provider: Provider) -> Host:
    """Create host"""
    return provider.host_create(utils.random_string())


@pytest.fixture()
def cluster_bundle(sdk_client_fs: ADCMClient):
    """Path to cluster bundle"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_bundle"))


@pytest.fixture()
def cluster(cluster_bundle: Bundle) -> Cluster:
    """Create cluster"""
    return cluster_bundle.cluster_create(utils.random_string())


class TestHost:
    """
    Basic tests for host
    """

    @pytest.mark.usefixtures("provider_bundle")
    def test_validate_host_prototype(self, sdk_client_fs: ADCMClient):
        """
        Validate provider object schema
        """
        host_prototype = sdk_client_fs.host_prototype()._data  # pylint:disable=protected-access
        with open(SCHEMAS + "/stack_list_item_schema.json", encoding="utf_8") as file:
            schema = json.load(file)
        with allure.step("Match prototype with schema"):
            assert validate(host_prototype, schema) is None

    def test_get_host_list(self, sdk_client_fs: ADCMClient, provider: Provider):
        """
        Create multiple hosts and check that all hosts was created
        """
        actual, expected = [], []
        for fqdn in utils.random_string_list():
            provider.host_create(fqdn)
            expected.append(fqdn)
        for host in sdk_client_fs.host_list():
            actual.append(host.fqdn)
        with allure.step("Check created hosts with the data from the API"):
            assert all(expected_host in actual for expected_host in expected)

    def test_create_hostcomponent(self, sdk_client_fs: ADCMClient, provider: Provider):
        """
        Check that hostcomponent is set
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_service_hostcomponent"))
        cluster = bundle.cluster_create(utils.random_string())
        host = provider.host_create(utils.random_string())
        cluster.host_add(host)
        service = cluster.service_add(name="ZOOKEEPER")
        component = service.component(name="ZOOKEEPER_CLIENT")
        cluster.hostcomponent_set((host, component))
        with allure.step("Check host component map"):
            hc_map = cluster.hostcomponent()
            assert len(hc_map) == 1
            assert hc_map[0]["host_id"] == host.id
            assert hc_map[0]["component_id"] == component.id

    def test_get_hostcomponent_list(self, cluster: Cluster, provider: Provider):
        """
        Check that hostcomponent map retrieved successfully
        """
        service = cluster.service_add(name="ZOOKEEPER")
        components = service.component_list()
        hc_map_temp = []
        for fqdn in utils.random_string_list():
            host = provider.host_create(fqdn=fqdn)
            cluster.host_add(host)
            component = random.choice(components)
            hc_map_temp.append((host, component))
        hc_map_expected = cluster.hostcomponent_set(*hc_map_temp)
        with allure.step("Check created data with data from API"):
            hc_map_actual = cluster.hostcomponent()
            assert hc_map_actual == hc_map_expected
