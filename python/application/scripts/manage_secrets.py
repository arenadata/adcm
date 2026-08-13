#!/usr/bin/env python3
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
import sys
import argparse
import logging.config

from application.constants import SECRETS_FILENAME, SECRETS_FILENAME_DEPRECATED
from application.di.providers.environment import EnvironmentProvider
from application.loggers import startup_logging_config_from_env
from application.startup.secrets import (
    check_all_secrets_are_avialable,
    initialize_secrets,
    load_secrets,
    migrate_secrets_on_fs_if_required,
)
from application.types import ADCMMaintenanceMode
from core.result import Fail, Success
from core.secrets import SecretsBackend
from core.settings import Directories
from integrations.vault import ClientSettings
import dishka

message_logger = logging.getLogger("startup.message")


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command", choices=("check", "init", "migrate", "load"), help="Secrets management operation to perform"
    )

    parser.add_argument(
        "--force", action="store_true", default=False, help="Overwrite secrets in target backend (init, load)"
    )
    parser.add_argument("--file", default=None, type=Path, help="Use this file to take secrets from (load)")

    return parser


def configure_output() -> None:
    logging_configuration = startup_logging_config_from_env()
    logging.config.dictConfig(logging_configuration)


def main(args: argparse.Namespace):
    container = dishka.make_container(EnvironmentProvider())

    match args.command:
        case "check":
            backend = container.get(SecretsBackend)
            result = check_all_secrets_are_avialable(backend=backend)

        case "init":
            adcm_maintenance_mode = container.get(ADCMMaintenanceMode)
            directories = container.get(Directories)
            target_backend = container.get(SecretsBackend)
            result = initialize_secrets(
                old_file=directories.secrets / SECRETS_FILENAME_DEPRECATED,
                new_file=directories.secrets / SECRETS_FILENAME,
                target_backend=target_backend,
                adcm_maintenance_mode=adcm_maintenance_mode,
                overwrite_if_exist=args.force,
            )

        case "migrate":
            directories = container.get(Directories)
            result = migrate_secrets_on_fs_if_required(
                source_file=directories.secrets / SECRETS_FILENAME_DEPRECATED,
                target_file=directories.secrets / SECRETS_FILENAME,
            )

        case "load":
            if args.file:
                source_file = Path(args.file)
            else:
                directories = container.get(Directories)
                source_file = directories.secrets / SECRETS_FILENAME

            adcm_maintenance_mode = container.get(ADCMMaintenanceMode)
            vault_settings = container.get(ClientSettings)

            result = load_secrets(
                source_file=source_file,
                vault_settings=vault_settings,
                overwrite_if_exist=args.force,
                adcm_maintenance_mode=adcm_maintenance_mode,
            )

        case unknown_command:
            message = f"Unknown command: {unknown_command}"
            raise RuntimeError(message)

    match result:
        case Success(message):
            message_logger.info(message)
            exit_code = 0

        case Fail(value=str(reason)):
            message_logger.error(reason)
            exit_code = 1

        case Fail(value=(message, err)):
            message_logger.error(message, exc_info=err)
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    argparser = build_argparser()
    arguments = argparser.parse_args()
    configure_output()
    main(arguments)
