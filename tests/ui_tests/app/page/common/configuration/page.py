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
import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Collection, List, Optional, TypeVar, Union

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.common_locators import (
    CommonLocators,
    ObjectPageLocators,
    ObjectPageMenuLocators,
)
from tests.ui_tests.app.page.common.configuration.fields import ConfigFieldsManipulator
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.core.checks import check_element_is_hidden, check_element_is_visible

# pylint: disable=too-many-public-methods

T = TypeVar("T")


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

    @property
    def rows_amount(self) -> int:
        return len(self.get_all_config_rows())

    def get_all_config_rows(self, *, displayed_only: bool = True, timeout: int = 5) -> List[WebElement]:
        """Return all config field rows"""

        try:
            if displayed_only:
                return [r for r in self.find_elements(CommonConfigMenu.config_row, timeout=timeout) if r.is_displayed()]
            return self.find_elements(CommonConfigMenu.config_row, timeout=timeout)
        except TimeoutException:
            return []

    def get_all_config_rows_names(self, *, displayed_only: bool = True) -> List[WebElement]:
        """Return all config field rows names"""
        # TODO it is a very special method for testing config hell
        #  so we can't just return []
        #  maybe here isn't a good place for it or we need a better check in config hell test
        try:
            self.wait_element_visible(CommonConfigMenu.config_row, timeout=120)
        except TimeoutException as exc:
            raise AssertionError("Config menu fields don't appear in time") from exc
        return [
            self.find_child(r, CommonConfigMenu.ConfigRow.name, timeout=2).text.rstrip(":")
            for r in self.get_all_config_rows(displayed_only=displayed_only)
        ]

    def get_config_row(self, display_name: str) -> WebElement:
        """Return config field row with provided display name"""

        row_name = f'{display_name}:' if not display_name.endswith(':') else display_name
        for row in self.get_all_config_rows():
            if self.find_child(row, CommonConfigMenu.ConfigRow.name).text == row_name:
                return row
        raise AssertionError(f"Configuration field with name {display_name} was not found")

    def get_textbox_rows(self, timeout=2) -> List[WebElement]:
        """Get textbox elements from the page"""
        try:
            return [r for r in self.find_elements(CommonConfigMenu.text_row, timeout=timeout) if r.is_displayed()]
        except TimeoutException:
            return []

    @allure.step("Saving configuration")
    def save_config(self, load_timeout: int = 5):
        """Save current configuration"""

        self.find_and_click(self.locators.search_input)
        self.find_and_click(self.locators.save_btn)
        self.wait_element_hide(self.locators.loading_text, timeout=load_timeout)

    @allure.step('Setting configuration description to {description}')
    def set_description(self, description: str) -> str:
        """Clear description field, set new value and get previous description"""

        desc = self.find_element(self.locators.description_input)
        previous_description = desc.get_property("value")
        self.send_text_to_element(self.locators.description_input, description, clean_input=True)
        return previous_description

    def compare_versions(self, compare_with: str, base_compare_version: Optional[str] = None):
        """Click on history button and select compare to config option by its description"""

        base_version = f'"{base_compare_version}"' if base_compare_version else 'current'
        with allure.step(f"Compare {base_version} configuration with {compare_with}"):
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

    @allure.step("Click on advanced button")
    def click_on_advanced(self):
        self.find_and_click(CommonConfigMenu.advanced_label)

    @property
    def advanced(self):
        """Get advanced checkbox status"""
        return "checked" in self.find_element(CommonConfigMenu.advanced_label).get_attribute("class")

    def get_input_value(self, row: WebElement, *, is_password: bool = False) -> str:
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

    def check_inputs_disabled(self, row: WebElement, is_password: bool = False):
        """Check that inputs in row are disabled"""
        row_locators = CommonConfigMenu.ConfigRow
        locator = row_locators.value if not is_password else row_locators.password
        for row_input in self.find_children(row, locator):
            assert row_input.get_attribute("disabled") == "true", "Input should be disabled"

    def is_history_disabled(self):
        return self.find_element(self.locators.history_btn).get_attribute("disabled") == "true"

    def activate_group_chbx(self, row: WebElement):
        """Activate group checkbox in row"""
        group_chbx = self.find_child(row, CommonConfigMenu.ConfigRow.group_chbx)

        def is_checked(chbx: WebElement):
            return "checked" in chbx.get_attribute("class")

        def assert_checked():
            if not is_checked(group_chbx):
                group_chbx.click()
            assert is_checked(
                self.find_child(row, CommonConfigMenu.ConfigRow.group_chbx)
            ), "Group checkbox in row is not checked"

        wait_until_step_succeeds(assert_checked, timeout=3, period=0.5)

    def check_inputs_enabled(self, row: WebElement, is_password: bool = False):
        """Check that inputs in row are enabled"""

        row_locators = CommonConfigMenu.ConfigRow
        locator = row_locators.value if not is_password else row_locators.password
        for row_input in self.find_children(row, locator):
            assert not row_input.get_attribute("disabled"), "Input should be enabled"

    @allure.step("Check bool field")
    def assert_checkbox_state(self, row: WebElement, expected_value: bool):
        current_bool_state = "checked" in self.find_child(row, CommonConfigMenu.ConfigRow.checkbox).get_attribute(
            "class"
        )
        assert (
            current_bool_state == expected_value
        ), f"Expected value was {expected_value} but presented is {current_bool_state}"

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
            assert expected_value == input_value, f"Expected value was {expected_value} but presented is {input_value}"

        wait_until_step_succeeds(_assert_value, timeout=4, period=0.5)

    @allure.step('Check field "{display_name}" has value "{expected_value}"')
    def assert_map_value_is(
        self,
        expected_value: list,
        display_name: str,
    ):
        """
        Assert that value in map field is expected_value (using retries)
        :param expected_value: Value expected to be in field
        :param expected_value: Value expected to be in field
        :param display_name: Config field display name
        """

        def _assert_value():
            input_value = {}
            row_values = [
                v.get_attribute("value")
                for v in self.find_children(self.get_config_row(display_name), self.locators.ConfigRow.input)
            ]
            for i in range(0, len(row_values) - 1, 2):  # row values are key-value for each "input" in a map row
                input_value[row_values[i]] = row_values[i + 1]
            assert expected_value == input_value, f"Expected value was {expected_value} but presented is {input_value}"

        wait_until_step_succeeds(_assert_value, timeout=4, period=0.5)

    @allure.step('Check field "{display_name}" has value "{expected_value}"')
    def assert_list_value_is(
        self,
        expected_value: list,
        display_name: str,
    ):
        """
        Assert that value in list field is expected_value (using retries)
        :param expected_value: Value expected to be in field
        :param expected_value: Value expected to be in field
        :param display_name: Config field display name
        """

        def _assert_value():
            input_value = [
                v.get_attribute("value")
                for v in self.find_children(self.get_config_row(display_name), self.locators.ConfigRow.input)
            ]
            assert expected_value == input_value, f"Expected value was {expected_value} but presented is {input_value}"

        wait_until_step_succeeds(_assert_value, timeout=4, period=0.5)

    def get_amount_of_inputs_in_row(self, row: WebElement):
        return len(self.find_children(row, self.locators.ConfigRow.input))

    def reset_to_default(self, row: WebElement):
        """Click reset button"""
        self.find_child(row, CommonConfigMenu.ConfigRow.reset_btn).click()

    def clear_secret(self, row: WebElement):
        self.find_child(row, CommonConfigMenu.ConfigRow.clear_btn).click()

    @allure.step('Type "{values}" into config field with few inputs')
    def type_in_field_with_few_inputs(self, row: WebElement | str, values: list[str | int], clear: bool = False):
        """
        Send keys to config list
        :param row: Config field row
        :param values: keys to send
        :param clear: clean input before sending keys or not
        """

        field_row = row if isinstance(row, WebElement) else self.get_config_row(display_name=row)
        self.scroll_to(field_row)
        for value_id, value in enumerate(values):
            try:
                field = self.find_children(field_row, self.locators.ConfigRow.input)[value_id]
            except IndexError:
                self.find_child(field_row, self.locators.ConfigRow.add_item_btn).click()
                self.wait_element_visible(self.find_child(field_row, self.locators.ConfigRow.input))
                field = self.find_children(field_row, self.locators.ConfigRow.input)[value_id]
            if clear:
                field.clear()
            self.find_children(field_row, self.locators.ConfigRow.input)[value_id].click()
            self.find_children(field_row, self.locators.ConfigRow.input)[value_id].send_keys(value)

    @allure.step("Click item button in config row")
    def click_add_item_btn_in_row(self, row: Union[WebElement, str]):
        """Click item button in config row"""
        field_row = row if isinstance(row, WebElement) else self.get_config_row(display_name=row)
        self.find_child(field_row, self.locators.ConfigRow.add_item_btn).click()

    @allure.step('Select option "{option}" in option field')
    def select_option(self, row: Union[WebElement, str], option: str):
        """For config type option select item from dropdown"""

        field_row = row if isinstance(row, WebElement) else self.get_config_row(display_name=row)
        self.find_child(field_row, self.locators.ConfigRow.select_btn).click()
        self.wait_element_visible(self.locators.ConfigRow.select_item)
        select_items = self.find_elements(self.locators.ConfigRow.select_item)
        for item in select_items:
            if item.text == option:
                item.click()
                return
        raise AttributeError(f"Option {option} has not been found")

    @allure.step("Click on group {title}")
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

    def click_boolean_checkbox(self, row):
        self.find_child(row, self.locators.ConfigRow.checkbox).click()

    @contextmanager
    def wait_group_changed(self, group_name: str):
        """Wait while group is opened or closed"""

        group_state_before = self.find_element(self.locators.group_btn(group_name)).get_attribute("class")
        yield

        def check_group_clicked():
            group_state_after = self.find_element(self.locators.group_btn(group_name)).get_attribute("class")
            assert group_state_before != group_state_after, "Group has not changed"

        wait_until_step_succeeds(check_group_clicked, period=1, timeout=10)

    @allure.step("Click on group {group_name} expanded toggle")
    def expand_or_close_group(self, group_name: str, expand: bool = True):
        """Click on group with given title"""

        group = self.find_element(self.locators.group_btn(group_name))

        def click_on_group():
            def is_expand_group():
                return "expanded" in self.find_element(self.locators.group_btn(group_name)).get_attribute("class")

            if is_expand_group() != expand:
                with self.wait_group_changed(group_name):
                    self.find_child(group, CommonLocators.mat_slide_toggle).click()
            is_expand = is_expand_group()
            assert (
                is_expand if expand else not is_expand
            ), f"Group {group_name} should{' ' if expand else ' not '}be expanded"

        wait_until_step_succeeds(click_on_group, period=1, timeout=10)

    @allure.step("Search for {keys}")
    def search(self, keys: str):
        """Clear search and send keys"""
        search = self.find_element(self.locators.search_input)
        search.clear()
        search.send_keys(keys)

    @allure.step("Clear search")
    def clear_search(self):
        """Clear search input with button"""
        self.find_and_click(CommonConfigMenu.search_input_clear_btn)

    @allure.step('Clear field "{display_name}"')
    def clear_field_by_keys(self, display_name: str):
        """Clear field by name"""

        row = self.get_config_row(display_name)
        self.clear_by_keys(self.find_child(row, CommonConfigMenu.ConfigRow.value))

    @allure.step("Check {name} required error is presented")
    def check_field_is_required(self, name: str):
        """
        Assert that message "Field [{name}] is required!" is presented
        """
        message = f'Field [{name}] is required!'
        check_element_is_visible(self, self.locators.field_error(message))

    @allure.step("Check {name} invalid error is presented")
    def check_field_is_invalid_error(self, name: str):
        check_element_is_visible(self, self.locators.field_error(f"Field [{name}] is invalid!"))

    @allure.step("Check {name} confirmation error is presented")
    def check_password_confirm_required(self, name: str):
        check_element_is_visible(self, self.locators.field_error(f"Confirm [{name}] is required!"))

    @allure.step("Check invalid value error is presented")
    def check_invalid_value_message(self, error_message: str):
        check_element_is_visible(self, self.locators.field_error(error_message))

    def is_save_btn_disabled(self):
        self.find_and_click(self.locators.search_input)
        return self.find_element(self.locators.save_btn).get_attribute("disabled") == "true"

    @allure.step("Check save button status")
    def check_save_btn_state_and_save_conf(self, expected_state: bool):
        self.find_and_click(self.locators.search_input)
        assert (
            not (self.is_save_btn_disabled()) == expected_state
        ), f'Save button should{" not " if expected_state is True else " "}be disabled'
        if expected_state:
            self.save_config()

    def check_text_in_tooltip(self, row_name: str, tooltip_text: str):
        tooltip_icon = self.find_element(self.locators.info_tooltip_icon(row_name, row_name))
        self.scroll_to(tooltip_icon)
        self.hover_element(tooltip_icon)
        tooltip_el = self.find_element(self.locators.tooltip_text)
        self.wait_element_visible(tooltip_el)
        assert tooltip_el.text == tooltip_text

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

    @allure.step("Check that group is active = {is_active}")
    def check_group_is_active(self, group_name, is_active: bool = True):
        """Get group activity state"""

        group = self.find_element(self.locators.group_btn(group_name))
        toogle = self.find_child(group, CommonLocators.mat_slide_toggle)
        toogle_is_active = "mat-checked" in toogle.get_attribute("class")
        assert (
            toogle_is_active if is_active else not toogle_is_active
        ), f"Group should{'' if is_active else ' not '}be active by default"

    def get_items_in_group(self, group: WebElement):
        """Get item rows in the group"""

        try:
            return self.find_children(group, self.locators.ConfigGroup.item_row, timeout=2)
        except TimeoutException:
            return []

    @allure.step("Check that subs in group {group_name} is visible = {is_visible}")
    def check_subs_visibility(self, group_name: str, is_visible: bool = True):
        """Get config field group elements"""

        item_rows = self.get_items_in_group(self.find_element(self.locators.group_row(group_name)))
        if is_visible:
            assert item_rows, "There should be items in the group"
            for item in item_rows:
                check_element_is_visible(self, item)
        else:
            for item in item_rows:
                check_element_is_hidden(self, item)

    def get_group_names(self, timeout: int = 2):
        """Wait for group elements to be displayed and get them"""
        try:
            return self.find_elements(self.locators.ConfigGroup.name, timeout=timeout)
        except TimeoutException:
            return []

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

    @allure.step("Check that there are no rows or groups on config page")
    def check_no_rows_or_groups_on_page(self, timeout=1):
        assert len(self.get_group_names(timeout)) == 0, "Config group should not be visible"
        assert len(self.get_all_config_rows(timeout=timeout)) == 0, "There should not be any rows"

    @allure.step("Check that there are no rows or groups on config page with advanced settings")
    def check_no_rows_or_groups_on_page_with_advanced(self):
        self.check_no_rows_or_groups_on_page()
        self.click_on_advanced()
        self.check_no_rows_or_groups_on_page()

    @contextmanager
    def wait_config_groups_change(self, expected_rows_amount: Optional[int] = None):
        """Wait changing config groups amount."""

        amount_before = len(self.get_group_names())
        yield

        def _wait_changing_groups_amount():
            amount_after = len(self.get_group_names())
            assert amount_after != amount_before, "Amount of groups on the page hasn't changed"
            if expected_rows_amount:
                assert (
                    amount_after == expected_rows_amount
                ), f"Amount of groups on the page should be {expected_rows_amount}"

        wait_until_step_succeeds(_wait_changing_groups_amount, period=1, timeout=10)

    def get_config_row_info(self, row: WebElement):
        """Get info by row"""
        return ConfigRowInfo(
            name=self.find_child(row, CommonConfigMenu.ConfigRow.name).text,
            value=self.find_child(row, CommonConfigMenu.ConfigRow.value).get_attribute("value"),
        )

    @allure.step("Clear search input")
    def clear_search_input(self):
        """Clear search input"""
        self.find_and_click(CommonConfigMenu.search_input_clear_btn)

    def get_history_in_row(self, row: WebElement):
        """Get history roe"""
        return [h.text for h in self.find_children(row, CommonConfigMenu.ConfigRow.history)]

    @allure.step("Wait row with history value {value}")
    def wait_history_row_with_value(self, row: WebElement, value: T, value_converter: Callable[[str], T] = lambda x: x):
        """Wait for value in History row"""

        def _assert_value():
            assert value_converter(self.get_history_in_row(row)[0]) == value, "History row should contain old value"

        wait_until_step_succeeds(_assert_value, timeout=4, period=0.5)

    @allure.step('Scroll to group "{display_name}"')
    def scroll_to_group(self, display_name: str) -> WebElement:
        """Scroll to parameter group by display name"""
        return self.scroll_to(CommonConfigMenu.group_btn(display_name))

    @allure.step('Scroll to field "{display_name}"')
    def scroll_to_field(self, display_name: str) -> WebElement:
        """Scroll to parameter field by display name"""
        row = self.get_config_row(display_name)
        return self.scroll_to(row)

    @allure.step("Check warn icon on the left menu Configuration element")
    def check_config_warn_icon_on_left_menu(self):
        assert self.is_child_displayed(
            self.find_element(ObjectPageMenuLocators.config_tab), ObjectPageMenuLocators.warn_icon
        ), "No warn icon near Configuration left menu element"

    @allure.step("Check warn icon on the left menu Import element")
    def check_import_warn_icon_on_left_menu(self):
        assert self.is_child_displayed(
            self.find_element(ObjectPageMenuLocators.import_tab), ObjectPageMenuLocators.warn_icon
        ), "No warn icon near Import left menu element"

    @allure.step("Check warn icon on the left menu Host-Components element")
    def check_hostcomponents_warn_icon_on_left_menu(self):
        assert self.is_child_displayed(
            self.find_element(ObjectPageMenuLocators.components_tab),
            ObjectPageMenuLocators.warn_icon,
        ), "No warn icon near Host-Components left menu element"

    @allure.step("Check warn icon on the left menu Host-Components element")
    def check_service_components_warn_icon_on_left_menu(self):
        assert self.is_child_displayed(
            self.find_element(ObjectPageMenuLocators.service_components_tab),
            ObjectPageMenuLocators.warn_icon,
        ), "No warn icon near Host-Components left menu element"

    @allure.step("Fill config page with test values")
    def fill_config_fields_with_test_values(self):
        """
        For config fields test when in config file there are all types of fields named accordingly.
        Fill fields with test values.
        """

        row_value_new = "test"
        with allure.step("Change value in float type"):
            self.type_in_field_with_few_inputs("float", ["1.1111111111"], True)
        with allure.step("Change value in boolean type"):
            self.click_boolean_checkbox(self.get_config_row("boolean"))
        with allure.step("Change value in int type"):
            self.type_in_field_with_few_inputs("integer", ["100500"], True)
        with allure.step("Change value in password type"):
            self.type_in_field_with_few_inputs("password", [row_value_new] * 2, True)
        with allure.step("Change value in string type"):
            self.type_in_field_with_few_inputs("string", [row_value_new], True)
        with allure.step("Change value in list type"):
            self.type_in_field_with_few_inputs(row="list", values=[row_value_new] * 3, clear=True)
        with allure.step("Change value in file type"):
            self.type_in_field_with_few_inputs("file", [row_value_new * 2], True)
        with allure.step("Change value in option type"):
            self.select_option("option", "WEEKLY")
        with allure.step("Change value in text type"):
            self.type_in_field_with_few_inputs(row="text", values=[row_value_new], clear=True)
        with allure.step("Deactivate group"):
            self.expand_or_close_group("group", expand=False)
        with allure.step("Change value in structure type"):
            self.type_in_field_with_few_inputs(
                row="structure", values=["1", row_value_new, "2", row_value_new], clear=True
            )
        with allure.step("Change value in map type"):
            self.type_in_field_with_few_inputs(row="map", values=[row_value_new] * 4, clear=True)
        with allure.step("Change value in secrettext type"):
            self.type_in_field_with_few_inputs(row="secrettext", values=[row_value_new], clear=True)
        with allure.step("Change value in json type"):
            self.type_in_field_with_few_inputs(row="json", values=['{}'], clear=True)

    @staticmethod
    def is_element_read_only(row: WebElement) -> bool:
        """Check if element is read-only by checking 'read-only' in class"""
        return "read-only" in str(row.get_attribute("class"))

    @allure.step("Check row history on config page")
    def check_config_fields_history_with_test_values(self):
        """
        For config fields test when in config file there are all types of fields named accordingly.
        Check common history values.
        """

        with allure.step("Check history value in float type"):
            self.wait_history_row_with_value(self.get_config_row("float"), "0.1")
        with allure.step("Check history value in boolean type"):
            self.wait_history_row_with_value(self.get_config_row("boolean"), "true")
        with allure.step("Check history value in int type"):
            self.wait_history_row_with_value(self.get_config_row("integer"), "16")
        with allure.step("Check history value in password type"):
            self.wait_history_row_with_value(
                self.get_config_row("password"),
                "$*************;*.*;****** *********************************************************************"
                "***********************************************************************************************"
                "************************************************************************************************"
                "****************************************************************",
            )
        with allure.step("Check history value in string type"):
            self.wait_history_row_with_value(self.get_config_row("string"), "string")
        with allure.step("Check history value in list type"):
            self.wait_history_row_with_value(
                self.get_config_row("list"), '["/dev/rdisk0s1","/dev/rdisk0s2","/dev/rdisk0s3"]'
            )
        with allure.step("Check history value in file type"):
            self.wait_history_row_with_value(self.get_config_row("file"), "file content")
        with allure.step("Check history value in option type"):
            self.wait_history_row_with_value(self.get_config_row("option"), "DAILY")
        with allure.step("Check history value in text type"):
            self.wait_history_row_with_value(self.get_config_row("text"), "text")
        with allure.step("Check group in not active"):
            self.check_group_is_active("group", is_active=False)
        with allure.step("Check history value in structure type"):
            self.wait_history_row_with_value(
                self.get_config_row("structure"),
                '[{"code":1,"country":"Test1"},{"code":2,"country":"Test2"}]',
            )
        with allure.step("Check history value in map type"):
            self.wait_history_row_with_value(
                self.get_config_row("map"),
                {"age": "24", "name": "Joe", "sex": "m"},
                value_converter=json.loads,
            )
        with allure.step("Change value in secrettext type"):
            self.wait_history_row_with_value(self.get_config_row("secrettext"), '****')
        with allure.step("Change value in json type"):
            self.wait_history_row_with_value(
                self.get_config_row("json"),
                {"age": "24", "name": "Joe", "sex": "m"},
                value_converter=json.loads,
            )

    def get_config_title(self):
        return self.find_element(ObjectPageLocators.title).text

    @staticmethod
    def is_element_editable(element: WebElement) -> bool:
        """Check if app-field element is read-only by checking 'read-only' class presence"""
        return "read-only" not in str(element.get_attribute("class"))


CONFIG_ITEMS = [
    "float",
    "boolean",
    "integer",
    "password",
    "string",
    "list",
    "file",
    "option",
    "text",
    "structure",
    "map",
    "secrettext",
    "json",
    "usual_port",
    "transport_port",
]
