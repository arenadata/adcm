from selenium.webdriver.common.by import By

from tests.ui_tests.app.page.common.dialogs.locators import Dialog
from tests.ui_tests.core.elements import AutoChildDialog
from tests.ui_tests.core.locators import Descriptor, Locator, autoname


class _Locators(Dialog):
    title = Locator(By.CSS_SELECTOR, "mat-dialog-container h3")
    name = Locator(By.CSS_SELECTOR, "adwp-input[label='Group name'] input", Descriptor.TEXT | Descriptor.INPUT)
    description = Locator(By.CSS_SELECTOR, "adwp-input[label='Description'] input", Descriptor.TEXT | Descriptor.INPUT)
    users = Locator(
        By.CSS_SELECTOR,
        "adwp-input-select[label='Select users'] adwp-select",
        Descriptor.TEXT | Descriptor.ELEMENT,
    )
    user_item = Locator(By.CSS_SELECTOR, "adwp-selection-list mat-list-option", Descriptor.ELEMENT)

    class UserRow:
        checkbox = Locator(By.CSS_SELECTOR, "mat-pseudo-checkbox", Descriptor.ELEMENT, name="User row checkbox")


class _AddUsersMixin:
    def add_users(self, usernames: list[str]) -> None:
        self.users_element.click()
        for user_item in self._view.find_elements(self.Locators.user_item, timeout=3):
            if user_item.text not in usernames:
                continue
            checkbox = self._view.find_child(user_item, self.Locators.UserRow.checkbox)
            self._view.hover_element(checkbox)
            checkbox.click()
        self.users_element.click()
        self._view.wait_element_hide(self.Locators.user_item, timeout=2)


class AddGroupDialog(AutoChildDialog, _AddUsersMixin):
    @autoname
    class Locators(_Locators):
        add = Locator(By.XPATH, "//button[./span[contains(text(), 'Add')]]", Descriptor.BUTTON)

    def add(self) -> None:
        self._view.scroll_to(self.add_button)
        self.add_button.click()
        self.wait_closed()


class UpdateGroupDialog(AutoChildDialog, _AddUsersMixin):
    @autoname
    class Locators(_Locators):
        update = Locator(By.XPATH, "//button[./span[contains(text(), 'Update')]]", Descriptor.BUTTON)

    def update(self) -> None:
        self._view.scroll_to(self.update_button)
        self.update_button.click()
        self.wait_closed()
