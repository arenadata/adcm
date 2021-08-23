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

from dataclasses import dataclass

from selenium.webdriver.common.by import By


@dataclass
class Locator:
    """Describes a locator on a webpage"""

    by: By
    value: str
    name: str


@dataclass
class TemplateLocator(Locator):
    """
    Similar to Locator, but with template in `value`
    and ability to generate Locators from template
    """

    def __call__(self, *args) -> Locator:
        """Get regular Locator by passing arguments to format function"""
        return Locator(by=self.by, value=self.value.format(*args), name=self.name.format(*args))
