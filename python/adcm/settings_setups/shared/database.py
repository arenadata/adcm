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

from application.environment import parse_db_settings_from_env

db_settings = parse_db_settings_from_env()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_settings.name,
        "USER": db_settings.user,
        "PASSWORD": db_settings.password.get_secret_value(),
        "HOST": db_settings.host,
        "PORT": db_settings.port,
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,  # Improves the reliability of connection reuse
        # and prevents errors when the connection was closed by the database server.
        "OPTIONS": db_settings.options,
    }
}
