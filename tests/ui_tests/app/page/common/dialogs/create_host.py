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

"""Popup page PageObjects classes"""

from typing import Optional

import allure
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.page.common.dialogs.create_host_locators import (
    HostCreationLocators,
)
from tests.ui_tests.core.checks import check_element_is_visible
from tests.ui_tests.core.interactors import Interactor
from tests.ui_tests.core.locators import BaseLocator


class HostCreateDialog(Interactor):
    """Class for manipulating with create host popup."""

    def __init__(self, driver):
        super().__init__(driver=driver, default_timeout=1)

    @allure.step("Close popup with `Cancel` button")
    def close(self):
        """Close popup with `Cancel` button"""
        self.find_and_click(HostCreationLocators.cancel_btn)

    @allure.step("Click create host button in popup")
    def create(self):
        """Click create host button in popup"""
        self.find_and_click(HostCreationLocators.create_btn)

    @allure.step("Insert new host info '{fqdn}' in fields of opened popup")
    def set_host_info(self, fqdn: str, cluster: str | None = None):
        """Insert new host info in fields of opened popup"""
        self.send_text_to_element(HostCreationLocators.fqdn_input, fqdn)
        if cluster:
            self.choose_cluster(cluster)

    @allure.step("Add host provider")
    def upload_bundle(self, bundle_path: str):
        """
        Add new host provider
        Popup should be opened
        Popup is not closed at the end
        """
        provider_section = HostCreationLocators.Provider
        self.find_and_click(provider_section.add_btn, timeout=2)
        self.wait_element_visible(provider_section.new_provider_block)
        self.find_element(provider_section.upload_bundle_btn).send_keys(bundle_path)
        self.find_and_click(provider_section.new_provider_add_btn, timeout=2)
        self.wait_element_hide(provider_section.new_provider_block, timeout=3)

    def get_hostprovider_name(self) -> str:
        """Get chosen provider from opened new host popup"""
        return self.find_element(HostCreationLocators.Provider.chosen_provider).text

    @allure.step("Select cluster '{cluster_name}' in popup")
    def choose_cluster(self, cluster_name: str):
        """Choose and click cluster in popup"""
        self.find_and_click(HostCreationLocators.Cluster.cluster_select)
        option = HostCreationLocators.Cluster.cluster_option(cluster_name)
        self.find_element(option).click()
        self.wait_element_hide(option)
        check_element_is_visible(self, HostCreationLocators.Cluster.chosen_cluster(cluster_name))

    def wait_and_click_on_cluster_option(self, cluster_name: str, option_locator: BaseLocator):
        """Wait for cluster and click on it"""
        WDW(self._driver, self._timeout).until(
            EC.presence_of_element_located([option_locator.by, option_locator.value.format(cluster_name)]),
            message=f"Can't find cluster with name {cluster_name} in dropdown "
            f"on page {self._driver.current_url} "
            f"for {self._timeout} seconds",
        ).click()

    @allure.step("Create new host")
    def create_host(self, fqdn: str, cluster: Optional[str] = None):
        """Create host in popup"""
        self.set_host_info(fqdn, cluster)
        self.create()
        self.close()

    @allure.step("Create new provider and host")
    def create_provider_and_host(
        self,
        bundle_path: str,
        fqdn: str,
        cluster: Optional[str] = None,
    ) -> str:
        """
        Open host creation popup
        Upload bundle and create provider
        Fill in information about new host
        Create host
        Close popup
        :returns: Name of created provider
        """
        self.upload_bundle(bundle_path)
        provider_name = self.get_hostprovider_name()
        self.set_host_info(fqdn, cluster)
        self.create()
        self.close()
        # because we don't pass provider name
        return provider_name
