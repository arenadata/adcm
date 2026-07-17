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
from pathlib import Path
import os
import json

from pydantic import BaseModel, ConfigDict, ValidationError

from core.ext_utils.pydantic import (
    represent_missing_and_others_errors_without_description,
)
from core.result import Fail, Success
from core.secrets import (
    ADCMSecrets,
    RetrieveError,
    Secret,
    SecretsBackend,
    SourceError,
    get_secret_from_adcm_secrets,
)


class SecretsFileModel(BaseModel):
    """
    Represents structure of secrets file on FS (with extra nesting level)
    """

    adcm: ADCMSecrets

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(slots=True)
class FSSecretsBackend(SecretsBackend):
    path: Path

    _secrets: ADCMSecrets | None = None

    def write_all(self, secrets: ADCMSecrets) -> None:
        secrets_as_json = SecretsFileModel(adcm=secrets).model_dump_json()
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode=0o600)
        with os.fdopen(fd, "w") as file:
            file.write(secrets_as_json)
        self.path.chmod(0o600)
        self._secrets = None

    def read_all(
        self,
    ) -> Success[ADCMSecrets] | Fail[tuple[dict[Secret, str], dict[Secret, RetrieveError]]] | Fail[SourceError]:
        if self._secrets:
            return Success(self._secrets)

        try:
            content = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            error = RetrieveError(f"No file {self.path}")
            return Fail(({}, {s: error for s in Secret}))
        except OSError as e:
            message = f"Failed to read secrets at {self.path}: {e}"
            return Fail(SourceError(message))
        except json.JSONDecodeError as e:
            message = f"Failed to parse secrets as json at {self.path}: {e}"
            return Fail(SourceError(message))

        try:
            validated = SecretsFileModel.model_validate_json(content)
        except ValidationError as e:
            message = represent_missing_and_others_errors_without_description(
                errors=e.errors(),
                prefix="Secrets file content format is unexpected (file system)",
                blocks_separator="\n",
            )
            return Fail(SourceError(message))

        self._secrets = validated.adcm

        return Success(self._secrets)

    def read(self, secret: Secret) -> str:
        result = self.read_all()
        match result:
            case Success(adcm_secrets):
                return get_secret_from_adcm_secrets(secret_to_find=secret, adcm_secrets=adcm_secrets)

            case Fail((discovered, missing)):
                if secret in discovered:
                    # impossible in first implementation
                    return discovered[secret]

                # it is expected that each secret is either in discovered or missing
                raise missing[secret]

            case Fail(SourceError()):
                raise result.value
