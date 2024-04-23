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

from adcm.tests.base import BaseTestCase
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK


class TestSchema(BaseTestCase):
    def test_swagger_available(self):
        response = self.client.get(path=reverse(viewname="v2:swagger-ui"))

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.get(path=reverse(viewname="v2:schema"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn("openapi", response.data)
