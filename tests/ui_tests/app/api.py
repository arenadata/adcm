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
import json
import allure
import requests


class RequestFailedException(Exception):
    """Request to ADCM API has status code >= 400"""


class ADCMDirectAPIClient:
    """Helper to make requests to ADCM API in a browser-like way"""

    def __init__(self, base_url: str, user_credentials: dict):
        self.base_url = base_url.rstrip("/")
        self.credentials = user_credentials
        self.login_endpoint = f'{base_url}/api/v1/token/'
        self.user_create_endpoint = f'{base_url}/api/v1/user/'
        self.user_delete_ep_template = f'{base_url}/api/v1/user/' + '{}/'
        self.password_endpoint = f'{base_url}/api/v1/profile/admin/password/'

    @allure.step('Get authorization token over API')
    def get_authorization_token(self) -> str:
        """Returns authorization token for current user"""
        response = requests.post(self.login_endpoint, json=self.credentials)
        self._check_response(response)
        return response.json()['token']

    def get_authorization_header(self) -> dict:
        """Returns "Authorization" header with token for current user"""
        token = self.get_authorization_token()
        return {'Authorization': f'Token {token}'}

    @allure.step('Create new user over API')
    def create_new_user(self, credentials: dict) -> None:
        """Creates new user"""
        self._make_authorized_request('post', self.user_create_endpoint, json=credentials)

    @allure.step('Delete user {username} over API')
    def delete_user(self, username: str) -> None:
        """Deletes user by name"""
        self._make_authorized_request('delete', self.user_delete_ep_template.format(username))

    def _make_authorized_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        request_function = getattr(requests, method)
        response = request_function(endpoint, headers=self.get_authorization_header(), **kwargs)
        self._check_response(response)
        return response

    @staticmethod
    def _check_response(response: requests.Response):
        if (status_code := response.status_code) < 400:
            return
        try:
            response_content = response.json()
        except json.JSONDecodeError:
            response_content = response.text
        raise RequestFailedException(
            f'Request finished with status {status_code} ' f'and json body: {response_content}',
        )
