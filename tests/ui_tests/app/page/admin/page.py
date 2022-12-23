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

"""Admin pages PageObjects classes"""

from dataclasses import dataclass
from typing import Collection, List, Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from tests.library.predicates import name_is
from tests.library.utils import get_or_raise
from tests.ui_tests.app.page.admin.locators import (
    AdminIntroLocators,
    AdminPoliciesLocators,
    AdminRolesLocators,
    AdminSettingsLocators,
    AdminUsersLocators,
    CommonAdminPagesLocators,
    LoginAuditLocators,
    OperationsAuditLocators,
)
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.common_locators import ObjectPageMenuLocators
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs.delete import DeleteDialog
from tests.ui_tests.app.page.common.dialogs.group import (
    AddGroupDialog,
    UpdateGroupDialog,
)
from tests.ui_tests.app.page.common.dialogs.locators import DeleteDialogLocators
from tests.ui_tests.app.page.common.dialogs.operation_changes import (
    OperationChangesDialog,
)
from tests.ui_tests.app.page.common.dialogs.role import (
    CreateRoleDialog,
    UpdateRoleDialog,
)
from tests.ui_tests.app.page.common.dialogs.user import AddUserDialog, UpdateUserDialog
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.core.checks import check_elements_are_displayed
from tests.ui_tests.core.elements import AutoChildElement, ObjectRowMixin
from tests.ui_tests.core.locators import BaseLocator, Descriptor, Locator, autoname


@dataclass
class AdminPolicyInfo:
    """Information about policy"""

    name: str
    description: Optional[str]
    role: str
    users: Optional[str]
    groups: Optional[str]
    objects: Optional[str]


class GeneralAdminPage(BasePageObject):
    """Base class for admin pages"""

    MENU_SUFFIX: str
    MAIN_ELEMENTS: List[BaseLocator]
    MAIN_ELEMENTS: Collection[BaseLocator]
    config: CommonConfigMenuObj
    table: CommonTableObj
    toolbar: CommonToolbar

    def __init__(self, driver, base_url):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, "/admin/" + self.MENU_SUFFIX)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.table = CommonTableObj(driver=self.driver)
        self.toolbar = CommonToolbar(self.driver, self.base_url)

    @allure.step("Assert that all main elements are presented on the page")
    def check_all_elements(self):
        """Assert presence of the MAIN_ELEMENTS"""

        if len(self.MAIN_ELEMENTS) == 0:
            raise AttributeError('MAIN_ELEMENTS should contain at least 1 element')
        check_elements_are_displayed(self, self.MAIN_ELEMENTS)

    @allure.step("Check admin toolbar")
    def check_admin_toolbar(self):
        check_elements_are_displayed(self, [CommonToolbarLocators.admin_link])

    @allure.step('Open Admin Intro page by left menu item click')
    def open_intro_menu(self) -> "AdminIntroPage":
        """Open Admin Intro page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.intro_tab)
        page = AdminIntroPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin Settings page by left menu item click')
    def open_settings_menu(self) -> "AdminSettingsPage":
        """Open Admin Settings page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.settings_tab)
        page = AdminSettingsPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin Users page by left menu item click')
    def open_users_menu(self) -> "AdminUsersPage":
        """Open Admin Users page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.users_tab)
        page = AdminUsersPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin groups page by left menu item click')
    def open_groups_menu(self) -> "AdminGroupsPage":
        """Open Admin groups page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.groups_tab)
        page = AdminGroupsPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin Roles page by left menu item click')
    def open_roles_menu(self) -> "AdminRolesPage":
        """Open Admin Roles page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.roles_tab)
        page = AdminRolesPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin policies page by left menu item click')
    def open_policies_menu(self) -> "AdminPoliciesPage":
        """Open Admin policies page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.policies_tab)
        page = AdminPoliciesPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Admin Operations Audit page by left menu item click")
    def open_operations_menu(self) -> "OperationsAuditPage":
        self.find_and_click(ObjectPageMenuLocators.operations_tab)
        page = OperationsAuditPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page


