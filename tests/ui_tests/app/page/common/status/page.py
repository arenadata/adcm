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

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.status.locators import StatusLocators


@dataclass
class StatusRowInfo:
    """Information from status row"""

    icon: bool
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

    def get_all_rows(self):
        """Get all config groups"""
        return [r for r in self.find_elements(StatusLocators.group_row) if r.is_displayed()]

    def get_page_info(self):
        """ "Get group info by row"""
        row_elements = StatusLocators.StatusRow
        page_rows = self.get_all_rows()
        components_items = []
        for row in page_rows:
            row_item = StatusRowInfo(
                icon=self.is_child_displayed(row, row_elements.icon, timeout=1),
                group_name=self.find_child(row, row_elements.group_name).text
                if self.is_child_displayed(row, row_elements.group_name, timeout=1)
                else None,
                state=self.find_child(row, row_elements.state).text
                if self.is_child_displayed(row, row_elements.state, timeout=1)
                else None,
                state_color=self.find_child(row, row_elements.state)
                .value_of_css_property('color')
                .split("(")[1]
                .split(", 1)")[0]
                .split(")")[0]
                if self.is_child_displayed(row, row_elements.state, timeout=1)
                else None,
                link=self.find_child(row, row_elements.link).text
                if self.is_child_displayed(row, row_elements.link, timeout=1)
                else None,
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
        assert current_status == expected_state, f'Status expected to be "{expected_state}", but was "{current_status}"'
