from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from tests.ui_tests.core.elements import Element, as_element
from tests.ui_tests.core.interactors import Interactor
from tests.ui_tests.core.locators import Locator, autoname


class MenuTab(Element):
    @autoname
    class Locators:
        name = Locator(By.TAG_NAME, "span")
        concern_mark = Locator(By.TAG_NAME, "mat-icon")

    _CHOSEN_GREEN = (0, 230, 118)

    def __init__(self, element: WebElement, interactor: Interactor):
        super().__init__(element=element, interactor=interactor)
        self._name = None

    @property
    def name(self) -> str:
        if self._name:
            return self._name

        self._name = self._view.find_child(self.element, self.Locators.name).text.strip()
        return self._name

    def has_concern_mark(self) -> bool:
        return self._view.is_child_displayed(self.element, self.Locators.concern_mark, timeout=0.1)

    def is_chosen(self) -> bool:
        name_element = self._view.find_child(self.element, self.Locators.name, timeout=0.1)
        rgba_string = name_element.value_of_css_property("color")
        rgb = tuple(map(int, rgba_string[:-1].split("(", maxsplit=1)[-1].split(",")[:3]))
        return rgb == self._CHOSEN_GREEN


class LeftMenu(Element):
    @autoname
    class Locators:
        block = Locator(By.TAG_NAME, "app-left-menu")
        tab = Locator(By.TAG_NAME, "a")

    def __init__(self, element: WebElement, interactor: Interactor):
        super().__init__(element=element, interactor=interactor)
        self._tabs = None

    @classmethod
    def at_current_page(cls, interactor: Interactor) -> "LeftMenu":
        return cls(element=interactor.find_element(cls.Locators.block), interactor=interactor)

    @property
    def tabs(self) -> tuple[MenuTab]:
        if self._tabs:
            return self._tabs

        self._tabs = tuple(
            map(as_element(MenuTab, self._view), self._view.find_children(self.element, self.Locators.tab))
        )
        return self._tabs

    def __getitem__(self, item: str) -> MenuTab:
        for tab in self.tabs:
            if tab.name == item:
                return tab

        raise IndexError(f"No such menu: {item}")
