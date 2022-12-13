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

"""The most basic PageObject classes"""

from contextlib import contextmanager
from typing import List, Optional, Union

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW
from tests.ui_tests.app.checks import check_elements_are_displayed
from tests.ui_tests.app.core import Interactor
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.common_locators import (
    CommonLocators,
    ObjectPageLocators,
)
from tests.ui_tests.app.page.common.footer_locators import CommonFooterLocators
from tests.ui_tests.app.page.common.header_locators import (
    AuthorizedHeaderLocators,
    CommonHeaderLocators,
)
from tests.ui_tests.app.page.common.popups.locator import CommonPopupLocators
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.utils import assert_enough_rows


class BasePageObject(Interactor):
    def __init__(
        self,
        driver: WebDriver,
        base_url: str,
        path_template: str = "",
        default_page_timeout: int = 10,
        default_loc_timeout: int = 15,
        **kwargs,
    ):
        """
        :param driver: Selenium WebDriver object, drives a browser
        :param base_url: string with page base url
        :param path_template: string template with path to a specific page. Template variables passed as kwargs
        :param header: header elements manipulator
        :param footer: footer elements manipulator
        :param default_page_timeout: default timeout for actions with page, eg open page or reload
        :param default_loc_timeout: default timeout for actions with locators, eg wait to display
        """
        if any(str.isdigit(char) for char in path_template):
            raise ValueError(
                f"Path template {path_template} should not contain any digits. "
                "Please use template string and pass values as kwargs"
            )

        super().__init__(driver=driver, default_timeout=default_loc_timeout)
        self.driver = driver
        self.base_url = base_url
        self.path = path_template.format(**kwargs)
        self.default_page_timeout = default_page_timeout
        self.default_loc_timeout = default_loc_timeout
        self.header = Header(self.driver, self.default_loc_timeout)
        self.footer = Footer(self.driver, self.default_loc_timeout)
        allure.dynamic.label("page_url", path_template)

    def open(self, timeout: int = None, *, close_popup: bool = False):
        url = self.base_url + self.path

        def _open_page():
            if self.driver.current_url == url:
                return

            with allure.step(f"Open {url}"):
                self.driver.get(url)
                assert self.path in self.driver.current_url, (
                    "Page URL didn't change. " f'Actual URL: {self.driver.current_url}. Expected URL: {url}.'
                )

        with allure.step(f"Open {self.__class__.__name__}"):
            wait_until_step_succeeds(_open_page, period=0.5, timeout=timeout or self.default_page_timeout)

        if close_popup and self.is_element_displayed(
            CommonPopupLocators.block_by_text("Connection established."), timeout=5
        ):
            connection_message = "Connection established."
            with allure.step(f"Close popup with '{connection_message}' message"):
                try:
                    self.find_and_click(CommonPopupLocators.hide_btn_by_text(connection_message), timeout=2)
                except (
                    StaleElementReferenceException,
                    NoSuchElementException,
                    ElementClickInterceptedException,
                    TimeoutException,
                ):
                    pass
                self.wait_element_hide(CommonPopupLocators.block_by_text(connection_message), timeout=5)

        return self

    @allure.step("Wait url to contain path {path}")
    def wait_url_contains_path(self, path: str, timeout: int = None) -> None:
        url_timeout = timeout or self.default_page_timeout
        WDW(self.driver, url_timeout).until(
            EC.url_contains(path),
            message=f"Page with path '{path}' has not been " f"loaded for {url_timeout} seconds",
        )

    def wait_page_is_opened(self, timeout: int = None):
        """Wait for current page to be opened"""
        timeout = timeout or self.default_page_timeout

        def _assert_page_is_opened():
            assert self.path in self.driver.current_url, f'Page is not opened at path {self.path} in {timeout}'

        page_name = self.__class__.__name__.replace('Page', '')
        with allure.step(f'Wait page {page_name} is opened'):
            wait_until_step_succeeds(_assert_page_is_opened, period=0.5, timeout=timeout)
            self.wait_element_hide(CommonToolbarLocators.progress_bar, timeout=60)

    @allure.step('Wait Config has been loaded after authentication')
    def wait_config_loaded(self):
        """
        Wait for hidden elements in DOM.
        Without this waiting and after the config finally is loaded
        there will be redirection to the greeting page.
        """

        self.find_element(CommonLocators.socket, timeout=30)
        self.find_element(CommonLocators.profile, timeout=60)

    @allure.step("Close popup at the bottom of the page")
    def close_info_popup(self, popup_wait_timeout: int = 5) -> None:
        if self.is_element_displayed(CommonPopupLocators.block, timeout=popup_wait_timeout):
            self.find_and_click(CommonPopupLocators.hide_btn)
            self.wait_element_hide(CommonPopupLocators.block)

    def is_popup_presented_on_page(self, timeout: int = 5) -> bool:
        return self.is_element_displayed(CommonPopupLocators.block, timeout=timeout)

    def get_info_popup_text(self) -> str:
        self.wait_element_visible(CommonPopupLocators.block)
        return self.wait_element_visible(CommonPopupLocators.text, timeout=5).text

    @allure.step('Write text to input element: "{text}"')
    def send_text_to_element(
        self,
        element: Union[Locator, WebElement],
        text: str,
        clean_input: bool = True,
        timeout: Optional[int] = None,
    ):
        """
        Writes text to input element found by locator

        If value of input before and after is the same, then retries to send keys again,
        because sometimes text doesn't appear in input

        :param element: Locator of element to write into (should be input)
        :param text: Text to use in .send_keys method, and it's also a expected_value
        :param clean_input: Clear input before saving element or not
        :param timeout: Timeout on finding element
        """

        def _send_keys_and_check():
            if clean_input:
                self.clear_by_keys(element)
            input_element = self.find_element(element, timeout) if isinstance(element, Locator) else element
            input_element.click()
            input_element.send_keys(text)
            assert (actual_value := input_element.get_property('value')) == text, (
                f'Value of input {element.name if isinstance(element, Locator) else element.text} '
                f'expected to be "{text}", but "{actual_value}" was found'
            )

        wait_until_step_succeeds(_send_keys_and_check, period=0.5, timeout=1.5)

    @allure.step('Clear element')
    def clear_by_keys(self, element: Union[Locator, WebElement]) -> None:
        """Clears element value by keyboard."""

        def _clear():
            locator_before = element if isinstance(element, WebElement) else self.find_element(element)
            actual_value = locator_before.get_property('value')
            for _ in range(len(actual_value)):
                locator_before.send_keys(Keys.BACKSPACE)
            locator_before.send_keys(Keys.BACK_SPACE)
            locator_after = element if isinstance(element, WebElement) else self.find_element(element)
            assert locator_after.text == ""

        wait_until_step_succeeds(_clear, period=0.5, timeout=self.default_loc_timeout)

    @allure.step("Click back button in browser")
    def click_back_button_in_browser(self):
        self.driver.back()

    @allure.step("Refresh page")
    def refresh(self):
        self.driver.refresh()

    @allure.step('Scroll to element')
    def scroll_to(self, locator: Union[Locator, WebElement]) -> WebElement:
        """Scroll to element"""
        element = locator if isinstance(locator, WebElement) else self.find_element(locator)
        # Hack for firefox because of move_to_element does not scroll to the element
        # https://github.com/mozilla/geckodriver/issues/776
        if self.driver.capabilities['browserName'] == 'firefox':
            self.driver.execute_script('arguments[0].scrollIntoView(true)', element)
        action = ActionChains(self.driver)
        action.move_to_element(element).perform()
        return element


