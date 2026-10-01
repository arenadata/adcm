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

"""
Plain, DI-free readers of process environment/filesystem layout.

Kept separate from `application.di.providers.environment` so callers that
need these values before a DI container exists (or without one at all) can
get them directly, instead of only through `container.get(...)`.
"""

from functools import cache
from pathlib import Path
from typing import Annotated
import os

from core.settings import Directories
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from application.constants import DEFAULT_DB_PORT
from application.utils import parse_settings_from_env


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="db_")

    user: str
    # prefix looks to be ignored when alias is used
    password: Annotated[SecretStr, Field(alias="db_pass")]
    name: str
    host: str
    port: str = DEFAULT_DB_PORT

    options: Annotated[dict, Field(default_factory=dict)]


@cache
def parse_db_settings_from_env() -> DBSettings:
    return parse_settings_from_env(settings_cls=DBSettings, name="database")


@cache
def directories_from_env() -> Directories:
    base_dir = Path(os.getenv("ADCM_BASE_DIR", Path(__file__).absolute().parent.parent.parent))
    stack_dir = Path(os.getenv("ADCM_STACK_DIR", base_dir))

    base_data_dir = base_dir / "data"
    # feels wrong to have both base dir and stack dir to have "data",
    # yet it's out there for a long time
    stack_data_dir = stack_dir / "data"

    return Directories(
        base=base_dir,
        stack=stack_dir,
        files=stack_data_dir / "file",
        bundles=stack_data_dir / "bundle",
        downloads=stack_data_dir / "download",
        secrets=base_data_dir / "var",
        code=base_dir / "python",
        data=base_data_dir,
        run=base_data_dir / "run",
        logs=base_data_dir / "log",
        temp=base_data_dir / "tmp",
    )
