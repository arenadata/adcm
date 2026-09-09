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

from core import secrets
from rbac.models import User
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_405_METHOD_NOT_ALLOWED,
)
from tests.base import WithPreparedFSAndInitADCM
from tests.client import ADCMTestClient
from tests.dependencies import get_status_scenarios_manager
from tests.suites import ADCMDjangoAPISuite
import dishka
import django.test


class TestStatusServerSync(django.test.TestCase, WithPreparedFSAndInitADCM):
    client: ADCMTestClient
    client_class = ADCMTestClient

    def get_sync_endpoint(self):
        return self.client.v2 / "internal" / "unstable" / "status-server" / "sync"

    def setUp(self) -> None:
        get_status_scenarios_manager().reset()

    def test_authorized_user_call_sync(self):
        status_user = User.objects.get(username="status")

        self.client.force_authenticate(status_user)

        endpoint = self.get_sync_endpoint()
        response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_200_OK)
        get_status_scenarios_manager().expect_called_once("update_all")

    def test_no_user_call_sync(self):
        endpoint = self.get_sync_endpoint()
        response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)
        get_status_scenarios_manager().expect_not_called("update_all")

    def test_unauthorized_user_call_sync(self):
        admin_user = User.objects.get(username="admin")

        self.client.force_authenticate(admin_user)

        endpoint = self.get_sync_endpoint()
        response = endpoint.post()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
        get_status_scenarios_manager().expect_not_called("update_all")


class TestStatusServerGetToken(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cls.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = cls.uc.create_user(**cls.test_user_credentials)

    def get_token_endpoint(self):
        return self.client.v2 / "internal" / "unstable" / "status-server" / "get-token"

    def test_superuser_success(self):
        response = self.get_token_endpoint().get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        with self.container(scope=dishka.Scope.REQUEST) as container:
            expected_token = container.get(secrets.StatusCheckerStatusServiceToken)
        self.assertEqual(response.json(), {"token": expected_token})

    def test_regular_user_forbidden(self):
        self.client.login(**self.test_user_credentials)

        response = self.get_token_endpoint().get()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_unauthenticated_forbidden(self):
        self.client.logout()

        response = self.get_token_endpoint().get()

        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)

    def test_post_not_allowed(self):
        response = self.get_token_endpoint().post()

        self.assertEqual(response.status_code, HTTP_405_METHOD_NOT_ALLOWED)