class AdminIntroPage(GeneralAdminPage):
    """Admin Intro Page class"""

    MENU_SUFFIX = 'intro'
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        CommonToolbarLocators.admin_link,
    ]


class AdminSettingsPage(GeneralAdminPage):
    """Admin Settings Page class"""

    MENU_SUFFIX = 'settings'
    MAIN_ELEMENTS = [
        AdminSettingsLocators.save_btn,
        AdminSettingsLocators.search_input,
        AdminSettingsLocators.advanced_label,
        CommonToolbarLocators.admin_link,
    ]


# !===== Users Page =====!


class UserRow(AutoChildElement):
    @autoname
    class Locators:
        username = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", Descriptor.TEXT | Descriptor.ELEMENT)
        groups = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(4)")
        email = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)")
        select = Locator(By.XPATH, ".//span[.//input[@type='checkbox']]", Descriptor.INPUT)
        delete = Locator(By.XPATH, ".//button[.//mat-icon[text()='delete']]", Descriptor.BUTTON)

    @property
    def is_active(self) -> bool:
        return "inactive" not in self._element.get_attribute("class")

    @property
    def is_delete_button_presented(self) -> bool:
        return self._view.is_child_displayed(self._element, self.Locators.delete, timeout=1)

    def get_groups(self) -> tuple[str, ...]:
        return tuple(group.strip() for group in self.groups.split(","))

    def open_update_dialog(self) -> UpdateUserDialog:
        self.username_element.click()
        return UpdateUserDialog.wait_opened(interactor=self._view)


class AdminUsersPage(GeneralAdminPage, ObjectRowMixin):
    """Admin Users Page class"""

    ROW_CLASS = UserRow
    MENU_SUFFIX = "users"
    MAIN_ELEMENTS = [
        AdminUsersLocators.create_user_button,
        AdminUsersLocators.user_row,
        CommonToolbarLocators.admin_link,
    ]

    def get_all_user_names(self) -> list[str]:
        return [user.username for user in self.get_rows()]

    @allure.step('Create new user "{username}" with password "{password}"')
    def create_user(self, username: str, password: str, first_name: str, last_name: str, email: str):
        self.find_and_click(AdminUsersLocators.create_user_button)
        dialog = AddUserDialog.wait_opened(driver=self.driver)
        dialog.username_input.fill(username)
        dialog.password_input.fill(password)
        dialog.password_confirm_input.fill(password)
        dialog.first_name_input.fill(first_name)
        dialog.last_name_input.fill(last_name)
        dialog.email_input.fill(email)
        dialog.add()

    @allure.step('Delete selected users')
    def delete_selected_users(self):
        self.find_and_click(AdminUsersLocators.delete_users, timeout=1)
        dialog = DeleteDialog.wait_opened(self.driver)
        dialog.yes_button.click()
        dialog.wait_closed()

    @allure.step("Filter users by {name}={value}")
    def filter_users_by(self, name: str, value: str):
        self.find_and_click(AdminUsersLocators.filter_btn)
        self.wait_element_visible(AdminUsersLocators.FilterPopup.block)

        suitable_filter = get_or_raise(
            self.find_elements(AdminUsersLocators.FilterPopup.filter_item),
            lambda element: element.text.lower() == name.lower(),
        )
        suitable_filter.click()

        self.wait_element_visible(AdminUsersLocators.filter_dropdown_select).click()
        self.wait_element_visible(AdminUsersLocators.filter_dropdown_option)

        suitable_option = get_or_raise(
            self.find_elements(AdminUsersLocators.filter_dropdown_option),
            lambda element: element.text.lower() == value.lower(),
        )
        suitable_option.click()

        self.wait_page_is_opened()

    @allure.step("Remove filter from users page")
    def remove_user_filter(self):
        self.find_and_click(AdminUsersLocators.filter_dropdown_remove)
        self.wait_page_is_opened()


# !===== Groups Page =====!


