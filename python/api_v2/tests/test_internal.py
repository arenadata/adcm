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

from secrets import token_hex
from unittest.mock import patch

from adcm.tests.base import ParallelReadyTestCase
from adcm.tests.client import ADCMTestClient
from django.conf import settings
from django.test import TestCase
from rbac.models import User
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN


class TestStatusServerSync(TestCase, ParallelReadyTestCase):
    client: ADCMTestClient
    client_class = ADCMTestClient

    def get_sync_endpoint(self):
        return self.client.v2 / "internal" / "unstable" / "status-server" / "sync"

    def test_authorized_user_call_sync(self):
        username = settings.ADCM_STATUS_USERNAME
        password = token_hex(16)
        User.objects.create_superuser(username=username, password=password)

        self.client.login(username=username, password=password)

        endpoint = self.get_sync_endpoint()
        with patch("api_v2.internal.views.notify.update_all") as mock:
            response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        mock.assert_called_once()

    def test_no_user_call_sync(self):
        endpoint = self.get_sync_endpoint()
        with patch("api_v2.internal.views.notify.update_all") as mock:
            response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        mock.assert_not_called()

    def test_unauthorized_user_call_sync(self):
        username = "admin"
        password = token_hex(16)
        User.objects.create_superuser(username=username, password=password)

        self.client.login(username=username, password=password)

        endpoint = self.get_sync_endpoint()
        with patch("api_v2.internal.views.notify.update_all") as mock:
            response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        mock.assert_not_called()
