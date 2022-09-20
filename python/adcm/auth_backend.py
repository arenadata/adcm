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

from django.conf import settings
from social_core.backends.oauth import BaseOAuth2


class YandexOAuth2(BaseOAuth2):
    name = "yandex"
    AUTHORIZATION_URL = settings.YANDEX_OAUTH_AUTH_URL
    ACCESS_TOKEN_URL = settings.YANDEX_OAUTH_TOKEN_URL
    ACCESS_TOKEN_METHOD = "POST"
    STATE_PARAMETER = False
    REDIRECT_STATE = False

    def auth_html(self):
        pass

    def get_user_details(self, response: dict) -> dict:
        return {
            "username": response.get("login"),
            "email": response.get("emails")[0],
            "first_name": response.get("first_name"),
            "last_name": response.get("last_name"),
        }

    def user_data(self, access_token: str, *args, **kwargs) -> dict:
        return self.get_json(
            url=settings.YANDEX_OAUTH_USER_DATA_URL,
            headers={"Authorization": f"OAuth {access_token}"},
        )
