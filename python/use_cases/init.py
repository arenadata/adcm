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
import json
import logging

from core import secrets
from core.settings import Directories
from django.conf import settings

logger = logging.getLogger("stream_std")


@dataclass(slots=True)
class RunPreMigration:
    secrets_source: secrets.SecretsSource
    directories: Directories

    def do(self) -> None:
        # place for all work that needs to be done before django migrations. See run_pre_migration.py

        if self.secrets_source == secrets.SecretsSource.FS:
            self._create_or_migrate_fs_secrets()

    def _create_or_migrate_fs_secrets(self) -> None:
        deprecated_secrets_file = self.directories.vars / secrets.FILENAME_DEPRECATED
        secrets_file = self.directories.vars / secrets.FILENAME

        if secrets_file.is_file():
            logger.info(f"FS secrets: OK ({secrets_file})")
            return

        if deprecated_secrets_file.is_file():
            secrets.migrate_format(
                old_path=deprecated_secrets_file, new_path=secrets_file, django_secret_key=settings.SECRET_KEY
            )
            deprecated_secrets_file.unlink()
            logger.info(f"FS secrets: migrated ({deprecated_secrets_file} -> {secrets_file})")
        else:
            self._write_fs_secrets(path=secrets_file, data=secrets.new())
            logger.info(f"FS secrets: created ({secrets_file})")

    @staticmethod
    def _write_fs_secrets(path: Path, data: dict) -> None:
        with path.open(mode="w") as f:
            json.dump(data, f)
