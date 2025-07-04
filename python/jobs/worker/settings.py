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

from typing import Generator
import os


def _get_env_variables(*args) -> Generator[str | None, None, None]:
    for arg in args:
        yield os.environ.get(arg.upper())


DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME = _get_env_variables("DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DB_NAME")
_db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

broker_url = f"sqla+{_db_url}"
result_backend = f"db+{_db_url}"
result_extended = True
broker_connection_retry_on_startup = True
timezone = "UTC"
