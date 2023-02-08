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
# pylint: disable=wrong-import-order

import datetime
import os
import sqlite3

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor

import adcm.init_django  # pylint: disable=unused-import
from cm.logger import logger


def check_migrations():
    try:
        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
    except ImproperlyConfigured:
        # No databases are configured (or the dummy one)
        return False
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        return True
    return False


def backup_sqlite(dbfile):
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backupfile = os.path.join(settings.BASE_DIR, "data", "var", f"{now_str}.db")
    old = sqlite3.connect(dbfile)
    new = sqlite3.connect(backupfile)
    with new:
        old.backup(new)

    new.close()
    old.close()
    logger.info("Backup sqlite db to %s", backupfile)


def backup_db():
    if not check_migrations():
        return

    db = settings.DATABASES["default"]
    if db["ENGINE"] != "django.db.backends.sqlite3":
        logger.error("Backup for %s not implemented yet", db["ENGINE"])

        return

    backup_sqlite(db["NAME"])


if __name__ == "__main__":
    backup_db()