class GroupRow(AutoChildElement):
    @autoname
    class Locators:
        checkbox = Locator(By.CSS_SELECTOR, "mat-checkbox", Descriptor.ELEMENT)
        name = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", Descriptor.TEXT | Descriptor.ELEMENT)
        description = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", Descriptor.TEXT)
        users = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(4)", Descriptor.TEXT)

    def get_users(self) -> tuple[str, ...]:
        return tuple(user.strip() for user in self.users.split(","))

    def open_update_dialog(self) -> UpdateUserDialog:
        self.name_element.click()
        return UpdateGroupDialog.wait_opened(interactor=self._view)

    def __iter__(self):
        yield "name", self.name
        yield "description", self.description
        yield "users", self.users


class AdminGroupsPage(GeneralAdminPage, ObjectRowMixin):
    ROW_CLASS = GroupRow
    MENU_SUFFIX = "groups"
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        CommonAdminPagesLocators.create_btn,
        CommonAdminPagesLocators.delete_btn,
        CommonTable.header,
    ]

    def open_add_group_dialog(self) -> AddGroupDialog:
        self.find_and_click(CommonAdminPagesLocators.create_btn)
        return AddGroupDialog.wait_opened(driver=self.driver)

    @allure.step('Create custom group {name}')
    def create_custom_group(self, name: str, description: str, users: list[str]):
        dialog = self.open_add_group_dialog()
        dialog.name_input.fill(name)
        dialog.description_input.fill(description)
        dialog.add_users(users)
        dialog.add()

    def select_all_groups(self):
        self.find_elements(self.table.locators.header)[0].click()

    def delete_selected_groups(self):
        self.find_and_click(AdminRolesLocators.delete_btn)
        DeleteDialog.wait_opened(self.driver).confirm()


# !===== Roles Page =====!


class RoleRow(AutoChildElement):
    @autoname
    class Locators:
        checkbox = Locator(By.CSS_SELECTOR, "mat-checkbox", Descriptor.ELEMENT)
        name = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", Descriptor.TEXT | Descriptor.ELEMENT)
        description = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", Descriptor.TEXT)
        permissions = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(4)", Descriptor.ELEMENT)

    @property
    def permissions(self) -> list[str]:
        return self.permissions_element.text.split(", ")

    def __iter__(self):
        yield "name", self.name
        yield "description", self.description
        yield "permissions", self.permissions


class AdminRolesPage(GeneralAdminPage, ObjectRowMixin):

    ROW_CLASS = RoleRow
    MENU_SUFFIX = "roles"
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        AdminRolesLocators.create_btn,
        AdminRolesLocators.delete_btn,
        CommonTable.header,
        CommonTable.row,
    ]

    @allure.step("Open create role popup")
    def open_create_role_dialog(self) -> CreateRoleDialog:
        self.find_and_click(AdminRolesLocators.create_btn)
        return CreateRoleDialog.wait_opened(driver=self.driver)

    @allure.step("Create new role")
    def create_role(self, name: str, description: str, permissions: list[str]):
        dialog = self.open_create_role_dialog()
        dialog.name_input.fill(name)
        dialog.description_input.fill(description)
        dialog.add_permissions(permissions)
        dialog.add()

    @allure.step("Open role {role_name}")
    def open_role_by_name(self, role_name: str) -> UpdateRoleDialog:
        row = self.get_row(name_is(role_name))
        row.name_element.click()
        return UpdateRoleDialog.wait_opened(driver=self.driver)

    def select_all_roles(self):
        self.find_elements(self.table.locators.header)[0].click()

    def delete_selected_roles(self):
        self.find_and_click(AdminRolesLocators.delete_btn)
        DeleteDialog.wait_opened(driver=self.driver).confirm()


# !===== Policies Page =====!


