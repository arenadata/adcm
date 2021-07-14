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
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webdriver import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.footer import CommonFooterLocators
from tests.ui_tests.app.page.common.header import (
    CommonHeaderLocators,
    AuthorizedHeaderLocators,
)


class BasePageObject:
    """
    BasePageObject is parent class for all ADCM's pages.
    :param driver: Selenium WebDriver object, drives a browser
    :param base_url: string with page base url
    :param path: string with path to a specific page
    :param header: header object, eg PageHeader
    :param footer: footer object, eg PageFooter
    :param default_page_timeout: default timeout for actions with page, eg open page or reload
    :param default_loc_timeout: default timeout for actions with locators, eg wait to display
    """

    __slots__ = {"driver", "base_url", "path", "header", "footer", "default_page_timeout", "default_loc_timeout"}

    def __init__(
            self,
            driver: WebDriver,
            base_url: str,
            path: str = "",
            default_page_timeout: int = 10,
            default_loc_timeout: int = 15,
    ):
        self.driver = driver
        self.base_url = base_url
        self.path = path
        self.default_page_timeout = default_page_timeout
        self.default_loc_timeout = default_loc_timeout

    def open(self, timeout: int = None):
        """Open page by its url and path."""

        url = self.base_url + self.path
        if self.driver.current_url != url:
            with allure.step(f"Open {url}"):
                self.driver.get(url)
        self.wait_url_contains_path(self.path, timeout=timeout or self.default_page_timeout)
        return self

    def wait_url_contains_path(self, path: str, timeout: int = None) -> None:
        """Wait url to contain path."""

        url_timeout = timeout or self.default_page_timeout
        WDW(self.driver, url_timeout).until(EC.url_contains(path), message=f"Page with path '{path}' has not been "
                                                                           f"loaded for {url_timeout} seconds")

    def find_element(self, locator: Locator, timeout: int = None) -> WebElement:
        """Find element on current page."""

        loc_timeout = timeout or self.default_loc_timeout
        with allure.step(f'Find element "{locator.name}" on page'):
            return WDW(self.driver, loc_timeout).until(EC.presence_of_element_located([locator.by, locator.value]),
                                                       message=f"Can't find {locator.name} on page "
                                                               f"{self.driver.current_url} for {loc_timeout} seconds")

    def find_elements(self, locator: Locator, timeout: int = None) -> [WebElement]:
        """Find elements on current page."""

        loc_timeout = timeout or self.default_loc_timeout
        with allure.step(f'Find elements "{locator.name}" on page'):
            return WDW(self.driver, loc_timeout).until(EC.presence_of_all_elements_located([locator.by, locator.value]),
                                                       message=f"Can't find {locator.name} on page "
                                                               f"{self.driver.current_url} for {loc_timeout} seconds")

    def is_element_displayed(self, locator: Locator, timeout: int = None) -> bool:
        """Checks if element is displayed.
        in case you'll need to divide methods for input params element and locator use dispatch decorator
        """

        try:
            with allure.step(f'Check "{locator.name}"'):
                return self.find_element(locator, timeout=timeout or self.default_loc_timeout).is_displayed()
        except (
                TimeoutException,
                NoSuchElementException,
                StaleElementReferenceException,
                TimeoutError,
        ):
            return False

    def assert_displayed_elements(self, locators: list) -> None:
        """Asserts that list of elements is displayed."""

        for loc in locators:
            assert self.is_element_displayed(loc), f"Locator {loc.name} doesn't displayed on page"

    def find_and_click(self, locator: Locator, is_js: bool = False) -> None:
        """Find element on current page and click on it."""

        if is_js:
            with allure.step(f'Click with js on "{locator.name}"'):
                loc = self.find_element(locator)
                self.driver.execute_script("arguments[0].click()", loc)
        else:
            with allure.step(f'Click on "{locator.name}"'):
                self.wait_element_clickable(locator)
                self.find_element(locator).click()

    def wait_element_clickable(self, locator: Locator, timeout: int = None) -> WebElement:
        """Wait for the element to become clickable."""

        loc_timeout = timeout or self.default_loc_timeout
        with allure.step(f'Wait "{locator.name}" clickable'):
            return WDW(self.driver, loc_timeout).until(EC.element_to_be_clickable([locator.by, locator.value]),
                                                       message=f"locator {locator.name} hasn't become clickable for "
                                                               f"{loc_timeout} seconds")

    def wait_element_visible(self, locator: Locator, timeout: int = None) -> WebElement:
        """Wait for the element visibility."""

        loc_timeout = timeout or self.default_loc_timeout
        with allure.step(f'Wait "{locator.name}" presence'):
            return WDW(self.driver, loc_timeout).until(EC.visibility_of_element_located([locator.by, locator.value]),
                                                       message=f"locator {locator.name} hasn't become visible for "
                                                               f"{loc_timeout} seconds")

    def wait_element_hide(self, locator: Locator, timeout: int = None) -> None:
        """Wait the element to hide."""

        loc_timeout = timeout or self.default_loc_timeout
        with allure.step(f'Wait "{locator.name}" to hide'):
            WDW(self.driver, loc_timeout).until(EC.invisibility_of_element_located([locator.by, locator.value]),
                                                message=f"locator {locator.name} hasn't hide for {loc_timeout} seconds")

    def set_locator_value(self, locator: Locator, value: str) -> None:
        """Fill locator with value."""

        with allure.step(f'Set value "{value}" to "{locator.name}"'):
            element = self.wait_element_clickable(locator)
            element.click()
            element.clear()
            element.send_keys(value)

    @allure.step('Clear element')
    def clear_by_keys(self, locator: Locator) -> None:
        """Clears element value by keyboard."""
        element = self.find_element(locator)
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.BACK_SPACE)


