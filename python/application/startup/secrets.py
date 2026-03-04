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
from secrets import token_hex
from traceback import format_exception
from typing import Annotated, Iterable, Literal
import os

from core import secrets
from core.files.secrets_provider import FSSecretsBackend
from core.result import Fail, Success
from integrations.vault import ClientSettings, VaultSecretsBackend
from pydantic import BaseModel, StringConstraints

from application.types import MigrationMode

_SECRET_TOKEN_LENGTH = 20

# check


def check_all_secrets_are_avialable(
    *, backend: secrets.SecretsBackend
) -> Success[str] | Fail[str] | Fail[tuple[str, secrets.SourceError]]:
    result = backend.read_all()
    match result:
        case Success():
            return Success("Secrets check passed.")

        case Fail((_, missing_secrets)):
            missing_secrets = _format_missing_secrets(missing_secrets)
            message = f"Some secrets are missing:\n{missing_secrets}"
            return Fail(message)

        case Fail(secrets.SourceError()):
            message = "Source backend is unavailable."
            return Fail((message, result.value))


# initialize


def initialize_secrets(
    *,
    old_file: Path,
    new_file: Path,
    target_backend: secrets.SecretsBackend,
    overwrite_if_exist: bool,
    migration_mode: MigrationMode,
) -> Success[str] | Fail[str]:
    if migration_mode == MigrationMode.ENABLED:
        return Fail("Initialization of secrets disallowed: migration mode is enabled.")

    new_file_is_present = new_file.is_file()

    if old_file.is_file() and not new_file_is_present:
        message = "\n".join(
            (
                "Initialization of secrets disallowed."
                f"Old secrets file exists ({old_file}) while new one doesn't ({new_file})."
                "You should run this script with `migrate` first even if you are using Vault Backend.",
            )
        )
        return Fail(message)

    result = target_backend.read_all()

    match result:
        case Fail(secrets.SourceError()):
            # state of secrets on backend is unknown, can't proceed
            message = "\n".join(
                (
                    "Initialization of secrets failed.",
                    "Problem when working with secret backend's source.",
                    "".join(format_exception(result.value)),
                )
            )
            return Fail(message)

    if not overwrite_if_exist:
        match result:
            case Success():
                return Success("Secrets initialization skipped: all secrets exist.")

            case Fail((found_secrets, missing_secrets)) if found_secrets:
                missing_secrets = _format_missing_secrets(missing_secrets)
                message = "\n".join(
                    (
                        "Initialization of secrets failed.",
                        "Can't proceed due to secrets partial initialization.",
                        "You can remove all secrets, fill missing ones or allow overwrite.",
                        "Missing secrets:",
                        missing_secrets,
                        "Proceed with caution.",
                    )
                )
                return Fail(message)

            case Fail(({}, _)) if new_file_is_present:
                # note that case when secrets not found, but new file is absent is correct case
                # AND if force override is allowed, this check is no use

                # most likely non-fs secrets unmigrated
                message = "\n".join(
                    "Initialization of secrets failed."
                    f"Secrets are absent in backend thou secrets file exists on filesystem ({new_file})."
                    "You need to migrate secrets to your backend with `load` command."
                )
                return Fail(message)

    from django.core.management.utils import get_random_secret_key

    django_secret_key = get_random_secret_key()

    new_secrets = secrets.ADCMSecrets(
        ansible=secrets.AnsibleSecrets(ansible_vault=token_hex(_SECRET_TOKEN_LENGTH)),
        django=secrets.DjangoSecrets(secret_key=django_secret_key),
        backend=secrets.BackendSecrets(status_service_token=token_hex(_SECRET_TOKEN_LENGTH)),
        status_service=secrets.StatusServiceSecrets(adcm_token=token_hex(_SECRET_TOKEN_LENGTH)),
        status_checker=secrets.StatusCheckerSecrets(status_service_token=token_hex(_SECRET_TOKEN_LENGTH)),
    )

    target_backend.write_all(new_secrets)

    return Success("Secrets initialized")