class AdminPoliciesPage(GeneralAdminPage):
    """Admin Policy Page class"""

    MENU_SUFFIX = 'policies'
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        CommonAdminPagesLocators.create_btn,
        CommonAdminPagesLocators.delete_btn,
        CommonTable.header,
    ]

    def open_create_policy_popup(self):
        self.find_and_click(AdminPoliciesLocators.create_btn)
        self.wait_element_visible(AdminPoliciesLocators.AddPolicyPopup.block)

    @allure.step('Fill first step in new policy')
    def fill_first_step_in_policy_popup(
        self,
        policy_name: str,
        description: Optional[str],
        role: str,
        users: Optional[str],
        groups: Optional[str],
    ):
        if not (users or groups):
            raise ValueError("There are should be users or groups in the policy")
        self.send_text_to_element(AdminPoliciesLocators.AddPolicyPopup.FirstStep.name_input, policy_name)
        if description:
            self.send_text_to_element(AdminPoliciesLocators.AddPolicyPopup.FirstStep.description_input, description)
        with allure.step(f"Select role {role} in popup"):
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.role_select)
            self.wait_element_visible(AdminPoliciesLocators.AddPolicyPopup.FirstStep.role_item)
            available_roles = self.find_elements(AdminPoliciesLocators.AddPolicyPopup.FirstStep.role_item)
            for available_role in available_roles:
                if available_role.text == role:
                    self.scroll_to(available_role)
                    self.hover_element(available_role)
                    available_role.click()
                    break
            else:
                raise AssertionError(f"There are no role {role} in select role popup")
        if users:
            with allure.step(f"Select users {users} in popup"):
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.users_select)
                self.wait_element_visible(AdminPoliciesLocators.item)
                self.fill_select_in_policy_popup(users, AdminPoliciesLocators.item)
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.users_select)
        if groups:
            with allure.step(f"Select groups {groups} in popup"):
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.group_select)
                self.wait_element_visible(AdminPoliciesLocators.item)
                self.fill_select_in_policy_popup(groups, AdminPoliciesLocators.item)
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.group_select)
        self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.next_btn_first)

    def fill_select_in_policy_popup(self, items, available_items_locator):
        for item in items.split(", "):
            self.wait_element_visible(available_items_locator)
            for count, available_item in enumerate(self.find_elements(available_items_locator)):
                try:
                    if available_item.text == item:
                        available_item.click()
                        break
                except StaleElementReferenceException:
                    if self.find_elements(available_items_locator)[count].text == item:
                        self.find_elements(available_items_locator)[count].click()
                        break
            else:
                raise AssertionError(f"There are no item {item} in select popup")

    @allure.step('Fill second step in new policy')
    def fill_second_step_in_policy_popup(
        self,
        clusters: Optional[str] = None,
        services: Optional[str] = None,
        parent: Optional[str] = None,
        providers: Optional[str] = None,
        hosts: Optional[str] = None,
    ):
        self.wait_element_visible(AdminPoliciesLocators.AddPolicyPopup.SecondStep.next_btn_second)

        def fill_select(locator_select: BaseLocator, locator_items: BaseLocator, values: str):
            with allure.step(f"Select {values} in popup"):
                self.wait_element_visible(locator_select)
                self.find_and_click(locator_select)
                self.wait_element_visible(locator_items)
                self.fill_select_in_policy_popup(values, locator_items)

        if clusters:
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.cluster_select,
                AdminPoliciesLocators.item,
                clusters,
            )
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.cluster_select)
        if services:
            if not parent:
                raise ValueError("There are should be parent for service")
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.service_select,
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.service_item,
                services,
            )
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.parent_select,
                AdminPoliciesLocators.item,
                parent,
            )
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.parent_select)

        if hosts:
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.hosts_select,
                AdminPoliciesLocators.item,
                hosts,
            )
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.hosts_select)
        if providers:
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.provider_select,
                AdminPoliciesLocators.item,
                providers,
            )
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.provider_select)
        self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.next_btn_second)

    @allure.step('Fill third step in new policy')
    def fill_third_step_in_policy_popup(self):
        self.wait_element_visible(AdminPoliciesLocators.save_update_btn)
        self.find_and_click(AdminPoliciesLocators.save_update_btn)
        self.wait_element_hide(AdminPoliciesLocators.AddPolicyPopup.block)

    @allure.step('Create new policy')
    def create_policy(
        self,
        policy_name: str,
        description: Optional[str],
        role: str,
        users: Optional[str] = None,
        groups: Optional[str] = None,
        clusters: Optional[str] = None,
        services: Optional[str] = None,
        parent: Optional[str] = None,
        providers: Optional[str] = None,
        hosts: Optional[str] = None,
    ):

        self.open_create_policy_popup()
        self.fill_first_step_in_policy_popup(policy_name, description, role, users, groups)
        self.fill_second_step_in_policy_popup(clusters, services, parent, providers, hosts)
        self.fill_third_step_in_policy_popup()

    def get_all_policies(self) -> [AdminPolicyInfo]:
        """Get all policies info and returns list with policies names."""

        policies_items = []
        policies_rows = self.table.get_all_rows()
        for policy in policies_rows:
            policy_groups = self.find_child(policy, AdminPoliciesLocators.PolicyRow.groups).text
            policy_objects = self.find_child(policy, AdminPoliciesLocators.PolicyRow.objects).text
            policy_item = AdminPolicyInfo(
                name=self.find_child(policy, AdminPoliciesLocators.PolicyRow.name).text,
                description=self.find_child(policy, AdminPoliciesLocators.PolicyRow.description).text,
                role=self.find_child(policy, AdminPoliciesLocators.PolicyRow.role).text,
                users=self.find_child(policy, AdminPoliciesLocators.PolicyRow.users).text,
                groups=policy_groups if policy_groups else None,
                objects=policy_objects if policy_objects else None,
            )
            policies_items.append(policy_item)
        return policies_items

    def select_all_policies(self):
        # first header element is checkbox for selecting all policies
        self.find_elements(self.table.locators.header)[0].click()

    def click_delete_button(self):
        """Click delete button and confirm the action in dialog popup."""

        self.find_and_click(AdminPoliciesLocators.delete_btn)
        self.wait_element_visible(DeleteDialogLocators.body)
        self.find_and_click(DeleteDialogLocators.yes)
        self.wait_element_hide(DeleteDialogLocators.body)

    def delete_all_policies(self):
        def delete_all():
            self.select_all_policies()
            if "disabled" not in self.find_element(AdminPoliciesLocators.delete_btn).get_attribute("class"):
                self.click_delete_button()
            assert len(self.table.get_all_rows()) == 0, "There should be 0 policies on the page"

        wait_until_step_succeeds(delete_all, period=5)


