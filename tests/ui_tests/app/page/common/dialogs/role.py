from operator import attrgetter

from selenium.webdriver.common.by import By
from tests.library.predicates import name_is
from tests.library.utils import get_or_raise
from tests.ui_tests.app.page.common.dialogs.locators import Dialog
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.core.elements import AutoChildDialog, AutoChildElement
from tests.ui_tests.core.locators import Descriptor, Locator, autoname


class _AvailablePermission(AutoChildElement):
    @autoname
    class Locators:
        name = Locator(By.CSS_SELECTOR, "div", Descriptor.TEXT)

    def pick(self) -> None:
        self._element.click()


class _ChosenPermission(AutoChildElement):
    @autoname
    class Locators:
        delete = Locator(By.CSS_SELECTOR, "button", Descriptor.BUTTON)

    @property
    def name(self):
        # just "text" returns more than a name, so it's the way I guess
        return self._element.text.split("\n")[0].strip()


class _PermissionsPick(AutoChildElement):
    @autoname
    class Locators:
        filter = Locator(By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-filter input", Descriptor.INPUT)
        available_item = Locator(By.TAG_NAME, "mat-list-option", Descriptor.SERVICE)
        chosen_item = Locator(By.TAG_NAME, "mat-chip", Descriptor.SERVICE)
        select = Locator(By.CSS_SELECTOR, ".adcm-rbac-permission__actions button", Descriptor.BUTTON)
        clear = Locator(By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-filter-clear", Descriptor.BUTTON)

    def get_available_permissions(self) -> list[_AvailablePermission]:
        return [
            _AvailablePermission(parent_element=element, interactor=self._view)
            for element in self._view.find_elements(self.Locators.available_item, timeout=1)
        ]

    def get_chosen_permissions(self) -> list[_ChosenPermission]:
        return [
            _ChosenPermission(parent_element=element, interactor=self._view)
            for element in self._view.find_elements(self.Locators.chosen_item, timeout=1)
        ]


class _Locators(Dialog):
    name = Locator(By.CSS_SELECTOR, "adwp-input[controlname='display_name'] input", Descriptor.INPUT | Descriptor.TEXT)
    description = Locator(
        By.CSS_SELECTOR, "adwp-input[controlname='description'] input", Descriptor.INPUT | Descriptor.TEXT
    )
    field_error = Locator(By.TAG_NAME, "mat-error", Descriptor.SERVICE)
    cancel = Locator(By.XPATH, "//button[./span[contains(text(), 'Cancel')]]", Descriptor.BUTTON)


class _RoleDialogMixin:
    def add_permissions(self, permissions: list[str]) -> None:
        picker = _PermissionsPick(parent_element=self._element, interactor=self._view)
        available_permissions = picker.get_available_permissions()
        for name in permissions:
            suitable_permission = get_or_raise(available_permissions, name_is(name))
            suitable_permission.pick()
        picker.select_button.click()

    def remove_permissions(self, permissions: list[str]) -> None:
        picker = _PermissionsPick(parent_element=self._element, interactor=self._view)
        for name in permissions:
            # we need to get permissions each time to avoid working with stale element
            suitable_permission = get_or_raise(picker.get_chosen_permissions(), name_is(name))
            suitable_permission.delete_button.click()

    def clear_permissions(self) -> None:
        picker = _PermissionsPick(parent_element=self._element, interactor=self._view)
        picker.clear_button.click()

    def get_error_messages(self) -> set[str]:
        return set(map(attrgetter("text"), self._view.find_elements(self.Locators.field_error, timeout=3)))


class CreateRoleDialog(AutoChildDialog, _RoleDialogMixin):
    @autoname
    class Locators(_Locators):
        add = Locator(By.XPATH, "//button[./span[contains(text(), 'Add')]]", Descriptor.BUTTON)

    def add(self) -> None:
        self.add_button.click()
        self.wait_closed()
        self._view.wait_element_hide(CommonToolbarLocators.progress_bar, timeout=5)


class UpdateRoleDialog(AutoChildDialog, _RoleDialogMixin):
    @autoname
    class Locators(_Locators):
        update = Locator(By.XPATH, "//button[./span[contains(text(), 'Update')]]", Descriptor.BUTTON)

    def update(self) -> None:
        self.update_button.click()
        self.wait_closed()
        self._view.wait_element_hide(CommonToolbarLocators.progress_bar, timeout=5)

    def is_update_enabled(self) -> bool:
        return self.update_button.is_enabled()
