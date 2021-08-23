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
from typing import Optional, List

import allure

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu


class CommonConfigMenuObj(BasePageObject):
    """Class for working with configuration menu"""

    def __init__(self, driver, base_url, config_class_locators=CommonConfigMenu):
        super().__init__(driver, base_url)
        self.locators = config_class_locators

    def get_all_config_rows(self) -> List[WebElement]:
        """Return all config field rows"""
        return [r for r in self.find_elements(CommonConfigMenu.config_row) if r.is_displayed()]

    def get_config_row(self, display_name: str) -> WebElement:
        """Return config field row with provided display name"""
        row_name = f'{display_name}:'
        for row in self.get_all_config_rows():
            if self.find_child(row, CommonConfigMenu.ConfigRow.name).text == row_name:
                return row
        raise AssertionError(f'Configuration field with name {display_name} was not found')

    @allure.step('Saving configuration')
    def save_config(self):
        """Save current configuration"""
        self.find_and_click(self.locators.save_btn)
        self.wait_element_hide(self.locators.loading_text, timeout=2)

    @allure.step('Setting configuration description to {description}')
    def set_description(self, description: str) -> str:
        """Clear description field, set new value and get previous description"""
        desc = self.find_element(self.locators.description_input)
        previous_description = desc.get_property('value')
        desc.clear()
        desc.send_keys(description)
        assert (
            current_description := desc.get_property('value')
        ) == description, f'Description value should be {description}, not {current_description}'
        return previous_description

    @allure.step('Compare current configuration to {description}')
    def compare_current_to(self, description: str):
        """
        Click on history button and select compare to config option by its description
        """
        self.find_and_click(self.locators.history_btn)
        self.find_and_click(self.locators.compare_to_select)
        self.find_and_click(self.locators.config_version_option(description))
        # to hide select panel so it won't block other actions
        self.find_element(self.locators.compare_to_select).send_keys(Keys.ESCAPE)

    def config_diff_is_presented(self, value: str, adcm_test: str):
        """
        Check if `value` is listed as change of field that can be located with `adcm_test`
        """
        loc = self.locators.config_diff(adcm_test, value)
        self.wait_element_visible(loc)

    def get_input_value(
        self,
        adcm_test_attr_value: Optional[str] = None,
        row: Optional[WebElement] = None,
        *,
        is_password: bool = False,
    ) -> str:
        """
        Get value from field input

        If is_password is True, then special field is used for search
        You can't get password confirmation method

        :param adcm_test_attr_value: Value of attribute "adcm_test" to generate Locator
        :param row: Field row element
        :param is_password: Is field password/confirmation
        :returns: Value of input
        """
        if adcm_test_attr_value:
            template = (
                CommonConfigMenu.field_input
                if not is_password
                else CommonConfigMenu.password_inputs
            )
            return self.find_element(template(adcm_test_attr_value)).get_property("value")
        elif row:
            row_locators = CommonConfigMenu.ConfigRow
            locator = row_locators.value if not is_password else row_locators.password
            return self.find_child(row, locator).get_property("value")
        raise ValueError

    @allure.step('Check input of field "{adcm_test_attr_value}" has value "{expected_value}"')
    def assert_input_value_is(
        self,
        expected_value: str,
        adcm_test_attr_value: Optional[str] = None,
        row: Optional[WebElement] = None,
        *,
        is_password: bool = False,
    ):
        """
        Assert that value in field is expected_value (using retries)

        :param expected_value: Value expected to be in input field
        :param adcm_test_attr_value: Value of attribute "adcm_test" to generate Locator
        :param row: Row with required input
        :param is_password: Is field password/confirmation
        """
        kwargs = {
            'adcm_test_attr_value': adcm_test_attr_value,
            'row': row,
            'is_password': is_password,
        }

        def assert_value():

            input_value = self.get_input_value(**kwargs)

            assert (
                expected_value == input_value
            ), f'Expected value was {expected_value} but presented is {input_value}'

        wait_until_step_succeeds(assert_value, timeout=4, period=0.5)

    def reset_to_default(self, adcm_test: Optional[str] = None, row: Optional[WebElement] = None):
        """Click reset button"""
        if adcm_test:
            self.find_and_click(self.locators.reset_btn(adcm_test))
        elif row:
            self.find_child(row, CommonConfigMenu.ConfigRow.reset_btn).click()
        else:
            raise ValueError('Either adcm_test or row should be passed')

    @allure.step('Type "{value}" into config field')
    def type_in_config_field(
        self,
        value: str,
        adcm_test: Optional[str] = None,
        row: Optional[WebElement] = None,
        *,
        clear: bool = False,
    ):
        """
        Send keys to config value input

        :param value: keys to send
        :param adcm_test: value of @adcm_test required for finding input
        :param row: Config field row
        :param clear: clean input before sending keys or not
        """
        if adcm_test:
            field = self.find_element(self.locators.field_input(adcm_test))
        elif row:
            field = self.find_child(row, self.locators.ConfigRow.value)
        else:
            raise AssertionError('Either adcm_test or row should not be None')
        if clear:
            field.clear()
        field.send_keys(value)

    @allure.step(
        "Filling in {adcm_test} field's password {password} and confirmation {confirmation}"
    )
    def fill_password_and_confirm_fields(self, password: str, confirmation: str, adcm_test: str):
        """
        Fill password in clean fields and confirm password fields
        """
        # there are invisible inputs, so we need special locator
        # if field is not empty or isn't required it can behave not so predictably
        password_input = self.find_elements(self.locators.password_inputs(adcm_test))[0]
        password_input.send_keys(password)
        confirm_input = self.find_elements(self.locators.password_inputs(adcm_test))[1]
        confirm_input.send_keys(confirmation)

    @allure.step('Click on group {title}')
    def click_on_group(self, title: str):
        """Click on group with given title"""
        self.find_and_click(self.locators.group_btn(title))

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

    @allure.step("Get row history")
    def get_history_in_row(self, row: WebElement):
        return [h.text for h in self.find_children(row, CommonConfigMenu.ConfigRow.history)]

    @allure.step("Wait row with history value {value}")
    def wait_history_row_with_value(self, row: WebElement, value: str):
        def assert_value():
            assert self.get_history_in_row(row)[0] == value, "History row should contain old value"

        wait_until_step_succeeds(assert_value, timeout=4, period=0.5)
