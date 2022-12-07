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

"""Tools for ADCM UI over selenium interactions"""

# Created by a1wen at 27.02.19

import os
from typing import Optional, Union

import allure
from adcm_client.wrappers.docker import ADCM
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ChromeOptions, FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW


class ADCMTest:
    """Wrapper class for ADCM UI interactions using Selenium"""

    __slots__ = ("opts", "capabilities", "driver", "ui", "adcm", "selenoid")

    def __init__(self, browser="Chrome", downloads: Optional[Union[os.PathLike, str]] = None):
        self.opts = FirefoxOptions() if browser == "Firefox" else ChromeOptions()
        self.opts.headless = True
        self.opts.add_argument("--no-sandbox")
        self.opts.add_argument("--disable-extensions")
        self.opts.add_argument("--ignore-certificate-errors")
        self.opts.add_argument("--disable-gpu")
        self.opts.add_argument("--start-maximized")
        self.opts.add_argument("--enable-logging")
        self.opts.add_argument("--enable-automation")
        if browser == "Chrome":
            self.opts.add_argument("--window-size=1366,768")
        else:
            self.opts.add_argument("--width=1366")
            self.opts.add_argument("--height=768")
        self.capabilities = self.opts.capabilities.copy()
        self.capabilities["acceptSslCerts"] = True
        self.capabilities["acceptInsecureCerts"] = True
        self.capabilities["goog:loggingPrefs"] = {"browser": "ALL", "performance": "ALL"}
        self.selenoid = {
            "host": os.environ.get("SELENOID_HOST"),
            "port": os.environ.get("SELENOID_PORT", "4444"),
        }
        self._configure_downloads(browser, downloads)
        self.driver = None
        self.adcm = None

    @allure.step("Init driver")
    def create_driver(self):
        """Init selenium driver based on the object properties"""
        if self.selenoid["host"]:
            self.driver = webdriver.Remote(
                command_executor=f"http://{self.selenoid['host']}:{self.selenoid['port']}/wd/hub",
                options=self.opts,
                desired_capabilities=self.capabilities,
            )
        else:
            self.driver = (
                webdriver.Firefox(options=self.opts, desired_capabilities=self.capabilities)
                if self.capabilities["browserName"] == "firefox"
                else webdriver.Chrome(options=self.opts, desired_capabilities=self.capabilities)
            )
        self.driver.implicitly_wait(1)

    @allure.step("Attache ADCM")
    def attache_adcm(self, adcm: ADCM):
        """Attache ADCM instance to the driver wrapper"""
        self.adcm = adcm

    def wait_for(self, condition: EC, locator: tuple, timer=5):
        """Wait for condition"""

        def _get_element(element):
            return WDW(self.driver, timer).until(condition(element))

        return _get_element(locator)

    @allure.step("Wait for element displayed")
    def wait_element_present(self, locator: tuple):
        """Wait for element displayed"""
        return self.wait_for(EC.presence_of_element_located, locator)

    @allure.step("Wait for adress string to contain: {url}")
    def contains_url(self, url: str, timer=5):
        """Wait for adress string to contain given URL"""
        return WDW(self.driver, timer).until(EC.url_contains(url))

    @allure.step("Open a new tab")
    def new_tab(self):
        """Open a new tab"""
        self.driver.execute_script("window.open('');")
        # close all tabs
        for tab in self.driver.window_handles[:-1]:
            self.driver.switch_to.window(tab)
            self.driver.close()
        # set focus to the newly created window
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.delete_all_cookies()
        try:
            self.driver.execute_script("window.localStorage.clear();")
        except WebDriverException:
            # we skip JS error here since we have no simple way to detect localStorage availability
            pass

    @allure.step("Destroy selenium driver")
    def destroy(self):
        """Destroy selenium driver"""
        self.driver.quit()

    def _configure_downloads(self, browser: str, downloads_directory: Optional[Union[os.PathLike, str]]):
        if downloads_directory is None:
            return
        if browser == "Chrome":
            self.opts.add_experimental_option(
                "prefs",
                {"download.default_directory": str(downloads_directory)},
            )
        else:
            if not self.selenoid['host']:
                # do not use default download directory
                self.opts.set_preference("browser.download.folderList", 2)
                self.opts.set_preference("browser.download.dir", str(downloads_directory))
            # allow documents to be saved without asking what to do
            self.opts.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/plain")
