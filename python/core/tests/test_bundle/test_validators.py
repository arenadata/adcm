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

from unittest import TestCase

from core.bundle_alt.errors import BundleValidationError
from core.bundle_alt.types import Definition
from core.bundle_alt.validation import check_display_names_are_unique


class TestCheckDisplayNamesAreUnique(TestCase):
    def test_component_in_different_services_named_as_service(self):
        definitions = {
            ("service", "main"): Definition(type="service", name="main", version="4", display_name="main"),
            ("component", "main", "main"): Definition(type="component", name="main", version="4", display_name="main"),
            ("service", "another"): Definition(type="service", name="another", version="4", display_name="another"),
            ("component", "another", "main"): Definition(
                type="component", name="main", version="4", display_name="main"
            ),
        }

        check_display_names_are_unique(definitions)

    def test_duplicated_display_names_within_one_service(self):
        definitions = {
            ("service", "main"): Definition(type="service", name="main", version="4", display_name="main"),
            ("component", "main", "main"): Definition(type="component", name="main", version="4", display_name="cool"),
            ("component", "main", "another"): Definition(
                type="component", name="another", version="4", display_name="cool"
            ),
        }

        with self.assertRaises(BundleValidationError, msg="Incorrect definition of component 'another'"):
            check_display_names_are_unique(definitions)
