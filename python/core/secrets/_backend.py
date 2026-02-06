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

from pathlib import Path
from typing import Protocol
import json

from pydantic import ValidationError

from core.secrets._secrets import SecretsError
from core.secrets._types import ADCMSecrets


class SecretsProvider(Protocol):
    def get(self) -> ADCMSecrets:
        ...


class FSSecretsProvider(SecretsProvider):
    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self) -> ADCMSecrets:
        if not self._path.is_file():
            raise SecretsError(f"Secrets file not found: {self._path}")

        try:
            with self._path.open(mode="r") as f:
                data = json.load(f)
            return ADCMSecrets(**data)
        except (ValidationError, json.JSONDecodeError) as e:
            raise SecretsError(f"File {self._path} can't be parsed as {ADCMSecrets.__class__.__name__}") from e


class OpenBaoSecretsProvider(SecretsProvider):
    def get(self):
        raise NotImplementedError()
