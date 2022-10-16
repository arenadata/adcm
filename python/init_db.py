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
import random
import string
from itertools import chain

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


def random_string(strlen=10):
    return "".join([random.choice(string.ascii_letters) for _ in range(strlen)])


def create_status_user():
    username = "status"
    if User.objects.filter(username=username).exists():
        return

    password = random_string(40)
    User.objects.create_superuser(username, "", password, built_in=True)
    with open(SECRETS_FILE, "w", encoding="utf_8") as f:
        json.dump(
            {
                "adcmuser": {"user": username, "password": password},
                "token": random_string(40),
                "adcm_internal_token": random_string(40)
            },
            f
        )
    logger.info("Update secret file %s OK", SECRETS_FILE)


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
    create_status_user()
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
