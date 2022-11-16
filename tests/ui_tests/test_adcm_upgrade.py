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

"""Check that ADCM works correctly after upgrade"""

import threading
from typing import Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.bundle_list.page import BundleListPage
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.page.profile.page import ProfilePage
from tests.upgrade_utils import upgrade_adcm_version


def old_adcm_image() -> Tuple[str, str]:
    """Get previous ADCM version"""
    return parametrized_by_adcm_version(adcm_min_version="2021.03.10")[0][-1]


def wait_info_popup_contains(page: BasePageObject, text: str):
    """Wait for popup to be the one that's expected"""
    try:
        assert (popup_text := page.get_info_popup_text()) == text, f'Text in popup should be {text}, not {popup_text}'
    except StaleElementReferenceException:
        # popups changes fast, so `get_info_popup_text` can get error during text extraction
        pass
    except TimeoutException as e:
        # for `wait_until_step_succeeds` to correctly handle situation when popup is not presented
        raise AssertionError('Popup element was not found') from e


@allure.step('Check tabs opens correctly')
def open_different_tabs(page: AdminIntroPage):
    """Open different tabs (cluster list, bundle list, profile page)"""
    page.header.click_clusters_tab_in_header()
    ClusterListPage(page.driver, page.base_url).wait_page_is_opened()
    page.header.click_bundles_tab_in_header()
    BundleListPage(page.driver, page.base_url).wait_page_is_opened()
    page.header.open_profile()
    ProfilePage(page.driver, page.base_url).wait_page_is_opened()


@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize("image", [old_adcm_image()], ids=repr)
def test_upgrade_adcm(
    app_fs: ADCMTest,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    adcm_image_tags: Tuple[str, str],
):
    """
    Login to ADCM (previous version)
    Upgrade ADCM
    Check messages about ADCM upgrade
    Check that user is still logged in (open different tabs)
    """
    credentials = {**adcm_api_credentials}
    credentials['username'] = credentials.pop('user')
    with allure.step('Login to ADCM with UI'):
        login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login_page.login_user(**credentials)
        intro_page = AdminIntroPage(login_page.driver, login_page.base_url)
        intro_page.wait_page_is_opened()
        intro_page.wait_config_loaded()
    with allure.step('Start ADCM upgrade with client'):
        upgrade_thread = threading.Thread(
            target=upgrade_adcm_version, args=(app_fs.adcm, sdk_client_fs, adcm_api_credentials, adcm_image_tags)
        )
        upgrade_thread.start()
    with allure.step('Check update popup messages are present'):
        for message in (
            'Connection lost. Recovery attempt.',
            'No connection to back-end. Check your internet connection.',
            'New version available. Page has been refreshed.',
        ):
            with allure.step(f'Check message "{message}" is presented'):
                wait_until_step_succeeds(
                    wait_info_popup_contains, page=intro_page, text=message, timeout=30, period=0.3
                )
    with allure.step('Wait for upgrade to finish'):
        upgrade_thread.join(timeout=60)
    open_different_tabs(intro_page)
