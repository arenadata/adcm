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

"""Component page PageObjects classes"""

import allure
from tests.ui_tests.app.page.common.base_page import BaseDetailedPage, BasePageObject
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
    ObjectPageMenuLocators,
)
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.group_config_list.locators import (
    GroupConfigListLocators,
)
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigList
from tests.ui_tests.app.page.common.status.locators import StatusLocators
from tests.ui_tests.app.page.common.status.page import StatusPage
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.core.checks import check_elements_are_displayed


class ComponentPageMixin(BasePageObject):
    """Helpers for working with Component page"""

    # /action /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    cluster_id: int
    service_id: int
    component_id: int
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj
    group_config = GroupConfigList

    def __init__(self, driver, base_url, cluster_id: int, service_id: int, component_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError("You should explicitly set MENU_SUFFIX in class definition")
        super().__init__(
            driver,
            base_url,
            "/cluster/{cluster_id}/service/{service_id}/component/{component_id}/" + self.MENU_SUFFIX,
            cluster_id=cluster_id,
            service_id=service_id,
            component_id=component_id,
        )
        self.cluster_id = cluster_id
        self.service_id = service_id
        self.component_id = component_id
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(driver=self.driver)
        self.group_config = GroupConfigList(self.driver, self.base_url)

    @allure.step("Open Main tab by menu click")
    def open_main_tab(self) -> "ComponentMainPage":
        """Open Main tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.main_tab)
        page = ComponentMainPage(self.driver, self.base_url, self.cluster_id, self.service_id, self.component_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Configuration tab by menu click")
    def open_config_tab(self) -> "ComponentConfigPage":
        """Open Configuration tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.config_tab)
        page = ComponentConfigPage(self.driver, self.base_url, self.cluster_id, self.service_id, self.component_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Group Configuration tab by menu click")
    def open_group_config_tab(self) -> "ComponentGroupConfigPage":
        """Open Group Configuration tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.group_config_tab)
        page = ComponentGroupConfigPage(self.driver, self.base_url, self.cluster_id, self.service_id, self.component_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Status tab by menu click")
    def open_status_tab(self) -> "ComponentStatusPage":
        """Open Status tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.status_tab)
        page = ComponentStatusPage(self.driver, self.base_url, self.cluster_id, self.service_id, self.component_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Assert that all main elements on the page are presented")
    def check_all_elements(self):
        """Assert all main elements presence"""
        check_elements_are_displayed(self, self.MAIN_ELEMENTS)

    @allure.step("Click on link {link_name}")
    def click_link_by_name(self, link_name: str):
        """Click on link by name"""
        self.wait_element_hide(CommonToolbarLocators.progress_bar)
        self.wait_element_visible(CommonToolbarLocators.admin_link)
        self.find_and_click(CommonToolbarLocators.text_link(link_name.upper().strip("_")))

    def check_component_toolbar(self, cluster_name: str, service_name: str, component_name: str):
        self.toolbar.check_toolbar_elements(
            ["CLUSTERS", cluster_name, "SERVICES", service_name, "COMPONENTS", component_name]
        )


class ComponentMainPage(ComponentPageMixin, BaseDetailedPage):
    """Component page Main menu"""

    MENU_SUFFIX = "main"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ComponentConfigPage(ComponentPageMixin):
    """Component page config menu"""

    MENU_SUFFIX = "config"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        CommonConfigMenu.description_input,
        CommonConfigMenu.search_input,
        CommonConfigMenu.advanced_label,
        CommonConfigMenu.save_btn,
        CommonConfigMenu.history_btn,
    ]


class ComponentGroupConfigPage(ComponentPageMixin):
    """Component page group config menu"""

    MENU_SUFFIX = "group_config"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        GroupConfigListLocators.header_item,
        GroupConfigListLocators.add_btn,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]


class ComponentStatusPage(ComponentPageMixin, StatusPage):
    """Component page config menu"""

    MENU_SUFFIX = "status"
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        StatusLocators.expand_collapse_btn,
    ]

    def click_host_by_name(self, host_name: str):
        """Click on host by name"""

        for row in self.get_all_rows():
            for link in self.find_children(row, StatusLocators.StatusRow.link):
                if link.text == host_name:
                    link.click()
                    return
        raise AssertionError(f"There are no host with name '{host_name}'")
