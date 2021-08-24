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

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import (
    ADCMClient,
    Bundle,
    Provider,
)
from adcm_pytest_plugin import utils

from tests.ui_tests.app.page.provider_list.page import ProviderListPage

# pylint: disable=redefined-outer-name,no-self-use
pytestmark = pytest.mark.usefixtures("login_to_adcm_over_api")

PROVIDER_NAME = 'test_provider'


@pytest.fixture(params=["provider"])
@allure.title("Upload provider bundle")
def provider_bundle(request: SubRequest, sdk_client_fs: ADCMClient) -> Bundle:
    return sdk_client_fs.upload_from_fs(os.path.join(utils.get_data_dir(__file__), request.param))


@pytest.fixture()
@allure.title("Create provider from uploaded bundle")
def upload_and_create_provider(provider_bundle) -> Provider:
    return provider_bundle.provider_create(PROVIDER_NAME)


class TestProviderListPage:
    @pytest.mark.parametrize(
        "bundle_archive", [pytest.param(utils.get_data_dir(__file__, "provider"), id="provider")], indirect=True
    )
    def test_create_provider_on_provider_list_page(self, app_fs, bundle_archive):
        provider_params = {
            "bundle": "test_provider 2.15-dev community",
            "state": "created",
        }
        provider_page = ProviderListPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Check no provider rows"):
            assert len(provider_page.table.get_all_rows()) == 0, "There should be no row with providers"
        provider_page.create_provider(bundle=bundle_archive)
        with allure.step("Check uploaded provider"):
            rows = provider_page.table.get_all_rows()
            assert len(rows) == 1, "There should be 1 row with providers"
            uploaded_provider = provider_page.get_provider_info_from_row(rows[0])
            assert (
                provider_params['bundle'] == uploaded_provider.bundle
            ), f"Provider bundle should be {provider_params['bundle']} and not {uploaded_provider.bundle}"
            assert (
                provider_params['state'] == uploaded_provider.state
            ), f"Provider state should be {provider_params['state']} and not {uploaded_provider.state}"

    @pytest.mark.parametrize(
        "bundle_archive", [pytest.param(utils.get_data_dir(__file__, "provider"), id="provider")], indirect=True
    )
    def test_create_custom_provider_on_provider_list_page(self, app_fs, bundle_archive):
        provider_params = {
            "name": "Test Provider",
            "description": "Test",
            "bundle": "test_provider 2.15-dev community",
            "state": "created",
        }
        provider_page = ProviderListPage(app_fs.driver, app_fs.adcm.url).open()
        provider_page.create_provider(
            bundle=bundle_archive, name=provider_params['name'], description=provider_params['description']
        )
        with allure.step("Check uploaded provider"):
            rows = provider_page.table.get_all_rows()
            uploaded_provider = provider_page.get_provider_info_from_row(rows[0])
            assert (
                provider_params['bundle'] == uploaded_provider.bundle
            ), f"Provider bundle should be {provider_params['bundle']} and not {uploaded_provider.bundle}"
            assert (
                provider_params['name'] == uploaded_provider.name
            ), f"Provider name should be {provider_params['name']} and not {uploaded_provider.name}"

    def test_check_provider_list_page_pagination(self, provider_bundle, app_fs):
        with allure.step("Create 11 providers"):
            for i in range(11):
                provider_bundle.provider_create(name=f"Test provider {i}")
        provider_page = ProviderListPage(app_fs.driver, app_fs.adcm.url).open()
        provider_page.close_info_popup()
        provider_page.table.check_pagination(second_page_item_amount=1)
