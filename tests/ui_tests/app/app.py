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

# Created by a1wen at 27.02.19

# pylint: disable=E0401, E0611, W0611, W0621
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW
from tests.library import steps
from tests.ui_tests.app.pages import Ui, ClustersList
from tests.ui_tests.app.helpers import urls


class ADCMTest:

    def __init__(self, adcm):
        self.opts = Options()
        self.opts.headless = True
        self.opts.add_argument('--no-sandbox')
        self.opts.add_argument('--disable-dev-shm-usage')
        self.opts.add_argument('--disable-extensions')
        self.opts.add_argument('--ignore-certificate-errors')
        self.opts.add_argument('--disable-gpu')
        self.opts.add_argument("--start-maximized")
        self.capabilities = webdriver.DesiredCapabilities.CHROME.copy()
        self.capabilities['acceptSslCerts'] = True
        self.capabilities['acceptInsecureCerts'] = True
        self.driver = webdriver.Chrome(options=self.opts, desired_capabilities=self.capabilities)
        self.driver.set_window_size(1800, 1000)
        self.driver.implicitly_wait(0.5)
        self.adcm = adcm
        self._client = adcm.api.objects
        self.ui = Ui(self.driver)

    def navigate_to(self, page: urls):
        self.driver.get(page)
        # return ?Page()

    def clusters_page(self):
        return ClustersList(self)

    def create_cluster(self):
        return steps.create_cluster(self._client)['name']

    def create_host(self, fqdn):
        steps.create_host_w_default_provider(self._client, fqdn)
        return fqdn

    def create_provider(self):
        return steps.create_hostprovider(self._client)['name']

    def wait_for(self, condition: EC, locator: tuple, timer=5):
        def get_element(el):
            return WDW(self.driver, timer).until(condition(el))
        return get_element(locator)

    def wait_element_present(self, locator: tuple):
        return self.wait_for(EC.presence_of_element_located, locator)

    def contains_url(self, url: str, timer=5):
        return WDW(self.driver, timer).until(EC.url_contains(url))

    def base_page(self):
        self.driver.get(self.adcm.url)

    def destroy(self):
        self.driver.quit()
