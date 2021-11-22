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

"""Config page PageObjects classes"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import List, Collection, Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.common_locators import ObjectPageMenuLocators
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.fields import ConfigFieldsManipulator


@dataclass
class ConfigRowInfo:
    """Information from config row on Config page"""

    name: str
    value: str


class CommonConfigMenuObj(BasePageObject):
    """Class for working with configuration menu"""

    def __init__(self, driver, base_url, config_class_locators=CommonConfigMenu):
        super().__init__(driver, base_url)
        self.locators = config_class_locators
        self.fields = ConfigFieldsManipulator(self.driver, self.base_url)

    def get_all_config_rows(self, *, displayed_only: bool = True) -> List[WebElement]:
        """Return all config field rows"""
        try:
            if displayed_only:
                return [r for r in self.find_elements(CommonConfigMenu.config_row, timeout=5) if r.is_displayed()]
            return self.find_elements(CommonConfigMenu.config_row, timeout=5)
        except TimeoutException:
            return []

    def get_config_row(self, display_name: str) -> WebElement:
        """Return config field row with provided display name"""
        row_name = f'{display_name}:' if not display_name.endswith(':') else display_name
        for row in self.get_all_config_rows():
            if self.find_child(row, CommonConfigMenu.ConfigRow.name).text == row_name:
                return row
        raise AssertionError(f'Configuration field with name {display_name} was not found')

    @allure.step('Saving configuration')
    def save_config(self, load_timeout: int = 2):
        """Save current configuration"""
        self.find_and_click(self.locators.save_btn)
        self.wait_element_hide(self.locators.loading_text, timeout=load_timeout)

    @allure.step('Setting configuration description to {description}')
    def set_description(self, description: str) -> str:
        """Clear description field, set new value and get previous description"""
        desc = self.find_element(self.locators.description_input)
        previous_description = desc.get_property('value')
        self.send_text_to_element(self.locators.description_input, description, clean_input=True)
        return previous_description

    def compare_versions(self, compare_with: str, base_compare_version: Optional[str] = None):
        """
        Click on history button and select compare to config option by its description
        """
        base_version = f'"{base_compare_version}"' if base_compare_version else 'current'
        with allure.step(f'Compare {base_version} configuration with {compare_with}'):
            self.find_and_click(self.locators.history_btn)
            if base_compare_version:
                self.find_and_click(self.locators.compare_version_select)
                base_version_option = self.locators.config_version_option(base_compare_version)
                self.find_and_click(base_version_option)
                self.wait_element_hide(base_version_option)
            self.find_and_click(self.locators.compare_to_select)
            self.find_and_click(self.locators.config_version_option(compare_with))
            # to hide select panel so it won't block other actions
            self.find_element(self.locators.compare_to_select).send_keys(Keys.ESCAPE)

    def click_on_advanced(self):
        """Click on advanced button and wait rows changed"""
        with self.wait_rows_change():
            self.find_and_click(CommonConfigMenu.advanced_label)

    def get_input_value(
        self,
        row: WebElement,
        *,
        is_password: bool = False,
    ) -> str:
        """
        Get value from field input
        If is_password is True, then special field is used for search
        You can't get password confirmation method
        :param row: Field row element
        :param is_password: Is field password/confirmation
        :returns: Value of input
        """
        row_locators = CommonConfigMenu.ConfigRow
        locator = row_locators.value if not is_password else row_locators.password
        return self.find_child(row, locator).get_property("value")

    @allure.step('Check field "{display_name}" has value "{expected_value}"')
    def assert_input_value_is(
        self,
        expected_value: str,
        display_name: str,
        *,
        is_password: bool = False,
    ):
        """
        Assert that value in field is expected_value (using retries)
        :param expected_value: Value expected to be in input field
        :param display_name: Config field display name
        :param is_password: Is field password/confirmation
        """

        def _assert_value():
            input_value = self.get_input_value(row=self.get_config_row(display_name), is_password=is_password)
            assert expected_value == input_value, f'Expected value was {expected_value} but presented is {input_value}'

        wait_until_step_succeeds(_assert_value, timeout=4, period=0.5)

    def reset_to_default(self, row: WebElement):
        """Click reset button"""
        self.find_child(row, CommonConfigMenu.ConfigRow.reset_btn).click()

    @allure.step('Type "{value}" into config field')
    def type_in_config_field(
        self,
        value: str,
        row: WebElement,
        *,
        clear: bool = False,
    ):
        """
        Send keys to config value input
        :param value: keys to send
        :param row: Config field row
        :param clear: clean input before sending keys or not
        """
        field = self.find_child(row, self.locators.ConfigRow.value)
        if clear:
            field.clear()
        field.send_keys(value)

    @allure.step("Filling in {display_name} field's password {password} and confirmation {confirmation}")
    def fill_password_and_confirm_fields(self, password: str, confirmation: str, display_name: str):
        """
        Fill password in clean fields and confirm password fields
        """
        # there are invisible inputs, so we need special locator
        # if field is not empty or isn't required it can behave not so predictably
        row = self.get_config_row(display_name)
        password_input = self.find_child(row, self.locators.ConfigRow.password)
        password_input.send_keys(password)
        confirm_input = self.find_child(row, self.locators.ConfigRow.confirm_password)
        confirm_input.send_keys(confirmation)

    @allure.step('Click on group {title}')
    def click_on_group(self, title: str):
        """Click on group with given title"""

        def _is_group_expanded(group: WebElement):
            return "expanded" in group.get_attribute("class")

        def _click_group():
            group = self.find_element(self.locators.group_btn(title))
            is_expanded = _is_group_expanded(group)
            group.click()
            assert (
                _is_group_expanded(self.find_element(self.locators.group_btn(title))) != is_expanded
            ), f"Group should be{'' if is_expanded else ' not '}expanded"

        wait_until_step_succeeds(_click_group, period=1, timeout=10)

    @allure.step('Search for {keys}')
    def search(self, keys: str):
        """Clear search and send keys"""
        search = self.find_element(self.locators.search_input)
        search.clear()
        search.send_keys(keys)

    @allure.step('Clear search')
    def clear_search(self):
        """Clear search input with button"""
        self.find_and_click(CommonConfigMenu.search_input_clear_btn)

    @allure.step("Check {name} required error is presented")
    def check_field_is_required(self, name: str):
        """
        Assert that message "Field [{name}] is required!" is presented
        """
        message = f'Field [{name}] is required!'
        self.check_element_should_be_visible(self.locators.field_error(message))

    @allure.step("Check {name} invalid error is presented")
    def check_field_is_invalid(self, name: str):
        """
        Assert that message "Field [{name}] is invalid!" is presented
        """
        message = f'Field [{name}] is invalid!'
        self.check_element_should_be_visible(self.locators.field_error(message))

    @allure.step("Check {name} confirmation error is presented")
    def check_password_confirm_required(self, name: str):
        """
        Assert that message "Confirm [{name}] is required!" is presented
        """
        message = f'Confirm [{name}] is required!'
        self.check_element_should_be_visible(self.locators.field_error(message))

    @allure.step("Check that correct fields are (in)visible")
    def check_config_fields_visibility(
        self, visible_fields: Collection[str] = (), invisible_fields: Collection[str] = ()
    ):
        """
        Checks if all provided fields meets visibility expectations.
        Collection items should be display names of config fields (not groups).
        """
        falsely_visible = set()
        visible_fields = set(visible_fields)
        for row in self.get_all_config_rows():
            if (row_name := self.find_child(row, self.locators.ConfigRow.name).text[:-1]) in invisible_fields:
                falsely_visible.add(row_name)
            elif row_name in visible_fields:
                visible_fields.remove(row_name)
        assert len(falsely_visible) == 0, f"Those fields shouldn't be visible in configuration: {falsely_visible}"
        assert len(visible_fields) == 0, f"Those fields should be visible: {visible_fields}"

    @contextmanager
    def wait_rows_change(self, expected_rows_amount: Optional[int] = None):
        """Wait changing rows amount."""

        amount_before = len(self.get_all_config_rows())
        yield

        def _wait_changing_rows_amount():
            amount_after = len(self.get_all_config_rows())
            assert amount_after != amount_before, "Amount of rows on the page hasn't changed"
            if expected_rows_amount:
                assert (
                    amount_after == expected_rows_amount
                ), f"Amount of rows on the page should be {expected_rows_amount}"

        wait_until_step_succeeds(_wait_changing_rows_amount, period=1, timeout=10)

    def get_config_row_info(self, row: WebElement):
        """Get info by row"""
        return ConfigRowInfo(
            name=self.find_child(row, CommonConfigMenu.ConfigRow.name).text,
            value=self.find_child(row, CommonConfigMenu.ConfigRow.value).get_attribute('value'),
        )

    @allure.step("Clear search input")
    def clear_search_input(self):
        """Clear search input"""
        self.find_and_click(CommonConfigMenu.search_input_clear_btn)

    def get_history_in_row(self, row: WebElement):
        """Get history roe"""
        return [h.text for h in self.find_children(row, CommonConfigMenu.ConfigRow.history)]

    @allure.step("Wait row with history value {value}")
    def wait_history_row_with_value(self, row: WebElement, value: str):
        """Wait for value in History row"""

        def _assert_value():
            assert self.get_history_in_row(row)[0] == value, "History row should contain old value"

        wait_until_step_succeeds(_assert_value, timeout=4, period=0.5)

    @allure.step('Scroll to group "{display_name}"')
    def scroll_to_group(self, display_name: str) -> WebElement:
        """Scroll to parameter group by display name"""
        return self.scroll_to(CommonConfigMenu.group_btn(display_name))

    @allure.step('Scroll to field "{display_name}"')
    def scroll_to_field(self, display_name: str) -> WebElement:
        """Scroll to parameter field by display name"""
        row = self.get_config_row(display_name)
        return self.scroll_to(element=row)

    @allure.step("Check warn icon on the left menu Configuration element")
    def check_config_warn_icon_on_left_menu(self):
        assert self.is_child_displayed(self.find_element(ObjectPageMenuLocators.config_tab), ObjectPageMenuLocators.warn_icon), "No warn icon near Configuration left menu element"

    @allure.step("Check warn icon on the left menu Import element")
    def check_import_warn_icon_on_left_menu(self):
        assert self.is_child_displayed(self.find_element(ObjectPageMenuLocators.import_tab), ObjectPageMenuLocators.warn_icon), "No warn icon near Import left menu element"

    @allure.step("Check warn icon on the left menu Host-Components element")
    def check_hostcomponents_warn_icon_on_left_menu(self):
        assert self.is_child_displayed(self.find_element(ObjectPageMenuLocators.components_tab), ObjectPageMenuLocators.warn_icon), "No warn icon near Host-Components left menu element"
