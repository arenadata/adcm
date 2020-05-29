from tests.ui_tests.app.configuration import Configuration
from tests.ui_tests.app.pages import Details, ListPage
from tests.ui_tests.app.locators import Service


class ServiceDetails(Details, ListPage):
    @property
    def main_tab(self):
        self._getelement(Service.main_tab).click()
        return ListPage(self.driver)

    @property
    def configuration_tab(self):
        self._getelement(Service.configuration_tab).click()
        return Configuration(self.driver)

    @property
    def status_tab(self):
        self._getelement(Service.status_tab).click()
        return ListPage(self.driver)

    def click_main_tab(self):
        return self._click_tab("Main")

    def click_configuration_tab(self):
        return self._click_tab("Configuration")