# migrate

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]


@dataclass(slots=True, frozen=True)
class _DeprecatedUserField:
    user: Literal["status"]
    password: NonEmptyStr


class _ADCMSecretsDeprecated(BaseModel):
    adcmuser: _DeprecatedUserField
    token: NonEmptyStr
    adcm_internal_token: NonEmptyStr


def migrate_secrets_on_fs_if_required(*, source_file: Path, target_file: Path) -> Success[str]:
    if target_file.is_file():
        return Success(f"Secrets migration skipped: target file exists: {target_file}.")

    if not source_file.is_file():
        return Success(f"Secrets migration skipped: source file does not exist: {source_file}.")

    # migration required
    old_secrets_content = source_file.read_text(encoding="utf-8")
    old_data = _ADCMSecretsDeprecated.model_validate_json(old_secrets_content)

    # django settings are unavailable here, using same code to retrieve/generate it
    from django.core.management.utils import get_random_secret_key

    django_secret_key = os.getenv("SECRET_KEY", get_random_secret_key())

    status_service_token = token_hex(_SECRET_TOKEN_LENGTH)

    migrated_secrets = secrets.ADCMSecrets(
        ansible=secrets.AnsibleSecrets(ansible_vault=old_data.adcmuser.password),
        django=secrets.DjangoSecrets(secret_key=django_secret_key),
        backend=secrets.BackendSecrets(status_service_token=status_service_token),
        status_service=secrets.StatusServiceSecrets(adcm_token=old_data.adcm_internal_token),
        status_checker=secrets.StatusCheckerSecrets(status_service_token=old_data.token),
    )

    fs_backend = FSSecretsBackend(path=target_file)
    fs_backend.write_all(migrated_secrets)

    return Success(f"Secrets migrated: {source_file} -> {target_file}")


# load


def load_secrets(
    *, source_file: Path, vault_settings: ClientSettings, overwrite_if_exist: bool, migration_mode: MigrationMode
) -> Success[str] | Fail[str]:
    if migration_mode != MigrationMode.ENABLED:
        return Fail("Secrets load disallowed: migration mode must be enabled.")

    source_backend = FSSecretsBackend(path=source_file)

    target_backend = VaultSecretsBackend.from_settings(vault_settings)

    result = target_backend.read_all()
    match result:
        case Fail(secrets.SourceError()):
            # state of secrets on backend is unknown, can't proceed
            message = "\n".join(
                (
                    "Secrets load failed.",
                    "Problem when working with target secret backend's source.",
                    "".join(format_exception(result.value)),
                )
            )
            return Fail(message)

        case Success() if not overwrite_if_exist:
            return Fail("Can't proceed, because all secrets exist.")

        case Fail((_, _)) if not overwrite_if_exist:
            message = "\n".join(
                (
                    "Secrets load failed.",
                    "Can't proceed due to secrets partial initialization.",
                    "You can remove all secrets or allow overwrite.",
                    "Proceed with caution.",
                )
            )
            return Fail(message)

    result = source_backend.read_all()

    match result:
        case Success(known_secrets):
            target_backend.write_all(known_secrets)
            return Success("Secrets were loaded")

        case Fail(secrets.SourceError()):
            # state of secrets on backend is unknown, can't proceed
            message = "\n".join(
                (
                    "Secrets load failed.",
                    "Problem when working with source secret backend's source.",
                    "".join(format_exception(result.value)),
                )
            )
            return Fail(message)

        case Fail((_, missing_secrets)):
            missing_secrets = _format_missing_secrets(missing_secrets)
            message = "\n".join(
                (
                    "Secrets load failed.",
                    "Can't proceed due to secrets partial initialization.",
                    "Missing secrets:",
                    missing_secrets,
                )
            )
            return Fail(message)


def _format_missing_secrets(missing_secrets: Iterable[secrets.Secret]) -> str:
    return "\n".join(f"- {'/'.join(secret.value.path)}" for secret in missing_secrets)
