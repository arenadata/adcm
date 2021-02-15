from tests.ui_tests.app.locators import ActionPageLocators
from tests.ui_tests.app.pages import BasePage
import allure


class ActionPage(BasePage):
    """Class for action page."""

    def __init__(self, driver, url=None, cluster_id=None):
        super().__init__(driver)
        self.get(f"{url}/cluster/{cluster_id}/action", "action")

    @allure.step('Open run action popup')
    def open_run_action_popup(self):
        self._wait_element_present(ActionPageLocators.action_run_button, timer=15).click()
        self._wait_element_present(ActionPageLocators.run_action_popup)

    @allure.step('Check if verbose checkbox is displayed on popup')
    def check_verbose_chbx_displayed(self):
        self.open_run_action_popup()
        return self.driver.find_element(*ActionPageLocators.ActionRunPopup.verbose_chbx).is_displayed()

    def run_action(self, is_verbose: bool = False):
        with allure.step(f'Run action {"with" if is_verbose else "without"} verbose checkbox'):
            self.open_run_action_popup()
            if is_verbose:
                self.driver.find_element(*ActionPageLocators.ActionRunPopup.verbose_chbx).click()
            self.driver.find_element(*ActionPageLocators.ActionRunPopup.run_btn).click()
            self._wait_element_hide(ActionPageLocators.ActionRunPopup.verbose_chbx)
