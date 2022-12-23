from selenium.webdriver.common.by import By
from tests.ui_tests.app.page.common.dialogs.locators import Dialog
from tests.ui_tests.core.elements import AutoChildDialog
from tests.ui_tests.core.locators import Descriptor, Locator, autoname


class DeleteDialog(AutoChildDialog):
    @autoname
    class Locators(Dialog):
        yes = Locator(By.XPATH, "//button//span[contains(text(), 'Yes')]", Descriptor.BUTTON)

    def confirm(self) -> None:
        self.yes_button.click()
        self.wait_closed()
