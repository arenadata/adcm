from operator import methodcaller
from typing import Callable

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW
from tests.ui_tests.app.helpers.locator import Locator


class Interactor:
    def __init__(self, driver: WebDriver, default_timeout: int | float):
        self._driver = driver
        self._timeout = default_timeout

    def hover_element(self, element: Locator | WebElement):
        hover = ActionChains(self._driver).move_to_element(
            element if isinstance(element, WebElement) else self.find_element(element)
        )
        hover.perform()

    def find_element(self, locator: Locator, timeout: int = None) -> WebElement:
        timeout = timeout or self._timeout
        return WDW(self._driver, timeout).until(
            EC.presence_of_element_located([locator.by, locator.value]),
            message=f"Can't find {locator.name} on page " f"{self._driver.current_url} for {timeout} seconds",
        )

    def find_child(self, element: WebElement, child: Locator, timeout: int = None) -> WebElement:
        timeout = timeout or self._timeout
        return WDW(element, timeout).until(
            EC.presence_of_element_located([child.by, child.value]),
            message=f"Can't find {child.name} on page " f"{self._driver.current_url} for {timeout} seconds",
        )

    def find_children(self, element: WebElement, child: Locator, timeout: int = 1) -> list[WebElement]:
        try:
            return WDW(element, timeout).until(
                EC.presence_of_all_elements_located([child.by, child.value]),
                message=f"Can't find {child.name} on page " f"{self._driver.current_url} for {timeout} seconds",
            )
        except TimeoutException:
            return []

    def find_elements(self, locator: Locator, timeout: int = 1) -> list[WebElement]:
        return WDW(self._driver, timeout).until(
            EC.presence_of_all_elements_located([locator.by, locator.value]),
            message=f"Can't find {locator.name} on page " f"{self._driver.current_url} for {timeout} seconds",
        )

    def find_elements_or_empty(self, locator: Locator, timeout: int = 2) -> list[WebElement]:
        try:
            return self.find_elements(locator, timeout=timeout)
        except TimeoutException:
            return []

    def is_element_displayed(self, element: Locator | WebElement, timeout: int | None = None) -> bool:
        return self._is_displayed(
            lambda: element
            if isinstance(element, WebElement)
            else self.find_element(element, timeout=timeout or self._timeout)
        )

    def is_child_displayed(self, parent: WebElement, child: Locator, timeout: int | None = None) -> bool:
        return self._is_displayed(lambda: self.find_child(parent, child, timeout=timeout or self._timeout))

    def find_and_click(self, locator: Locator, is_js: bool = False, timeout: int | None = None) -> None:
        if is_js:
            with allure.step(f'Click with js on "{locator.name}"'):
                loc = self.find_element(locator)
                self._driver.execute_script("arguments[0].click()", loc)
        else:
            with allure.step(f'Click on "{locator.name}"'):
                self.wait_element_clickable(locator, timeout=timeout)
                self.find_element(locator).click()

    def wait_element_clickable(self, locator: Locator, timeout: int = None) -> WebElement:
        loc_timeout = timeout or self._timeout
        with allure.step(f'Wait "{locator.name}" is clickable'):
            return WDW(self._driver, loc_timeout).until(
                EC.element_to_be_clickable([locator.by, locator.value]),
                message=f"locator {locator.name} hasn't become clickable for " f"{loc_timeout} seconds",
            )

    def wait_element_visible(self, element: Locator | WebElement, timeout: int | None = None) -> WebElement:
        timeout = timeout or self._timeout

        if isinstance(element, Locator):
            method = EC.visibility_of_element_located([element.by, element.value])
            name = element.name
        else:
            method = EC.visibility_of(element)
            name = element.text

        with allure.step(f"Wait '{name}' become visible"):
            return WDW(self._driver, timeout).until(
                method=method, message=f"{name} hasn't become visible for {timeout} seconds"
            )

    def wait_element_hide(self, element: Locator | WebElement, timeout: int | None = None) -> None:
        timeout = timeout or self._timeout

        if isinstance(element, Locator):
            locator = [element.by, element.value]
            name = element.name
        else:
            locator = element
            name = element.text

        with allure.step(f"Wait '{name}' hide"):
            WDW(self._driver, timeout).until(
                method=EC.invisibility_of_element_located(locator),
                message=f"locator {name} hasn't hide for {timeout} seconds",
            )

    def wait_element_attribute(
        self,
        locator: Locator,
        attribute: str,
        expected_value: str,
        exact_match: bool = True,
        timeout: int = 5,
    ):
        """
        Wait for element to has locator's attribute equals to `expected_value`
        If exact match is False then __contains__ is used
        """
        comparator = methodcaller("__eq__" if exact_match else "__contains__", expected_value)

        def _assert_attribute_value():
            actual_value = self.find_element(locator).get_attribute(attribute)
            assert comparator(actual_value), (
                f'Attribute "{attribute}" of element "{locator}" '
                f'should be/has "{expected_value}", but "{actual_value}" was found'
            )

        wait_until_step_succeeds(_assert_attribute_value, period=0.5, timeout=timeout)

    @staticmethod
    def _is_displayed(find_element_func: Callable[[], WebElement]) -> bool:
        try:
            return find_element_func().is_displayed()
        except (
            TimeoutException,
            NoSuchElementException,
            StaleElementReferenceException,
            TimeoutError,
        ):
            return False