# !===== Audit =====!


class GeneralAuditPage(GeneralAdminPage):
    FILTER_LOCATORS = None

    def add_filter(self, filter_menu_name: str) -> None:
        """Filter name is the visible name of filter in menu"""
        filter_locators = self.FILTER_LOCATORS
        self.find_and_click(filter_locators.button)
        self.wait_element_visible(filter_locators.menu)

        suitable_option = next(
            filter(
                lambda child: child.text.strip() == filter_menu_name,
                self.find_children(self.find_element(filter_locators.menu, timeout=0.5), filter_locators.choice),
            ),
            None,
        )
        if suitable_option is None:
            raise AssertionError(f"Failed to find filter named '{filter_menu_name}'")

        suitable_option.click()
        self.wait_element_hide(filter_locators.menu)

    def remove_filter(self, filter_position: int) -> None:
        filter_buttons = self.find_elements_or_empty(self.FILTER_LOCATORS.remove_button)
        amount_of_buttons = len(filter_buttons)
        if filter_position >= amount_of_buttons:
            raise ValueError(f"Can't get remove element #{filter_position}, because there's only {amount_of_buttons}")

        filter_buttons[filter_position].click()

        wait_until_step_succeeds(
            self._remove_buttons_amount_should_decrease, initial_amount=amount_of_buttons, timeout=2, period=0.5
        )

    def refresh_filter(self, filter_position: int) -> None:
        filter_buttons = self.find_elements_or_empty(self.FILTER_LOCATORS.refresh_button)
        amount_of_buttons = len(filter_buttons)
        if filter_position >= amount_of_buttons:
            raise ValueError(f"Can't get remove element #{filter_position}, because there's only {amount_of_buttons}")

        filter_buttons[filter_position].click()

    def is_filter_visible(self, filter_name: str, timeout: int = 1) -> bool:
        locators = self.FILTER_LOCATORS.Item

        if not hasattr(locators, filter_name):
            raise ValueError("Incorrect filter name")

        filters_block = self.find_element(self.FILTER_LOCATORS.block, timeout=1)
        return self.is_child_displayed(filters_block, getattr(locators, filter_name), timeout=timeout)

    def get_filter_input(self, filter_name: str) -> WebElement:
        """
        Based on filter, return element will be:
        - input
        - mat-select
        - mat-date-range-input
        """
        locators = self.FILTER_LOCATORS.Item

        if not hasattr(locators, filter_name):
            raise ValueError("Incorrect filter name")

        filters_block = self.find_element(self.FILTER_LOCATORS.block, timeout=1)
        return self.find_child(filters_block, getattr(locators, filter_name), timeout=3)

    def pick_filter_value(self, filter_input: WebElement, value_to_pick: str) -> None:
        filter_input.click()
        dropdown_locator = self.FILTER_LOCATORS.dropdown_option
        self.wait_element_visible(dropdown_locator)

        suitable_option: WebElement | None = next(
            filter(lambda option: option.text.strip() == value_to_pick, self.find_elements(dropdown_locator)), None
        )
        if suitable_option is None:
            raise AssertionError(f"Failed to find option with value '{value_to_pick}'")

        suitable_option.click()

        self.wait_element_hide(dropdown_locator)

    def _remove_buttons_amount_should_decrease(self, initial_amount: int) -> None:
        assert (
            len(self.find_elements_or_empty(self.FILTER_LOCATORS.remove_button)) < initial_amount
        ), f"There should be less than {initial_amount} buttons"


