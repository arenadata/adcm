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
from secrets import token_hex
import json
import logging

from django.utils import timezone

import adcm.init_django  # noqa: F401, isort:skip

from cm.bundle import load_adcm
from cm.issue import update_hierarchy_issues
from cm.job import abort_all
from cm.models import (
    ADCM,
    CheckLog,
    Cluster,
    ConcernItem,
    ConcernType,
    GroupCheckLog,
    HostProvider,
    JobLog,
    JobStatus,
    TaskLog,
)
from django.conf import settings
from rbac.models import User

TOKEN_LENGTH = 20


logger = logging.getLogger("stream_std")


def prepare_secrets_json(status_user_username: str, status_user_password: str | None) -> None:
    # we need to know status user's password to write it to secrets.json [old implementation]
    if not settings.SECRETS_FILE.is_file() and status_user_username is not None:
        with Path(settings.SECRETS_FILE).open(mode="w", encoding=settings.ENCODING_UTF_8) as f:
            json.dump(
                {
                    "adcmuser": {"user": status_user_username, "password": status_user_password},
                    "token": token_hex(TOKEN_LENGTH),
                    "adcm_internal_token": settings.ADCM_TOKEN,
                },
                f,
            )
        logger.info("Update secret file %s OK", settings.SECRETS_FILE)
    else:
        logger.info("Secret file %s is not updated", settings.SECRETS_FILE)


def create_status_user() -> tuple[str, str | None]:
    username = "status"
    if User.objects.filter(username=username).exists():
        return username, None

    password = token_hex(TOKEN_LENGTH)
    User.objects.create_superuser(username, "", password, built_in=True)
    return username, password


def clear_temp_tables():
    CheckLog.objects.all().delete()
    GroupCheckLog.objects.all().delete()


def drop_locks():
    """Drop orphaned locks"""
    ConcernItem.objects.filter(type=ConcernType.LOCK).delete()


def recheck_issues():
    """
    Drop old issues and re-check from scratch
    Could slow down startup process
    """
    ConcernItem.objects.filter(type=ConcernType.ISSUE).delete()
    for model in [ADCM, Cluster, HostProvider]:
        for obj in model.objects.order_by("id"):
            update_hierarchy_issues(obj)


def abort_all():
    for task in TaskLog.objects.filter(status=JobStatus.RUNNING):
        task.status = JobStatus.ABORTED
        task.finish_date = timezone.now()
        task.save(update_fields=["status", "finish_date"])

        unlock_affected_objects(task=task)

    JobLog.objects.filter(status=JobStatus.RUNNING).update(status=JobStatus.ABORTED, finish_date=timezone.now())


def init(adcm_conf_file: Path = Path(settings.BASE_DIR, "conf", "adcm", "config.yaml")):
    logger.info("Start initializing ADCM DB...")
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin", built_in=True)
    status_user_username, status_user_password = create_status_user()
    prepare_secrets_json(status_user_username, status_user_password)
    if not User.objects.filter(username="system").exists():
        User.objects.create_superuser("system", "", None, built_in=True)
        logger.info("Create system user")
    abort_all()
    clear_temp_tables()
    load_adcm(adcm_conf_file)
    drop_locks()
    recheck_issues()
    logger.info("ADCM DB is initialized")


if __name__ == "__main__":
    init()
