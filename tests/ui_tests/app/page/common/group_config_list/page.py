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

"""GroupConfig page PageObjects classes"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import List, Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebElement
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.dialogs.locators import DeleteDialogLocators
from tests.ui_tests.app.page.common.group_config_list.locators import (
    GroupConfigListLocators,
)


@dataclass
class GroupConfigRowInfo:
    """Information from group config row on GroupConfig page"""

    name: str
    description: str


class GroupConfigList(BasePageObject):
    """Class for working with group configuration list"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)

    def get_all_config_rows(self) -> List[WebElement]:
        """Return all group config rows"""

        try:
            return [
                r for r in self.find_elements(GroupConfigListLocators.group_config_row, timeout=5) if r.is_displayed()
            ]
        except TimeoutException:
            return []

    def get_config_row_info(self, row: WebElement) -> GroupConfigRowInfo:
        """Return group config row info"""

        return GroupConfigRowInfo(
            name=self.find_child(row, GroupConfigListLocators.GroupConfigRow.name).text,
            description=self.find_child(row, GroupConfigListLocators.GroupConfigRow.description).text,
        )

    @allure.step('Create new group config {name}')
    def create_group(self, name: str, description: str):
        """Create new group config"""

        self.find_and_click(GroupConfigListLocators.add_btn)
        self.wait_element_visible(GroupConfigListLocators.CreateGroupPopup.block)
        self.send_text_to_element(GroupConfigListLocators.CreateGroupPopup.name_input, name, clean_input=True)
        self.send_text_to_element(
            GroupConfigListLocators.CreateGroupPopup.description_input,
            description,
            clean_input=True,
        )
        self.find_and_click(GroupConfigListLocators.CreateGroupPopup.create_btn)
        self.wait_element_hide(GroupConfigListLocators.CreateGroupPopup.block)

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

    def delete_row(self, row: WebElement):
        """Delete row"""
        self.find_child(row, GroupConfigListLocators.GroupConfigRow.delete_btn).click()
        self.wait_element_visible(DeleteDialogLocators.body)
        self.find_and_click(DeleteDialogLocators.yes)
        self.wait_element_hide(DeleteDialogLocators.body)
