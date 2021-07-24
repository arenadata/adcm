from selenium.webdriver.common.by import By

from tests.ui_tests.app.helpers.locator import Locator


class CommonLocators:
    """Locators common to all pages"""

    socket = Locator(By.CLASS_NAME, "socket", "open socket marker")
    profile = Locator(By.CLASS_NAME, "profile", "profile load marker")
    load_marker = Locator(By.CLASS_NAME, 'load_complete', "page load marker")
