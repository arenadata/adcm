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

from cm.services.authorization import get_google_oauth, get_yandex_oauth
from social_core.backends.google import GoogleOAuth2
from social_core.backends.yandex import YandexOAuth2


class CustomYandexOAuth2(YandexOAuth2):
    def auth_html(self):
        pass  # not necessary

    def get_key_and_secret(self) -> tuple[str, str]:
        return get_yandex_oauth()


class CustomGoogleOAuth2(GoogleOAuth2):
    def auth_html(self):
        pass  # not necessary

    def get_key_and_secret(self) -> tuple[str, str]:
        return get_google_oauth()
