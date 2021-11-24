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

from http import HTTPStatus
from uuid import uuid4

from django.test import Client, TestCase

from rbac import models


class UserEndpoints(TestCase):
    """Tests for rbac.endpoints.user module"""

    def setUp(self) -> None:
        password = 'P@ssw0rd'
        self.admin = models.User.objects.create_superuser(
            username=f'admin_{uuid4().hex}', email='admin@test.com', password=password
        )
        self.user = models.User.objects.create_user(
            username=f'user_{uuid4().hex}', email='user@test.com', password=password
        )
        self.admin_client = Client()
        self.admin_client.post(
            '/api/v1/auth/login/', {'username': self.admin.username, 'password': password}
        )
        self.user_client = Client()
        self.user_client.post(
            '/api/v1/auth/login/', {'username': self.user.username, 'password': password}
        )

    def test_admin_get_user_list(self):
        response = self.admin_client.get('/api/v1/rbac/user/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        self.assertIn('results', data)
        usernames = [r['username'] for r in data['results']]
        self.assertIn(self.admin.username, usernames)
        self.assertIn(self.user.username, usernames)

    def test_user_forbidden_get(self):
        response = self.user_client.get('/api/v1/rbac/user/')
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
