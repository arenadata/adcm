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

from typing import TypeVar

from core.ext_utils.pydantic import represent_missing_and_others_errors_without_description
from pydantic_settings import BaseSettings, SettingsError
import pydantic

_EnvSettingsT = TypeVar("_EnvSettingsT", bound=BaseSettings)


class SettingsReadError(Exception):
    ...


def parse_settings_from_env(settings_cls: type[_EnvSettingsT], name: str) -> _EnvSettingsT:
    prefix = f"Failed to retrieve {name} settings from environment.\nSummary:\n"
    try:
        return settings_cls()
    except pydantic.ValidationError as e:
        message = represent_missing_and_others_errors_without_description(
            errors=e.errors(),
            prefix=prefix,
        )
        raise SettingsReadError(message) from None
    except SettingsError as e:
        raise SettingsReadError(f"{prefix}{e}") from e
