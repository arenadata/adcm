from operator import attrgetter

from selenium.webdriver.common.by import By

from tests.library.utils import get_or_raise
from tests.ui_tests.app.page.common.dialogs.locators import Dialog
from tests.ui_tests.core.elements import AutoChildDialog
from tests.ui_tests.core.locators import Descriptor, Locator, autoname


class _Locators(Dialog):
    username = Locator(By.NAME, "username", Descriptor.TEXT | Descriptor.ELEMENT | Descriptor.INPUT)
    password = Locator(By.CSS_SELECTOR, "input[data-placeholder='Password']", Descriptor.INPUT | Descriptor.ELEMENT)
    password_confirm = Locator(
        By.CSS_SELECTOR,
        "input[data-placeholder='Confirm password']",
        Descriptor.INPUT | Descriptor.ELEMENT,
    )
    first_name = Locator(By.NAME, "first_name", Descriptor.TEXT | Descriptor.ELEMENT | Descriptor.INPUT)
    last_name = Locator(By.NAME, "last_name", Descriptor.TEXT | Descriptor.ELEMENT | Descriptor.INPUT)
    email = Locator(By.NAME, "email", Descriptor.TEXT | Descriptor.ELEMENT | Descriptor.INPUT)
    groups = Locator(
        By.CSS_SELECTOR,
        "adwp-input-select[controlname='group']",
        Descriptor.TEXT | Descriptor.ELEMENT,
    )
    group_item = Locator(By.CSS_SELECTOR, "mat-list-option[role='option']", Descriptor.ELEMENT)
    cancel = Locator(By.XPATH, "//button[./span[contains(text(), 'Cancel')]]", Descriptor.BUTTON)


class UpdateUserDialog(AutoChildDialog):
    @autoname
    class Locators(_Locators):
        update = Locator(By.XPATH, "//button[./span[contains(text(), 'Update')]]", Descriptor.BUTTON)

    def get_unavailable_groups(self) -> tuple[str, ...]:
        """Get groups that are not allowed to be picked for user"""
        self.groups_element.click()
        self._view.wait_element_visible(self.Locators.group_item, timeout=1.5)
        names = tuple(
            map(
                attrgetter("text"),
                filter(
                    lambda group: "disabled" in group.get_attribute("class"),
                    self._view.find_elements(self.Locators.group_item, timeout=1),
                ),
            ),
        )
        self.first_name_element.click()
        self._view.wait_element_hide(self.Locators.group_item, timeout=1.5)
        return names

    def add_to_group(self, group: str):
        self.groups_element.click()
        self._view.wait_element_visible(self.Locators.group_item, timeout=1.5)
        suitable_group = get_or_raise(
            self._view.find_elements(self.Locators.group_item),
            lambda element: element.text == group,
        )
        self._view.scroll_to(suitable_group)
        self._view.hover_element(suitable_group)
        suitable_group.click()
        self.first_name_element.click()
        self._view.wait_element_hide(self.Locators.group_item, timeout=1.5)

    def has_update_button(self) -> bool:
        return self._view.is_child_displayed(self._element, self.Locators.update, timeout=1)

    def update(self) -> None:
        self._view.scroll_to(self.update_button)
        self.update_button.click()
        self.wait_closed()


class AddUserDialog(AutoChildDialog):
    @autoname
    class Locators(_Locators):
        add = Locator(By.XPATH, "//button[./span[contains(text(), 'Add')]]", Descriptor.BUTTON)

    def add(self) -> None:
        self._view.scroll_to(self.add_button)
        self.add_button.click()
        self.wait_closed()
