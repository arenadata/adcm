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
from core.secrets._types import ADCMSecrets, SecretsFileModel


class SecretsProvider(Protocol):
    def get(self) -> ADCMSecrets:
        ...


class FSSecretsProvider(SecretsProvider):
    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self) -> ADCMSecrets:
        try:
            content = self._path.read_text(encoding="utf-8")
            return SecretsFileModel.model_validate_json(content).adcm

        except FileNotFoundError as e:
            message = f"Secrets file not found: {self._path}"
            raise SecretsError(message) from e

        except (ValidationError, json.JSONDecodeError) as e:
            message = f"File {self._path} can't be parsed as {ADCMSecrets.__class__.__name__}"
            raise SecretsError(message) from e


class OpenBaoSecretsProvider(SecretsProvider):
    def get(self):
        raise NotImplementedError()
