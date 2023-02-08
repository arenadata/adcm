from operator import contains, eq
from typing import Generator

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from tests.library.utils import name_of
from tests.ui_tests.core.elements import Button, Link, ListOfElements, as_element
from tests.ui_tests.core.interactors import Interactor
from tests.ui_tests.core.locators import Locator, autoname


class Concern:
    _link = Locator(By.TAG_NAME, "a")

    def __init__(self, element: WebElement, interactor: Interactor):
        self.element = element
        self._view = interactor
        self.name = self.element.text
        self._links = None

    @property
    def links(self) -> ListOfElements[Link]:
        if self._links:
            return self._links

        self._links = ListOfElements(
            map(as_element(Link, self._view), self._view.find_children(self.element, self._link))
        )
        return self._links

    def click(self) -> None:
        """Click on first suitable link"""
        link = next(iter(self.links), None)
        assert link, f"At least one link expected for concern {self.name}"

        with allure.step(f"Click on link {link.name}"):
            link.click()


class ListOfConcerns(ListOfElements):
    @property
    def names(self) -> Generator[str, None, None]:
        return map(name_of, self.data)

    def with_link(self, link_name: str, *, exact: bool = True) -> "ListOfConcerns":
        test_ = eq if exact else contains
        return ListOfConcerns(
            filter(lambda concern: any(test_(link.name, link_name) for link in concern.links), self.data)
        )

    def with_text(self, text: str, *, exact: bool = False) -> "ListOfConcerns":
        test_ = eq if exact else contains
        return ListOfConcerns(filter(lambda concern: test_(concern.name, text), self.data))


class ConcernPopover:
    @autoname
    class Locators:
        block = Locator(By.TAG_NAME, "app-popover")
        concern = Locator(By.TAG_NAME, "app-concern")

    def __init__(self, element: WebElement, interactor: Interactor):
        self.element = element
        self._view = interactor
        self._concerns: ListOfConcerns | None = None

    @classmethod
    def wait_opened(cls, interactor: Interactor) -> "ConcernPopover":
        element = interactor.wait_element_visible(cls.Locators.block, timeout=2)
        return cls(element=element, interactor=interactor)

    @property
    def concerns(self) -> ListOfConcerns:
        if self._concerns:
            return self._concerns

        self._concerns = ListOfConcerns(
            map(as_element(Concern, self._view), self._view.find_children(self.element, self.Locators.concern))
        )
        return self._concerns

    def get_concern_links(self) -> tuple[str, ...]:
        return tuple(concern.links[0].element.get_attribute("href") for concern in self.concerns)


class ConcernMark(Button):
    def hover(self) -> ConcernPopover:
        super().hover()
        return ConcernPopover.wait_opened(self._view)
