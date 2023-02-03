from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from tests.library.utils import name_of
from tests.ui_tests.core.elements import (
    Button,
    Element,
    Link,
    ListOfElements,
    as_element,
)
from tests.ui_tests.core.interactors import Interactor
from tests.ui_tests.core.locators import Locator, autoname


class Crumb(Element):
    @autoname
    class Locators:
        actions_button = Locator(By.TAG_NAME, "app-actions-button")
        app_upgrade = Locator(By.TAG_NAME, "app-upgrade")
        concern_mark = Locator(By.XPATH, ".//app-actions-button[app-concern-list-ref]")

    def __init__(self, element: WebElement, interactor: Interactor):
        super().__init__(element=element, interactor=interactor)
        self._link = None

    @property
    def link(self) -> Link:
        if self._link:
            return self._link

        self._link = Link.from_parent(parent=self.element, interactor=self._view)
        return self._link

    @property
    def name(self) -> str:
        return self.link.name

    def has_concern_mark(self) -> bool:
        return self._view.is_child_displayed(self.element, self.Locators.concern_mark, timeout=0.2)

    def has_actions_button(self) -> bool:
        """
        Check if Breadcrumb block has actions button (both with and without concern's exclamation mark)
        """
        return self._view.is_child_displayed(self.element, self.Locators.actions_button, timeout=0.2)

    def has_upgrade_button(self) -> bool:
        return self._view.is_child_displayed(self.element, self.Locators.upgrade_button, timeout=0.2)

    def get_actions_button(self) -> Button:
        assert self.has_actions_button(), f"No action button for crumb {self.name}"
        assert not self.has_concern_mark(), "Action button is hidden behind concern's exclamation mark"

        return Button(element=self._view.find_child(self.element, self.Locators.actions_button), interactor=self._view)

    def get_concern_mark(self) -> Button:
        assert self.has_concern_mark(), f"Concern mark isn't presented on crumb {self.name}"

        return Button(element=self._view.find_child(self.element, self.Locators.concern_mark), interactor=self._view)

    def get_upgrade_button(self) -> Button:
        assert self.has_upgrade_button(), f"Upgrade button isn't presented on crumb {self.name}"

        return Button(element=self._view.find_child(self.element, self.Locators.upgrade_button), interactor=self._view)


class Breadcrumbs(Element):
    @autoname
    class Locators:
        block = Locator(By.TAG_NAME, "app-navigation")
        to_main_page = Locator(By.TAG_NAME, "a")
        crumb = Locator(By.XPATH, "//span[div]")

    def __init__(self, element: WebElement, interactor: Interactor):
        super().__init__(element=element, interactor=interactor)
        self._to_main_page = None
        self._crumbs = None

    @classmethod
    def at_current_page(cls, interactor: Interactor) -> "Breadcrumbs":
        return cls(element=interactor.find_element(cls.Locators.block), interactor=interactor)

    @property
    def to_main_page(self) -> WebElement:
        if self._to_main_page:
            return self._to_main_page

        self._to_main_page = self._view.find_child(self.element, self.Locators.to_main_page)
        return self._to_main_page

    @property
    def crumbs(self) -> ListOfElements[Crumb]:
        if self._crumbs:
            return self._crumbs

        self._crumbs = ListOfElements(
            map(as_element(Crumb, self._view), self._view.find_children(self.element, self.Locators.crumb))
        )
        return self._crumbs

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(map(name_of, self.crumbs))
