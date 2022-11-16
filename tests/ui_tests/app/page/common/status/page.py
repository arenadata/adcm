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

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebElement
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.status.locators import StatusLocators

SUCCESS_COLOR = '0, 230, 118'
NEGATIVE_COLOR = '255, 152, 0'


@dataclass
class StatusRowInfo:
    """Information from status row"""

    icon_status: bool
    group_name: Optional[str]
    state: Optional[str]
    state_color: Optional[str]
    link: Optional[str]


class StatusPage(BasePageObject):
    """Class for working with status page"""

    @allure.step("Click on collapse all button")
    def click_collapse_all_btn(self):
        """Click on collapse all button"""
        self.find_and_click(StatusLocators.expand_collapse_btn)

    def get_all_rows(self) -> [WebElement]:
        """Get all config groups"""
        return self.find_elements(StatusLocators.group_row)

    def get_page_info(self) -> [StatusRowInfo]:
        """ "Get group info by row"""
        row_elements = StatusLocators.StatusRow
        page_rows = self.get_all_rows()
        components_items = []

        def get_child_text(row: WebElement, locator: Locator) -> str:
            return self.find_child(row, locator).text if self.is_child_displayed(row, locator, timeout=1) else None

        for row in page_rows:
            row_item = StatusRowInfo(
                icon_status="mat-accent" in self.find_child(row, row_elements.icon).get_attribute("class")
                if self.is_child_displayed(row, row_elements.icon, timeout=1)
                else None,
                group_name=get_child_text(row, row_elements.group_name),
                state=get_child_text(row, row_elements.state),
                state_color=self.find_child(row, row_elements.state)
                .value_of_css_property('color')
                .split("(")[1]
                .split(", 1)")[0]
                .split(")")[0]
                if self.is_child_displayed(row, row_elements.state, timeout=1)
                else None,
                link=get_child_text(row, row_elements.link),
            )
            components_items.append(row_item)
        return components_items

    @contextmanager
    def wait_rows_collapsed(self):
        """Wait when status info is visible or hidden."""

        rows_before = len(self.get_all_rows())
        yield

        def _wait_collapsed():
            assert rows_before != len(self.get_all_rows()), "Status info rows has not been changed"

        wait_until_step_succeeds(_wait_collapsed, period=1, timeout=5)

    def compare_current_and_expected_state(self, expected_state: [StatusRowInfo]):
        current_status = self.get_page_info()
        expected = "\n".join(map(str, expected_state))
        actual = "\n".join(map(str, current_status))
        assert current_status == expected_state, f'Status expected to be:\n {expected}, \nbut was \n"{actual}"'
