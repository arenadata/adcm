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

import json
from itertools import chain
from pathlib import Path
from secrets import token_hex
from typing import Tuple, Optional

import adcm.init_django  # pylint: disable=unused-import
from cm.bundle import load_adcm
from cm.config import SECRETS_FILE
from cm.issue import update_hierarchy_issues
from cm.job import abort_all
from cm.logger import logger
from cm.models import (
    CheckLog,
    Cluster,
    ConcernItem,
    ConcernType,
    DummyData,
    GroupCheckLog,
    HostProvider,
)
from cm.status_api import Event
from rbac.models import User


TOKEN_LENGTH = 20


def prepare_secrets_json(st_username: str, st_password: Optional[str]) -> None:
    secrets_exists = Path(SECRETS_FILE).is_file()
    if not secrets_exists and st_password is not None:
        with open(SECRETS_FILE, "w", encoding="utf_8") as f:
            json.dump(
                {
                    "adcmuser": {"user": st_username, "password": st_password},
                    "token": token_hex(TOKEN_LENGTH),
                    "adcm_internal_token": token_hex(TOKEN_LENGTH)
                },
                f
            )
    elif secrets_exists:
        with open(SECRETS_FILE, encoding="utf_8") as f:
            data = json.load(f)
        # write missing token
        if "adcm_internal_token" not in data:
            data["adcm_internal_token"] = token_hex(TOKEN_LENGTH)
            with open(SECRETS_FILE, "w", encoding="utf_8") as f:
                json.dump(data, f)

    logger.info("Update secret file %s OK", SECRETS_FILE)


def create_status_user() -> Tuple[str, Optional[str]]:
    username = "status"
    if User.objects.filter(username=username).exists():
        return username, None

    password = token_hex(TOKEN_LENGTH)
    User.objects.create_superuser(username, "", password, built_in=True)
    return username, password


def create_dummy_data():
    DummyData.objects.create()


def clear_temp_tables():
    CheckLog.objects.all().delete()
    GroupCheckLog.objects.all().delete()


def drop_locks():
    """Drop orphaned locks"""
    ConcernItem.objects.filter(type=ConcernType.Lock).delete()


def recheck_issues():
    """
    Drop old issues and re-check from scratch
    Could slow down startup process
    """
    ConcernItem.objects.filter(type=ConcernType.Issue).delete()
    for model in chain([Cluster, HostProvider]):
        for obj in model.objects.all():
            update_hierarchy_issues(obj)


def init():
    logger.info("Start initializing ADCM DB...")
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin", built_in=True)
    st_username, st_password = create_status_user()
    prepare_secrets_json(st_username, st_password)
    if not User.objects.filter(username="system").exists():
        User.objects.create_superuser("system", "", None, built_in=True)
        logger.info("Create system user")
    event = Event()
    abort_all(event)
    clear_temp_tables()
    event.send_state()
    load_adcm()
    create_dummy_data()
    drop_locks()
    recheck_issues()
    logger.info("ADCM DB is initialized")


if __name__ == "__main__":
    init()
