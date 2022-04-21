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

"""Cluster page PageObjects classes"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import List

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.cluster.locators import (
    ClusterServicesLocators,
    ClusterHostLocators,
    ClusterComponentsLocators,
)
from tests.ui_tests.app.page.common.base_page import BasePageObject, PageHeader, PageFooter, BaseDetailedPage
from tests.ui_tests.app.page.common.common_locators import ObjectPageLocators, ObjectPageMenuLocators
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs_locators import ActionDialog, DeleteDialog
from tests.ui_tests.app.page.common.group_config.page import CommonGroupConfigMenu
from tests.ui_tests.app.page.common.group_config_list.locators import GroupConfigListLocators
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigList
from tests.ui_tests.app.page.common.import_page.locators import ImportLocators
from tests.ui_tests.app.page.common.import_page.page import ImportPage
from tests.ui_tests.app.page.common.popups.locator import HostAddPopupLocators
from tests.ui_tests.app.page.common.popups.locator import HostCreationLocators
from tests.ui_tests.app.page.common.popups.locator import PageConcernPopupLocators, ListConcernPopupLocators
from tests.ui_tests.app.page.common.popups.page import HostCreatePopupObj
from tests.ui_tests.app.page.common.status.page import StatusPage
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.host_list.page import HostRowInfo


@dataclass
class ComponentsHostRowInfo:
    """Information from host row about host on Components page"""

    name: str
    components: str


@dataclass
class StatusGroupInfo:
    """Information from group on Status page"""

    service: str
    hosts: list


class ClusterPageMixin(BasePageObject):
    """Helpers for working with cluster page"""

    # /action /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    cluster_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj
    host_popup: HostCreatePopupObj
    group_config = GroupConfigList

    def __init__(self, driver, base_url, cluster_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, "/cluster/{cluster_id}/" + self.MENU_SUFFIX, cluster_id=cluster_id)
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)
        self.host_popup = HostCreatePopupObj(self.driver, self.base_url)
        self.group_config = GroupConfigList(self.driver, self.base_url)

    def open_main_tab(self):
        """Open Main tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.main_tab)
        page = ClusterMainPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_services_tab(self):
        """Open Services tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.services_tab)
        page = ClusterServicesPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_hosts_tab(self):
        """Open Hosts tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.hosts_tab)
        page = ClusterHostPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_components_tab(self):
        """Open Components tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.components_tab)
        page = ClusterComponentsPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Group Configuration tab by menu click")
    def open_group_config_tab(self) -> "ClusterGroupConfigPage":
        """Open Group Configuration tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.group_config_tab)
        page = ClusterGroupConfigPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_config_tab(self):
        """Open Configuration tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.config_tab)
        page = ClusterConfigPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_status_tab(self):
        """Open Status tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.status_tab)
        page = ClusterStatusPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_import_tab(self):
        """Open Import tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.import_tab)
        page = ClusterImportPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Assert that all main elements on the page are presented")
    def check_all_elements(self):
        """Assert all main elements presence"""
        self.assert_displayed_elements(self.MAIN_ELEMENTS)

    def check_cluster_toolbar(self, cluster_name: str):
        self.toolbar.check_toolbar_elements(["CLUSTERS", cluster_name])


class ClusterMainPage(ClusterPageMixin, BaseDetailedPage):
    """Cluster page Main menu"""

    MENU_SUFFIX = 'main'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ClusterServicesPage(ClusterPageMixin):
    """Cluster page services menu"""

    MENU_SUFFIX = 'service'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ClusterServicesLocators.add_services_btn,
        CommonTable.header,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]

    def click_add_service_btn(self):
        """Click on Add service button"""
        self.find_and_click(ClusterServicesLocators.add_services_btn)

    @allure.step("Add service {service_name} to cluster")
    def add_service_by_name(self, service_name: str):
        """Add service to cluster"""
        self.find_and_click(ClusterServicesLocators.add_services_btn)
        self.wait_element_visible(ClusterServicesLocators.AddServicePopup.block)
        for service in self.find_elements(ClusterServicesLocators.AddServicePopup.service_row):
            service_text = self.find_child(service, ClusterServicesLocators.AddServicePopup.ServiceRow.text)
            if service_text.text == service_name:
                service_text.click()
        self.find_and_click(ClusterServicesLocators.AddServicePopup.create_btn)
        self.wait_element_hide(ClusterServicesLocators.AddServicePopup.block)

    @allure.step("Click on service concern object name from the row")
    def click_on_concern_by_object_name(self, row: WebElement, concern_object_name: str):
        """Click on concern object link from the row"""
        self.hover_element(self.find_child(row, ClusterServicesLocators.ServiceTableRow.actions))
        self.wait_element_visible(ListConcernPopupLocators.block)
        for issue in self.find_elements(ListConcernPopupLocators.link_to_concern_object):
            if concern_object_name in issue.text:
                issue.click()
                return
        raise AssertionError(f"Issue name '{concern_object_name}' not found in issues")

    def click_action_btn_in_row(self, row: WebElement):
        """Click on Action button from the row"""
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.actions).click()

    def click_import_btn_in_row(self, row: WebElement):
        """Click on Import button from the row"""
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.service_import).click()

    def click_config_btn_in_row(self, row: WebElement):
        """Click on Config button from the row"""
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.config).click()

    def get_service_state_from_row(self, row: WebElement):
        """Get service state from the row"""
        return self.find_child(row, ClusterServicesLocators.ServiceTableRow.state).text

    @allure.step("Run action {action_name} for service")
    def run_action_in_service_row(self, row: WebElement, action_name: str):
        """Run Action by Action button from the row"""
        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        self.find_and_click(self.table.locators.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @contextmanager
    def wait_service_state_change(self, row: WebElement):
        """Wait for service state to change"""
        state_before = self.get_service_state_from_row(row)
        yield

        def _wait_state():
            state_after = self.get_service_state_from_row(row)
            assert state_after != state_before, f"State should not be equal {state_before}"
            assert (
                state_after != self.table.LOADING_STATE_TEXT
            ), f"State should not be equal {self.table.LOADING_STATE_TEXT}"

        wait_until_step_succeeds(_wait_state, period=1, timeout=self.default_loc_timeout)


class ClusterImportPage(ClusterPageMixin, ImportPage):
    """Cluster page import menu"""

    MENU_SUFFIX = 'import'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ImportLocators.save_btn,
        ImportLocators.import_item_block,
    ]


class ClusterConfigPage(ClusterPageMixin):
    """Cluster page config menu"""

    MENU_SUFFIX = 'config'
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

    @allure.step('Check that group field is visible = {is_group_visible} if group is active = {is_group_active}')
    def check_groups(
        self,
        group_names: List[str],
        is_group_visible: bool = True,
        is_group_active: bool = True,
        is_subs_visible: bool = True,
    ):
        group_names_on_page = [name.text for name in self.config.get_group_names()]
        if is_group_visible:
            assert group_names_on_page, "There are should be groups on the page"
            for group_name in group_names:
                self.config.expand_or_close_group(group_name, expand=is_group_active)
                self.config.check_subs_visibility(group_name, is_subs_visible)
                assert group_name in group_names_on_page, f"There is no {group_name} group on the page"
        else:
            for group_name in group_names:
                assert group_name not in group_names_on_page, f"There is visible '{group_name}' group on the page"


class ClusterGroupConfigPage(ClusterPageMixin):
    """Cluster page group config menu"""

    MENU_SUFFIX = 'group_config'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        GroupConfigListLocators.header_item,
        GroupConfigListLocators.add_btn,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]


class ClusterHostPage(ClusterPageMixin):
    """Cluster page host menu"""

    MENU_SUFFIX = 'host'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ClusterHostLocators.add_host_btn,
        CommonTable.header,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]

    @allure.step("Click on add host button")
    def click_add_host_btn(self, is_not_first_host: bool = True):
        """
        Click on the button 'Add host' under the host table.
        In case there are any hosts that have been added earlier
        (no matter from this popup or from host list page)
        there will be a popup with the list of the existing hosts,
        so to open creating host popup you need again to click on
        a special button for creating hosts.
        In case there are no hosts at all, creating hosts popup will be open instantly.
        :param is_not_first_host: flag to indicate if there are any created hosts in adcm.
        """

        self.find_and_click(ClusterHostLocators.add_host_btn)
        self.wait_element_visible(HostCreationLocators.block)
        if is_not_first_host:
            self.wait_element_visible(HostAddPopupLocators.add_new_host_btn).click()

    @allure.step("Get info about host row")
    def get_host_info_from_row(self, row_num: int = 0, table_has_cluster_column: bool = True) -> HostRowInfo:
        """
        Compile the values of the fields describing the host.
        :param table_has_cluster_column: flag to define if there is a cluster column in the table
        (e.g. there are no such column in cluster host page).
        :param row_num: row number in the table.
        """
        row = self.table.get_all_rows()[row_num]
        row_elements = ClusterHostLocators.HostTable.HostRow
        cluster_value = (
            self.find_child(row, row_elements.cluster).text
            if table_has_cluster_column
            else HostRowInfo.UNASSIGNED_CLUSTER_VALUE
        )
        return HostRowInfo(
            fqdn=self.find_child(row, row_elements.fqdn).text,
            provider=self.find_child(row, row_elements.provider).text,
            cluster=self.find_child(row, row_elements.cluster).text
            if cluster_value != HostRowInfo.UNASSIGNED_CLUSTER_VALUE
            else None,
            state=self.find_child(row, row_elements.state).text,
        )

    @allure.step("Click on host name in row")
    def click_on_host_name_in_host_row(self, row: WebElement):
        """Click on Host name in the Host row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.fqdn).click()

    @allure.step("Click on action in host row")
    def click_on_action_btn_in_host_row(self, row: WebElement):
        """Click on Action button in the Host row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.actions).click()

    @allure.step("Click on config in host row")
    def click_config_btn_in_row(self, row: WebElement):
        """Click on Configuration button in the Host row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.config).click()

    @allure.step('Click on concern of "{concern_object_name}" in host concerns')
    def click_on_concern_by_object_name(self, row: WebElement, concern_object_name: str):
        """Click on concern link in Host concerns"""
        self.hover_element(self.find_child(row, ClusterHostLocators.HostTable.HostRow.actions))
        self.wait_element_visible(PageConcernPopupLocators.block)
        for concern in self.find_elements(PageConcernPopupLocators.link_to_concern_object):
            if concern_object_name in concern.text:
                concern.click()
                return
        raise AssertionError(f'Concern name "{concern_object_name}" not found in concerns')

    def get_host_state_from_row(self, row: WebElement):
        """Get Host state from the row"""
        return self.find_child(row, ClusterHostLocators.HostTable.HostRow.state).text

    @contextmanager
    def wait_host_state_change(self, row: WebElement):
        """Wait for Host state to change"""
        state_before = self.get_host_state_from_row(row)
        yield

        def _wait_state():
            state_after = self.get_host_state_from_row(row)
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(_wait_state, period=1, timeout=self.default_loc_timeout)

    @allure.step("Run action {action_name} for host")
    def run_action_in_host_row(self, row: WebElement, action_name: str):
        """Run Host action from the row"""
        self.click_on_action_btn_in_host_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        self.find_and_click(self.table.locators.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @allure.step("Delete host")
    def delete_host_by_row(self, row: WebElement):
        """Delete Host by button from the row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.link_off_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    def check_cluster_hosts_toolbar(self, cluster_name: str, host_name: str):
        self.toolbar.check_toolbar_elements(["CLUSTERS", cluster_name, "HOSTS", host_name])


class ClusterComponentsPage(ClusterPageMixin):
    """Cluster page components menu"""

    MENU_SUFFIX = 'host_component'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ClusterComponentsLocators.restore_btn,
        ClusterComponentsLocators.save_btn,
        ClusterComponentsLocators.components_title,
        ClusterComponentsLocators.hosts_title,
        ClusterComponentsLocators.service_page_link,
        ClusterComponentsLocators.hosts_page_link,
    ]

    def click_service_page_link(self):
        """Click on Service page link"""
        self.find_and_click(ClusterComponentsLocators.service_page_link)

    def click_hosts_page_link(self):
        """Click on Hosts page link"""
        self.find_and_click(ClusterComponentsLocators.hosts_page_link)

    def click_add_host_btn(self):
        """Click on Add Host button"""
        self.find_and_click(ClusterComponentsLocators.create_hosts_btn)
        self.wait_element_visible(HostCreationLocators.block)

    def get_host_rows(self):
        """Get all hosts rows"""
        return self.find_elements(ClusterComponentsLocators.host_row)

    def get_components_rows(self):
        """Get all components rows"""
        return self.find_elements(ClusterComponentsLocators.component_row)

    def get_row_info(self, row: WebElement):
        """Get components row info"""
        return ComponentsHostRowInfo(
            name=self.find_child(row, ClusterComponentsLocators.Row.name).text,
            components=self.find_child(row, ClusterComponentsLocators.Row.number).text,
        )

    def find_host_row_by_name(self, host_name: str):
        """Find Host row by name"""
        for host_row in self.get_host_rows():
            host_name_element = self.find_child(host_row, ClusterComponentsLocators.Row.name)
            if host_name_element.text == host_name:
                return host_row
        raise AssertionError(f"There are no host with name '{host_name}'")

    def find_component_row_by_name(self, component_name: str):
        """Find Component row by name"""
        for component_row in self.get_components_rows():
            component_name_element = self.find_child(component_row, ClusterComponentsLocators.Row.name)
            if component_name_element.text == component_name:
                return component_row
        raise AssertionError(f"There are no component with name '{component_name}'")

    @allure.step("Click on host row")
    def click_host(self, host_row: WebElement):
        """Click on Host row"""
        self.find_child(host_row, ClusterComponentsLocators.Row.name).click()

    @allure.step("Click on component row")
    def click_component(self, component_row: WebElement):
        """Click on Component row"""
        self.find_child(component_row, ClusterComponentsLocators.Row.name).click()

    @allure.step("Click on row number in component row")
    def click_number_in_component(self, component_row: WebElement):
        """Click on Component row number"""
        self.find_child(component_row, ClusterComponentsLocators.Row.number).click()

    @allure.step("Click on save button")
    def click_save_btn(self):
        """Click on Save button"""
        self.find_and_click(ClusterComponentsLocators.save_btn)

    @allure.step("Click on restore button")
    def click_restore_btn(self):
        """Click on Restore button"""
        self.find_and_click(ClusterComponentsLocators.restore_btn)

    @allure.step("Delete item {item_name} from row")
    def delete_related_item_in_row_by_name(self, row: WebElement, item_name: str):
        """Delete related item by button from row"""
        self.wait_element_visible(ClusterComponentsLocators.Row.relations_row)
        for item_row in self.find_children(row, ClusterComponentsLocators.Row.relations_row):
            item_name_element = self.find_child(item_row, ClusterComponentsLocators.Row.RelationsRow.name)
            if item_name_element.text == item_name:
                self.find_child(item_row, ClusterComponentsLocators.Row.RelationsRow.delete_btn).click()
                return
        raise AssertionError(f"There are no item with name '{item_name}'")

    def check_that_save_btn_disabled(self):
        """Get Save button available state"""
        return self.find_element(ClusterComponentsLocators.save_btn).get_attribute("disabled") == "true"


class ClusterStatusPage(ClusterPageMixin, StatusPage):
    """Cluster page status menu"""

    MENU_SUFFIX = 'status'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ClusterGroupConfigPageMixin(BasePageObject):
    """Helpers for working with cluster group config page"""

    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    cluster_id: int
    group_config_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    group_config: CommonGroupConfigMenu
    toolbar: CommonToolbar
    table: CommonTableObj

    def __init__(self, driver, base_url, cluster_id: int, group_config_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(
            driver,
            base_url,
            "/cluster/{cluster_id}/group_config/{group_config_id}/" + self.MENU_SUFFIX,
            cluster_id=cluster_id,
            group_config_id=group_config_id,
        )
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.group_config = CommonGroupConfigMenu(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.group_config_id = group_config_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)

    @allure.step("Assert that all main elements on the page are presented")
    def check_all_elements(self):
        """Assert all main elements presence"""
        self.assert_displayed_elements(self.MAIN_ELEMENTS)

    def open_hosts_tab(self):
        """Open Hosts tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.hosts_tab)
        page = ClusterGroupConfigHosts(self.driver, self.base_url, self.cluster_id, self.group_config_id)
        page.wait_page_is_opened()
        return page

    def open_config_tab(self):
        """Open Hosts tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.config_tab)
        page = ClusterGroupConfigConfig(self.driver, self.base_url, self.cluster_id, self.group_config_id)
        page.wait_page_is_opened()
        return page

    def check_cluster_group_conf_toolbar(self, cluster_name: str, group_name: str):
        self.toolbar.check_toolbar_elements(["CLUSTERS", cluster_name, "GROUPCONFIGS", group_name])


class ClusterGroupConfigHosts(ClusterGroupConfigPageMixin):
    """Cluster page status menu"""

    MENU_SUFFIX = 'host'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ClusterGroupConfigConfig(ClusterGroupConfigPageMixin):
    """Cluster page status menu"""

    MENU_SUFFIX = 'config'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]
