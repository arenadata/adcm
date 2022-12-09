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

"""Tests for hostprovider functions"""

import json
import os

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils
from coreapi import exceptions
from jsonschema import validate
from tests.conftest import include_dummy_data

# pylint: disable=protected-access
from tests.library import errorcodes

BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")
SCHEMAS = os.path.join(os.path.dirname(__file__), "schemas/")


@include_dummy_data
def test_load_host_provider(sdk_client_fs: ADCMClient):
    """Test load hostprovider bundle"""
    sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")
    with allure.step("Check bundle list"):
        assert "provider_sample" in [bundle.name for bundle in sdk_client_fs.bundle_list()]


def test_validate_provider_prototype(sdk_client_fs: ADCMClient):
    """Test validate hostprovider prototype"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")
    with allure.step("Load provider prototype"):
        provider_prototype = bundle.provider_prototype()._data
        with open(SCHEMAS + '/stack_list_item_schema.json', encoding='utf_8') as file:
            schema = json.load(file)
    with allure.step("Check provider prototype"):
        assert validate(provider_prototype, schema) is None


@include_dummy_data
def test_should_create_provider_wo_description(sdk_client_fs: ADCMClient):
    """Test create provider without description"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")
    provider_name = utils.random_string()
    bundle.provider_create(name=provider_name)
    with allure.step("Check provider list"):
        assert provider_name in [provider.name for provider in sdk_client_fs.provider_list()]


def test_should_create_provider_w_description(sdk_client_fs: ADCMClient):
    """Test create provider with description"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")
    description = utils.random_string(140)
    provider = bundle.provider_create(name=utils.random_string(), description=description)
    with allure.step("Check provider with description"):
        assert provider.description == description


def test_get_provider_config(sdk_client_fs: ADCMClient):
    """Test get provider config"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")
    provider = bundle.provider_create(name=utils.random_string())
    with allure.step("Check provider config"):
        assert provider.config() is not None


@allure.link("https://jira.arenadata.io/browse/ADCM-472")
def test_provider_shouldnt_be_deleted_when_it_has_host(sdk_client_fs: ADCMClient):
    """Test delete provider with host should fail"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")
    provider = bundle.provider_create(name=utils.random_string())
    provider.host_create(fqdn=utils.random_string())
    with allure.step("Delete provider"):
        with pytest.raises(exceptions.ErrorMessage) as e:
            provider.delete()
    with allure.step("Check error"):
        errorcodes.PROVIDER_CONFLICT.equal(e, "There is host ", " of host provider ")


def test_shouldnt_create_host_with_unknown_prototype(sdk_client_fs):
    """Test create host with unknown prototype should fail"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES + "hostprovider_bundle")
    provider = bundle.provider_create(name=utils.random_string())
    with allure.step("Delete provider"):
        provider.delete()
    with allure.step("Create host"):
        with pytest.raises(exceptions.ErrorMessage) as e:
            # Using lack of auto refresh of object as workaround.
            # If adcm_client object behaviour will be changed, test may fall.
            provider.host_create(fqdn=utils.random_string())
    with allure.step("Check error provider doesn't exist"):
        errorcodes.PROVIDER_NOT_FOUND.equal(e, "provider doesn't exist")
