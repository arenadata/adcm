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

from typing import Callable, Union

import allure
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from tests.library.utils import get_or_raise
from tests.ui_tests.app.page.common.dialogs.locators import Dialog
from tests.ui_tests.core.elements import AutoChildDialog
from tests.ui_tests.core.interactors import Interactor
from tests.ui_tests.core.locators import BaseLocator, Descriptor, Locator, autoname


class _Locators(Dialog):
    # item of selector
    selector_item = Locator(By.CSS_SELECTOR, "adwp-selection-list mat-list-option", Descriptor.ELEMENT)


def prepare_multiple_pick(
    item_name: str, selector_name: str, item_locator: BaseLocator = _Locators.selector_item
) -> Callable[[Union["AddPolicyBaseInfoDialog", "AddPolicyObjectPickDialog"], list[str]], None]:
    def pick(self, items_to_pick: list[str]) -> None:
        # pylint: disable=protected-access
        with allure.step(f"Select {item_name}s in dialog: {', '.join(items_to_pick)}"):
            getattr(self, selector_name).click()
            self._view.wait_element_visible(item_locator, timeout=3)
            for item_text in items_to_pick:
                suitable_item = get_or_raise(
                    self._view.find_elements(item_locator, timeout=1),
                    lambda element: element.text == item_text,  # pylint: disable=cell-var-from-loop
                )
                suitable_item.click()
            getattr(self, selector_name).click()
            self._view.wait_element_hide(item_locator, timeout=2)
        # pylint: enable=protected-access

    return pick


def prepare_single_pick(
    item_name: str, selector_name: str, item_locator: BaseLocator = _Locators.selector_item
) -> Callable[[Union["AddPolicyBaseInfoDialog", "AddPolicyObjectPickDialog"], str], None]:
    def pick(self, item: list[str]) -> None:
        with allure.step(f"Select {item_name} '{item}' in dialog"):
            getattr(self, selector_name).click()
            # pylint: disable=protected-access
            self._view.wait_element_visible(item_locator, timeout=3)
            suitable_item = get_or_raise(
                self._view.find_elements(item_locator, timeout=1), lambda element: element.text == item
            )
            suitable_item.click()
            self._view.wait_element_hide(item_locator, timeout=2)
            # pylint: enable=protected-access

    return pick


class AddPolicyBaseInfoDialog(AutoChildDialog):
    @autoname
    class Locators(_Locators):
        name = Locator(By.CSS_SELECTOR, "input[name='name']", Descriptor.INPUT | Descriptor.TEXT)
        description = Locator(By.CSS_SELECTOR, "input[name='description']", Descriptor.INPUT | Descriptor.TEXT)
        roles = Locator(By.CSS_SELECTOR, "mat-select[placeholder='Role']", Descriptor.ELEMENT)
        role_item = Locator(
            By.XPATH, "//div[./mat-option//*[@placeholderlabel='Select role']]/mat-option", Descriptor.SERVICE
        )
        users = Locator(By.CSS_SELECTOR, "adwp-input-select[label='User'] adwp-select", Descriptor.ELEMENT)
        groups = Locator(By.CSS_SELECTOR, "adwp-input-select[label='Group'] adwp-select", Descriptor.ELEMENT)
        next = Locator(By.CSS_SELECTOR, "app-rbac-policy-form-step-one~div button.mat-stepper-next", Descriptor.BUTTON)

    pick_role = prepare_single_pick("role", "roles_element", Locators.role_item)
    pick_users = prepare_multiple_pick("user", "users_element")
    pick_groups = prepare_multiple_pick("group", "groups_element")

    def to_next_step(self) -> "AddPolicyObjectPickDialog":
        self.next_button.click()
        return AddPolicyObjectPickDialog.wait_opened(interactor=self._view)


class AddPolicyObjectPickDialog(AutoChildDialog):
    @autoname
    class Locators(_Locators):
        clusters = Locator(By.XPATH, "//div[./span//span[text()='Cluster']]//adwp-select", Descriptor.ELEMENT)
        services = Locator(By.XPATH, "//div[./span//span[text()='Service']]//mat-select", Descriptor.ELEMENT)
        service_item = Locator(By.CSS_SELECTOR, ".mat-select-panel mat-option", Descriptor.SERVICE)
        providers = Locator(By.CSS_SELECTOR, "app-parametrized-by-provider adwp-select", Descriptor.ELEMENT)
        # parent of service when it's suitable
        parent = Locator(By.XPATH, "//div[./span//span[text()='Parent']]//adwp-select", Descriptor.ELEMENT)
        hosts = Locator(By.CSS_SELECTOR, "app-parametrized-by-host mat-form-field", Descriptor.ELEMENT)

        back = Locator(
            By.CSS_SELECTOR, "app-rbac-policy-form-step-two~div button[matstepperprevious]", Descriptor.BUTTON
        )
        next = Locator(By.CSS_SELECTOR, "app-rbac-policy-form-step-two~div .mat-stepper-next", Descriptor.BUTTON)

    _pick_cluster_as_parent = prepare_multiple_pick("cluster", "parent_element")
    _pick_service = prepare_single_pick("service", "services_element", Locators.service_item)
    pick_clusters = prepare_multiple_pick("cluster", "clusters_element")
    pick_providers = prepare_multiple_pick("provider", "providers_element")
    pick_hosts = prepare_multiple_pick("provider", "hosts_element")

    @classmethod
    def wait_opened(cls, driver: WebDriver | None = None, interactor: Interactor | None = None):
        interactor = interactor or Interactor(driver=driver, default_timeout=0.5)
        interactor.wait_element_visible(cls.Locators.body, timeout=5)
        interactor.wait_element_visible(cls.Locators.next, timeout=5)
        return cls(parent_element=interactor.find_element(cls.Locators.body), interactor=interactor)

    def pick_services(self, cluster_name: str, service: str):
        self._pick_service(service)
        self._pick_cluster_as_parent([cluster_name])

    def to_next_step(self) -> "AddPolicyFinishDialog":
        self.next_button.click()
        return AddPolicyFinishDialog.wait_opened(interactor=self._view)


class AddPolicyFinishDialog(AutoChildDialog):
    @autoname
    class Locators(_Locators):
        add = Locator(By.XPATH, "//button[./span[contains(text(), 'Add')]]", Descriptor.BUTTON)

    @classmethod
    def wait_opened(cls, driver: WebDriver | None = None, interactor: Interactor | None = None):
        interactor = interactor or Interactor(driver=driver, default_timeout=0.5)
        interactor.wait_element_visible(cls.Locators.body, timeout=5)
        interactor.wait_element_visible(cls.Locators.add, timeout=5)
        return cls(parent_element=interactor.find_element(cls.Locators.body), interactor=interactor)

    def add(self) -> None:
        self.add_button.click()
        self.wait_closed()