class PageHeader(BasePageObject):
    """Class for header manipulating."""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)

    @allure.step('Check elements in header for authorized user')
    def check_auth_page_elements(self):
        self.assert_displayed_elements([
            AuthorizedHeaderLocators.arenadata_logo,
            AuthorizedHeaderLocators.clusters,
            AuthorizedHeaderLocators.hostproviders,
            AuthorizedHeaderLocators.hosts,
            AuthorizedHeaderLocators.jobs,
            AuthorizedHeaderLocators.bundles,
            AuthorizedHeaderLocators.job_block_previous,
            AuthorizedHeaderLocators.help_button,
            AuthorizedHeaderLocators.account_button,
        ])

    @allure.step('Check elements in header for unauthorized user')
    def check_unauth_page_elements(self):
        self.wait_element_visible(CommonHeaderLocators.block)
        self.assert_displayed_elements([
            CommonHeaderLocators.arenadata_logo,
            CommonHeaderLocators.clusters,
            CommonHeaderLocators.hostproviders,
            CommonHeaderLocators.hosts,
            CommonHeaderLocators.jobs,
            CommonHeaderLocators.bundles,
        ])

    def click_arenadata_logo_in_header(self):
        self.find_and_click(CommonHeaderLocators.arenadata_logo)

    def click_cluster_tab_in_header(self):
        self.find_and_click(CommonHeaderLocators.clusters)

    def click_hostproviders_tab_in_header(self):
        self.find_and_click(CommonHeaderLocators.hostproviders)

    def click_hosts_tab_in_header(self):
        self.find_and_click(CommonHeaderLocators.hosts)

    def click_jobs_tab_in_header(self):
        self.find_and_click(CommonHeaderLocators.jobs)

    def click_bundles_tab_in_header(self):
        self.find_and_click(CommonHeaderLocators.bundles)

    def click_job_block_in_header(self):
        self.find_and_click(AuthorizedHeaderLocators.job_block_previous)

    def click_help_button_in_header(self):
        self.find_and_click(AuthorizedHeaderLocators.help_button)

    def click_account_button_in_header(self):
        self.find_and_click(AuthorizedHeaderLocators.account_button)

    def check_job_popup(self):
        assert self.is_element_displayed(AuthorizedHeaderLocators.job_popup)

    def check_help_popup(self):
        help_popup = AuthorizedHeaderLocators.HelpPopup
        self.wait_element_visible(help_popup.block)
        self.assert_displayed_elements([help_popup.ask_link, help_popup.doc_link])

    def click_ask_link_in_help_popup(self):
        self.find_and_click(AuthorizedHeaderLocators.HelpPopup.ask_link)

    def click_doc_link_in_help_popup(self):
        self.find_and_click(AuthorizedHeaderLocators.HelpPopup.doc_link)


class PageFooter(BasePageObject):
    """Class for footer manipulating."""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)

    @allure.step('Check elements in footer')
    def check_all_elements(self):
        self.assert_displayed_elements([
            CommonFooterLocators.version_link,
            CommonFooterLocators.logo,
        ])
