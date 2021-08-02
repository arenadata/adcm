import allure

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.common.dialogs import (
    ActionDialog,
    DeleteDialog,
)


class CommonToolbar(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url)

    def click_admin_link(self):
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.admin_link)

    def click_link_by_name(self, link_name: str):
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.text_link(link_name.upper().strip("_")))

    @allure.step("Run action {action_name} in {tab_name}")
    def run_action(self, tab_name: str, action_name: str):
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.action_btn(tab_name.upper().strip("_")))
        self.wait_element_visible(CommonToolbarLocators.Popup.popup_block)
        self.find_and_click(CommonToolbarLocators.Popup.item(action_name))

    @allure.step("Run upgrade {upgrade_name} in {tab_name}")
    def run_upgrade(self, tab_name: str, upgrade_name: str):
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.upgrade_btn(tab_name.upper().strip("_")))
        self.wait_element_visible(CommonToolbarLocators.Popup.popup_block)
        self.find_and_click(CommonToolbarLocators.Popup.item(upgrade_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
