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

from core.tools import convert_keys_to_camel_case


class TestConvertKeysToCamelCase(TestCase):
    def test_nested_dicts_and_lists(self) -> None:
        source = {
            "is_blocking": True,
            "cause": None,
            "reason": {
                "placeholder": [
                    {"cluster_id": 1, "service_id": 2},
                ]
            },
        }

        result = convert_keys_to_camel_case(value=source)

        self.assertEqual(
            result,
            {
                "isBlocking": True,
                "cause": None,
                "reason": {
                    "placeholder": [
                        {"clusterId": 1, "serviceId": 2},
                    ]
                },
            },
        )
