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

import logging

from application.di.providers.environment import EnvironmentProvider
from application.startup.secrets import prepare_secrets_file
from core import secrets
from core.settings import Directories
import dishka


def main():
    container = dishka.make_container(EnvironmentProvider())

    # todo init loggers correctly
    main_logger = logging.getLogger("stream_std")

    secrets_source = container.get(secrets.SecretsSource)
    if secrets_source != secrets.SecretsSource.FILE_SYSTEM:
        return

    directories = container.get(Directories)
    prepare_secrets_file(secrets_directory=directories.secrets, logger=main_logger)


if __name__ == "__main__":
    main()
