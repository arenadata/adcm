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

"""
Manipulations with different type of configuration parameters
"""
from contextlib import contextmanager
from typing import Dict

from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu


class ConfigFieldsManipulator(BasePageObject):
    """
    Class for handling different types of inputs on configuration page.
    """

    def fill_password(self, password: str, row: WebElement, *, confirmation: str = None):
        """
        Fill password and confirm password field with same value if confirmation is not provided explicitly
        """
        password_input = self.find_child(row, CommonConfigMenu.ConfigRow.password)
        password_input.send_keys(password)
        if confirmation is not None:
            confirm_input = self.find_child(row, CommonConfigMenu.ConfigRow.confirm_password)
            confirm_input.send_keys(password)

    def add_list_values(self, values: list, row: WebElement):
        """Add list values to config parameter in row"""
        add_button = self.find_child(row, CommonConfigMenu.ConfigRow.add_item_btn)
        for value in values:
            with self._with_items_added(row):
                self.scroll_to(add_button)
                add_button.click()
            item_to_fill = self._get_first_empty_input(row)
            item_to_fill.send_keys(value)

    def add_map_values(self, values: Dict[str, str], row: WebElement):
        """Add map values to config parameter in row"""
        add_button = self.find_child(row, CommonConfigMenu.ConfigRow.add_item_btn)
        for key, value in values.items():
            with self._with_items_added(row):
                self.scroll_to(add_button)
                add_button.click()
            item_to_fill = self._get_first_empty_map_input(row)
            key_input = self.find_child(item_to_fill, CommonConfigMenu.ConfigRow.map_input_key)
            value_input = self.find_child(item_to_fill, CommonConfigMenu.ConfigRow.map_input_value)
            key_input.send_keys(key)
            value_input.send_keys(value)

    def _get_first_empty_input(self, row: WebElement) -> WebElement:
        """Get first empty field (simple search for inputs/textareas in row)"""
        for item in self.find_children(row, CommonConfigMenu.ConfigRow.value, timeout=2):
            if not item.get_attribute("value"):
                return item
        raise ValueError('All items in row has "value" or no items are presented')

    def _get_first_empty_map_input(self, row: WebElement) -> WebElement:
        """Search for first empty (by key) input element for map and return 'parent' map WebElement"""
        for item in self.find_children(row, CommonConfigMenu.ConfigRow.map_item, timeout=2):
            key_input = self.find_child(item, CommonConfigMenu.ConfigRow.map_input_key)
            if not key_input.get_attribute("value"):
                return item
        raise ValueError('All items in map has "value" in key input field or no items are presented')

    @contextmanager
    def _with_items_added(self, row: WebElement):
        """Wait for new items to appear after 'add new' button is clicked"""
        before = len(self.find_children(row, CommonConfigMenu.ConfigRow.value, timeout=2))

        yield

        def check_new_item_appeared():
            assert (
                len(self.find_children(row, CommonConfigMenu.ConfigRow.value, timeout=1)) > before
            ), f"New item should appear in {row}, but there are still {before} rows"

        wait_until_step_succeeds(check_new_item_appeared, timeout=10, period=1)
