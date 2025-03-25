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
import os
import json
import logging

from django.utils import timezone

import adcm.init_django  # noqa: F401, isort:skip

from adcm.feature_flags import use_new_bundle_parsing_approach
from cm.bundle import load_adcm
from cm.issue import update_hierarchy_issues
from cm.models import (
    ADCM,
    UNFINISHED_STATUS,
    CheckLog,
    Cluster,
    ConcernItem,
    ConcernType,
    GroupCheckLog,
    JobLog,
    JobStatus,
    Provider,
    TaskLog,
)
from cm.services.bundle_alt.adcm import process_adcm_bundle
from cm.services.concern.locks import delete_task_flag_concern, delete_task_lock_concern
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


def _create_admin_user() -> None:
    username = "admin"
    email = f"{username}@example.com"

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=username, built_in=False)


def _create_status_user() -> tuple[str, str | None]:
    username = "status"
    email = f"{username}@example.com"

    status_user = User.objects.filter(username=username).only("email").first()
    if status_user is not None:
        if status_user.email != email:
            status_user.email = email
            status_user.save(update_fields=["email"])

        return username, None

    password = token_hex(TOKEN_LENGTH)
    User.objects.create_superuser(username=username, email=email, password=password, built_in=True)

    return username, password


def _create_system_user() -> None:
    username = "system"
    email = f"{username}@example.com"

    system_user = User.objects.filter(username=username).only("email").first()
    if system_user is None:
        User.objects.create_superuser(username=username, email=email, password=None, built_in=True)
    elif system_user.email != email:
        system_user.email = email
        system_user.save(update_fields=["email"])


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
    for model in [ADCM, Cluster, Provider]:
        for obj in model.objects.order_by("id"):
            update_hierarchy_issues(obj)


def abort_all():
    for task in TaskLog.objects.filter(status__in=UNFINISHED_STATUS):
        task.status = JobStatus.ABORTED
        task.finish_date = timezone.now()
        task.save(update_fields=["status", "finish_date"])

        if task.is_blocking:
            delete_task_lock_concern(task_id=task.pk)
        else:
            delete_task_flag_concern(task_id=task.pk)

    JobLog.objects.filter(status__in=UNFINISHED_STATUS).update(status=JobStatus.ABORTED, finish_date=timezone.now())


def init(adcm_conf_file: Path = Path(settings.BASE_DIR, "conf", "adcm", "config.yaml")):
    logger.info("Start initializing ADCM DB...")

    _create_admin_user()
    status_user_username, status_user_password = _create_status_user()
    prepare_secrets_json(status_user_username, status_user_password)
    _create_system_user()

    abort_all()
    clear_temp_tables()

    adcm_parser = process_adcm_bundle if use_new_bundle_parsing_approach(env=os.environ, headers={}) else load_adcm
    adcm_parser(adcm_conf_file)

    drop_locks()
    recheck_issues()
    logger.info("ADCM DB is initialized")


if __name__ == "__main__":
    init()
