import allure
from selenium.common import TimeoutException
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.core.locators import BaseLocator


def check_elements_are_displayed(page, locators: list[BaseLocator]) -> None:
    for loc in locators:
        assert page.is_element_displayed(loc), f"Locator {loc.name} isn't displayed on page {page.driver.current_url}"


def check_element_is_hidden(page, element: BaseLocator | WebElement, timeout: int | None = None) -> None:
    """Raises assertion error if element is still visible after timeout"""
    try:
        page.wait_element_hide(element, timeout)
    except TimeoutException as e:
        raise AssertionError(e.msg) from e


def check_element_is_visible(page, element: BaseLocator | WebElement, timeout: int | None = None) -> None:
    """Raises assertion error if element is not visible after timeout"""
    try:
        page.wait_element_visible(element, timeout)
    except TimeoutException as e:
        raise AssertionError(e.msg) from e


@allure.step("Check pagination")
def check_pagination(table: CommonTableObj, expected_on_second: int, expected_on_first: int = 10):
    table.wait_element_hide(CommonToolbarLocators.progress_bar, timeout=60)
    with table.wait_rows_change():
        table.click_page_by_number(2)
    assert table.row_count == expected_on_second, f"Second page should contains {expected_on_second} items"
    with table.wait_rows_change():
        table.click_page_by_number(1)
    assert table.row_count == expected_on_first, f"First page should contains {expected_on_first} items"
    with table.wait_rows_change():
        table.click_next_page()
    assert table.row_count == expected_on_second, f"Next page should contains {expected_on_second} items"
    with table.wait_rows_change():
        table.click_previous_page()
    assert table.row_count == expected_on_first, f"Previous page should contains {expected_on_first} items"