@dataclass()
class OperationRowInfo:
    object_type: str
    object_name: str
    operation_name: str
    operation_type: str
    operation_result: str
    operation_time: str
    username: str


class OperationsAuditPage(GeneralAuditPage):

    MENU_SUFFIX = "audit/operations"
    FILTER_LOCATORS = OperationsAuditLocators.Filter
    MAIN_ELEMENTS = (OperationsAuditLocators.Filter.button,)

    def get_audit_operation_info(self, row: WebElement) -> OperationRowInfo:
        return OperationRowInfo(
            **{
                field: self.find_child(row, getattr(OperationsAuditLocators.Row, field), timeout=0.5).text
                for field in (
                    "object_type",
                    "object_name",
                    "operation_name",
                    "operation_type",
                    "operation_result",
                    "operation_time",
                    "username",
                )
            }
        )

    def get_info_from_all_rows(self) -> tuple[OperationRowInfo, ...]:
        return tuple(self.get_audit_operation_info(row) for row in self.table.get_all_rows(timeout=2))

    def open_changes_dialog(self, row: WebElement) -> OperationChangesDialog:
        self.get_show_changes_button(row).click()
        return OperationChangesDialog(self.driver, self.base_url)

    def get_show_changes_button(self, row: WebElement) -> WebElement:
        return self.find_child(row, OperationsAuditLocators.Row.show_changes, timeout=1)

    def click_out_of_filter(self):
        self.find_and_click(OperationsAuditLocators.title, timeout=1.5)


@dataclass()
class LoginRowInfo:
    login: str
    result: str
    login_time: str


class LoginAuditPage(GeneralAuditPage):

    MENU_SUFFIX = "audit/logins"
    MAIN_ELEMENTS = (LoginAuditLocators.Filter.button,)
    FILTER_LOCATORS = LoginAuditLocators.Filter

    def get_audit_login_info(self, row: WebElement) -> LoginRowInfo:
        return LoginRowInfo(
            **{
                field: self.find_child(row, getattr(LoginAuditLocators.Row, field), timeout=0.5).text
                for field in ("login", "result", "login_time")
            }
        )

    def get_info_from_all_rows(self) -> tuple[LoginRowInfo, ...]:
        return tuple(self.get_audit_login_info(row) for row in self.table.get_all_rows(timeout=2))

    def click_out_of_filter(self):
        self.find_and_click(LoginAuditLocators.title, timeout=1.5)
