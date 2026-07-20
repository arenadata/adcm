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

from dataclasses import dataclass
from typing import Annotated

from integrations.consul import ConsulBackend
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvDBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="db_")

    user: str
    # prefix looks to be ignored when alias is used
    password: Annotated[SecretStr, Field(alias="db_pass")]
    name: str
    host: str
    port: str

    options: Annotated[dict, Field(default_factory=dict)]


@dataclass(slots=True)
class CelerySettings:
    # Connections
    db_url: str
    broker_url: str
    result_backend: str
    consul: ConsulBackend | None

    # ADCM specifics
    default_adcm_url: str | None
    status_service_base_path: str

    # Various
    result_extended: bool = True
    broker_connection_retry_on_startup: bool = True
    timezone: str = "UTC"