class Header(Interactor):  # pylint: disable=too-many-public-methods
    @property
    def popup_jobs_row_count(self):
        return len(self.get_job_rows_from_popup())

    @allure.step('Check elements in header for authorized user')
    def check_auth_page_elements(self):
        check_elements_are_displayed(
            self,
            [
                AuthorizedHeaderLocators.arenadata_logo,
                AuthorizedHeaderLocators.clusters,
                AuthorizedHeaderLocators.hostproviders,
                AuthorizedHeaderLocators.hosts,
                AuthorizedHeaderLocators.jobs,
                AuthorizedHeaderLocators.bundles,
                AuthorizedHeaderLocators.job_block,
                AuthorizedHeaderLocators.help_button,
                AuthorizedHeaderLocators.account_button,
            ],
        )

    @allure.step('Check elements in header for unauthorized user')
    def check_unauth_page_elements(self):
        """Check elements in header for unauthorized user"""
        self.wait_element_visible(CommonHeaderLocators.block)

        check_elements_are_displayed(
            self,
            [
                CommonHeaderLocators.arenadata_logo,
                CommonHeaderLocators.clusters,
                CommonHeaderLocators.hostproviders,
                CommonHeaderLocators.hosts,
                CommonHeaderLocators.jobs,
                CommonHeaderLocators.bundles,
            ],
        )

    @allure.step("Click arenadata logo in header")
    def click_arenadata_logo(self):
        self.find_and_click(CommonHeaderLocators.arenadata_logo)

    @allure.step("Click clusters tab in header")
    def click_clusters_tab(self):
        self.find_and_click(CommonHeaderLocators.clusters)

    @allure.step("Click hostprovider tab in header")
    def click_hostproviders_tab(self):
        self.find_and_click(CommonHeaderLocators.hostproviders)

    @allure.step("Click hosts tab in header")
    def click_hosts_tab(self):
        self.find_and_click(CommonHeaderLocators.hosts)

    @allure.step("Click jobs tab in header")
    def click_jobs_tab(self):
        self.find_and_click(CommonHeaderLocators.jobs)

    @allure.step("Click bundles tab in header")
    def click_bundles_tab(self):
        self.find_and_click(CommonHeaderLocators.bundles)

    @allure.step("Click job block in header")
    def click_job_block(self):
        self.find_and_click(AuthorizedHeaderLocators.job_block)

    @allure.step("Click help button in header")
    def click_help_button(self):
        self.find_and_click(AuthorizedHeaderLocators.help_button)

    @allure.step("Click account button in header")
    def click_account_button(self):
        self.find_and_click(AuthorizedHeaderLocators.account_button)

    @allure.step("Assert job popup is displayed")
    def check_job_popup(self):
        assert self.is_element_displayed(AuthorizedHeaderLocators.job_popup), 'Job popup should be displayed'

    @allure.step("Assert help popup elements are displayed")
    def check_help_popup(self):
        """Assert help popup elements are displayed"""
        self.wait_element_visible(AuthorizedHeaderLocators.block)
        check_elements_are_displayed(
            self,
            [
                AuthorizedHeaderLocators.HelpPopup.ask_link,
                AuthorizedHeaderLocators.HelpPopup.doc_link,
            ],
        )

    @allure.step("Click ask link in help popup")
    def click_ask_link_in_help_popup(self):
        """Click ask link in help popup"""
        self.find_and_click(AuthorizedHeaderLocators.HelpPopup.ask_link)

    @allure.step("Click doc link in help popup")
    def click_doc_link_in_help_popup(self):
        """Click doc link in help popup"""
        self.find_and_click(AuthorizedHeaderLocators.HelpPopup.doc_link)

    def hover_logo(self):
        self.hover_element(AuthorizedHeaderLocators.arenadata_logo)

    @allure.step("Assert account elements are displayed")
    def check_account_popup(self):
        """Assert account elements are displayed"""
        self.wait_element_visible(AuthorizedHeaderLocators.block)
        acc_popup = AuthorizedHeaderLocators.AccountPopup
        check_elements_are_displayed(
            self,
            [
                acc_popup.settings_link,
                acc_popup.profile_link,
                acc_popup.logout_button,
            ],
        )

    @allure.step("Click settings link in account popup")
    def click_settings_link_in_acc_popup(self):
        """Click Settings link in account popup"""
        self.find_and_click(AuthorizedHeaderLocators.AccountPopup.settings_link)

    @allure.step("Click profile link in account popup")
    def click_profile_link_in_acc_popup(self):
        """Click Profile link in account popup"""
        self.find_and_click(AuthorizedHeaderLocators.AccountPopup.profile_link)

    @allure.step("Click logout in account popup")
    def click_logout_in_acc_popup(self):
        """Click Logout in account popup"""
        self.find_and_click(AuthorizedHeaderLocators.AccountPopup.logout_button)

    def get_success_job_amount(self) -> int:
        """Get success job amount from header"""
        self.hover_element(AuthorizedHeaderLocators.job_block)
        self.wait_element_visible(AuthorizedHeaderLocators.job_popup)
        return int(self.find_element(AuthorizedHeaderLocators.JobPopup.success_jobs).text.split("\n")[1])

    def get_in_progress_job_amount(self) -> int:
        """Get progress job amount from header"""
        self.hover_element(AuthorizedHeaderLocators.job_block)
        self.wait_element_visible(AuthorizedHeaderLocators.job_popup)
        return int(self.find_element(AuthorizedHeaderLocators.JobPopup.in_progress_jobs).text.split("\n")[1])

    def get_failed_job_amount(self) -> int:
        """Get failed job amount from header"""
        self.hover_element(AuthorizedHeaderLocators.job_block)
        self.wait_element_visible(AuthorizedHeaderLocators.job_popup)
        return int(self.find_element(AuthorizedHeaderLocators.JobPopup.failed_jobs).text.split("\n")[1])

    def wait_success_job_amount(self, expected_job_amount: int):
        """Wait for success job amount to be as expected"""

        def _wait_job():
            assert (
                self.get_success_job_amount() == expected_job_amount
            ), f"Should be {expected_job_amount} tasks in popup header"

        wait_until_step_succeeds(_wait_job, period=1, timeout=90)

    def wait_in_progress_job_amount(self, expected_job_amount: int):
        """Wait for in progress job amount to be as expected"""

        def _wait_job():
            assert (
                self.get_in_progress_job_amount() == expected_job_amount
            ), f"Should be {expected_job_amount} tasks in popup header"

        wait_until_step_succeeds(_wait_job, period=1, timeout=70)

    @allure.step('Open profile using account popup in header')
    def open_profile(self):
        """Open profile page"""
        self.click_account_button()
        self.click_profile_link_in_acc_popup()

    @allure.step('Logout using account popup in header')
    def logout(self):
        """Logout using account popup"""
        self.click_account_button()
        self.click_logout_in_acc_popup()

    @contextmanager
    def open_jobs_popup(self):
        """Open jobs popup by hovering icon and hover JOBS menu item afterwards"""
        self.hover_element(AuthorizedHeaderLocators.job_block)
        yield
        self.hover_element(AuthorizedHeaderLocators.jobs)

    def get_job_rows_from_popup(self) -> List[WebElement]:
        """Get job rows from *opened* popup"""
        self.wait_element_visible(AuthorizedHeaderLocators.job_popup)
        return self.find_elements(AuthorizedHeaderLocators.JobPopup.job_row)

    @allure.step('Click on task row {task_name}')
    def click_on_task_row_by_name(self, task_name: str):
        """Click on task row by name"""
        for task in self.find_elements(AuthorizedHeaderLocators.JobPopup.job_row):
            name = self.find_child(task, AuthorizedHeaderLocators.JobPopup.JobRow.job_name)
            if name.text == task_name:
                name.click()
                return
        raise AssertionError(f"Task with name '{task_name}' not found")

    def get_single_job_row_from_popup(self, row_num: int = 0) -> WebElement:
        """Get single job row from *opened* popup"""

        def _popup_table_has_enough_rows():
            assert_enough_rows(row_num, self.popup_jobs_row_count)

        with allure.step('Check popup table has enough rows'):
            wait_until_step_succeeds(_popup_table_has_enough_rows, timeout=5, period=0.1)
        rows = self.get_job_rows_from_popup()
        assert_enough_rows(row_num, len(rows))
        return rows[row_num]

    @allure.step('Click on all link in job popup')
    def click_all_link_in_job_popup(self):
        """Click on all link in job popup"""
        self.wait_element_visible(AuthorizedHeaderLocators.JobPopup.block)
        self.find_and_click(AuthorizedHeaderLocators.JobPopup.show_all_link)

    @allure.step('Click on "in progress" in job popup')
    def click_in_progress_in_job_popup(self):
        """Click on in progress in job popup"""
        self.wait_element_visible(AuthorizedHeaderLocators.JobPopup.block)
        self.find_and_click(AuthorizedHeaderLocators.JobPopup.in_progress_jobs)

    @allure.step('Click on "success" in job popup')
    def click_success_jobs_in_job_popup(self):
        """Click on success in job popup"""
        self.wait_element_visible(AuthorizedHeaderLocators.JobPopup.block)
        self.find_and_click(AuthorizedHeaderLocators.JobPopup.success_jobs)

    @allure.step('Click on "failed" in job popup')
    def click_failed_jobs_in_job_popup(self):
        """Click on failed in job popup"""
        self.wait_element_visible(AuthorizedHeaderLocators.JobPopup.block)
        self.find_and_click(AuthorizedHeaderLocators.JobPopup.failed_jobs)

    @allure.step('Click on acknowledge button in job popup')
    def click_acknowledge_btn_in_job_popup(self):
        """Click on acknowledge button in job popup"""
        self.wait_element_visible(AuthorizedHeaderLocators.JobPopup.block)
        self.find_and_click(AuthorizedHeaderLocators.JobPopup.acknowledge_btn)

    def get_jobs_circle_color(self):
        """Get jobs circle color"""
        return self.find_element(AuthorizedHeaderLocators.bell_icon).get_attribute("style")

    @allure.step("Check that job list is empty")
    def check_no_jobs_presented(self):
        """Check that job list is empty"""
        if not self.is_element_displayed(AuthorizedHeaderLocators.JobPopup.block):
            self.find_and_click(AuthorizedHeaderLocators.jobs)
        assert (
            "Nothing to display" in self.find_element(AuthorizedHeaderLocators.JobPopup.empty_text).text
        ), "There should be message 'Nothing to display'"

    @allure.step("Check acknowledge button not displayed")
    def check_acknowledge_btn_not_displayed(self):
        """Check acknowledge button not displayed"""
        if not self.is_element_displayed(AuthorizedHeaderLocators.JobPopup.block):
            self.find_and_click(AuthorizedHeaderLocators.jobs)
        assert not self.is_element_displayed(AuthorizedHeaderLocators.JobPopup.acknowledge_btn)


class Footer(Interactor):
    @allure.step("Check elements in footer")
    def check_all_elements(self):
        check_elements_are_displayed(
            self,
            [
                CommonFooterLocators.version_link,
                CommonFooterLocators.logo,
            ],
        )

    @allure.step("Click on version link in footer")
    def click_version_link_in_footer(self):
        self.find_and_click(CommonFooterLocators.version_link)


class BaseDetailedPage(BasePageObject):
    """General functions to get default info from detailed page of an object"""

    def get_description(self) -> str:
        """Get description from detailed object page"""
        return self.find_element(ObjectPageLocators.text).text
