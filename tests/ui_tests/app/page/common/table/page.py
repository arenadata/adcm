from contextlib import contextmanager

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.table.locator import CommonTable


class CommonTableObj(BasePageObject):
    """Class for manipulating with common tables elements."""

    def __init__(self, driver, base_url, table_class_locators=CommonTable):
        super().__init__(driver, base_url)
        self.table = table_class_locators

    @allure.step("Get all rows from the table")
    def get_all_rows(self) -> list:
        try:
            return self.find_elements(self.table.row, timeout=5)
        except TimeoutException:
            return []

    def click_previous_page(self):
        self.find_and_click(self.table.Pagination.previous_page)

    def click_next_page(self):
        self.find_and_click(self.table.Pagination.next_page)

    @contextmanager
    def wait_rows_change(self):
        """Wait changing rows amount."""

        current_amount = len(self.get_all_rows())
        yield

        def wait_scroll():
            assert len(self.get_all_rows()) != current_amount
        wait_until_step_succeeds(wait_scroll, period=1, timeout=10)

    @allure.step("Click on page number {number}")
    def click_page_by_number(self, number: int):
        pages = self.find_elements(self.table.Pagination.page_btn)
        for page in pages:
            if int(page.text) == number:
                page.click()
