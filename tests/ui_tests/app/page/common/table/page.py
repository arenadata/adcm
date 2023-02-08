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

"""Table page PageObjects classes"""

from contextlib import contextmanager

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.core.interactors import Interactor
from tests.ui_tests.utils import assert_enough_rows


class CommonTableObj(Interactor):
    """Class for manipulating with common tables elements."""

    LOADING_STATE_TEXT = "autorenew"

    def __init__(self, driver, locators_class=CommonTable):
        super().__init__(driver=driver, default_timeout=3)
        self.locators = locators_class

    @property
    def row_count(self) -> int:
        """Get amount of rows on page"""
        return len(self.get_all_rows())

    def get_all_rows(self, timeout: int | float = 5) -> list[WebElement]:
        return self.find_elements_or_empty(self.locators.row, timeout=timeout)

    def get_row(self, row_num: int = 0) -> WebElement:
        """Get row from the table"""

        def _table_has_enough_rows():
            assert_enough_rows(row_num, self.row_count)

        wait_until_step_succeeds(_table_has_enough_rows, timeout=5, period=0.1)
        rows = self.get_all_rows()
        assert_enough_rows(row_num, len(rows))
        return rows[row_num]

    @allure.step("Click on previous page")
    def click_previous_page(self):
        """Click on previous page"""
        self.find_and_click(self.locators.Pagination.previous_page)

    @allure.step("Click on previous page")
    def click_next_page(self):
        """Click on next page"""
        self.find_and_click(self.locators.Pagination.next_page)

    @contextmanager
    def wait_rows_change(self):
        """Wait changing rows amount"""

        current_amount = len(self.get_all_rows())
        yield

        def _wait_scroll():
            assert len(self.get_all_rows()) != current_amount, "Amount of rows on the page hasn't changed"

        self.wait_element_hide(CommonToolbarLocators.progress_bar)
        wait_until_step_succeeds(_wait_scroll, period=1, timeout=10)

    @allure.step("Click on page number {number}")
    def click_page_by_number(self, number: int):
        """Click on page number"""
        page_loc = self.locators.Pagination.page_to_choose_btn
        WDW(self._driver, self._timeout).until(
            EC.presence_of_element_located([page_loc.by, page_loc.value.format(number)]),
            message=f"Can't find page {number} in table on page {self._driver.current_url} "
            f"for {self._timeout} seconds",
        ).click()

    @allure.step("Set rows per page to {rows_amount}")
    def set_rows_per_page(self, rows_amount: int) -> None:
        paging = self.locators.Pagination

        self.find_and_click(paging.per_page_dropdown)
        self.wait_element_visible(paging.per_page_block, timeout=1.5)
        per_page_options = self.find_element(paging.per_page_block, timeout=0.5)

        suitable_option = next(
            filter(
                lambda child: child.text.strip() == str(rows_amount),
                self.find_children(per_page_options, paging.per_page_element),
            ),
            None,
        )
        if suitable_option is None:
            raise AssertionError(f"Failed to find suitable option to show {rows_amount} per page")

        suitable_option.click()
        self.wait_element_hide(paging.per_page_block, timeout=5)
