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

from json import JSONDecodeError
from typing import Generator
import os
import json


def _get_env_variables(*args) -> Generator[str | None, None, None]:
    for arg in args:
        yield os.environ.get(arg.upper())


def get_db_options() -> str:
    db_options = os.getenv("DB_OPTIONS", "{}")
    try:
        parsed = json.loads(db_options)
    except JSONDecodeError as json_error:
        raise RuntimeError("Failed to decode DB_OPTIONS as JSON") from json_error
    if not isinstance(parsed, dict):
        raise RuntimeError("DB_OPTIONS should be dict")  # noqa: TRY004

    return "&".join((f"{key}={value}" for key, value in parsed.items()))


DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME = _get_env_variables("DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DB_NAME")
db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
if _options := get_db_options():
    db_url = f"{db_url}?{_options}"

########################
# Celery Worker settings
########################

broker_url = f"sqla+{db_url}"
result_backend = f"db+{db_url}"
result_extended = True
broker_connection_retry_on_startup = True
timezone = "UTC"
