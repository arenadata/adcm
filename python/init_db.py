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
import logging.config

from dishka import make_container
from django.db.models import Q
import dishka

import adcm.init_django  # noqa: F401, isort:skip

from application.di.containers import get_main_providers
from application.loggers import startup_logging_config_from_env
from cm.legacy.issue import update_hierarchy_issues
from cm.models import (
    ADCM,
    CheckLog,
    Cluster,
    ConcernItem,
    ConcernType,
    GroupCheckLog,
    Provider,
    TaskLog,
)
from core.action import UNFINISHED_STATUSES, ExecutionStatus, TaskRunnerEnvironment
from core.files.directories import ADCMBundleDir
from core.secrets import Secret, SecretsBackend
from rbac.models import User
from rest_framework.authtoken.models import Token
from use_cases import bundle

TOKEN_LENGTH = 20


logger = logging.getLogger("startup.flow")


def _create_admin_user() -> None:
    username = "admin"
    email = f"{username}@example.com"

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=username, built_in=False)


def _create_status_user() -> int:
    username = "status"
    email = f"{username}@example.com"

    status_user = User.objects.filter(username=username).only("email").first()
    if status_user is not None:
        update_fields = []
        if status_user.email != email:
            status_user.email = email
            update_fields.append("email")
        if status_user.is_superuser:
            status_user.is_superuser = False
            update_fields.append("is_superuser")
        if update_fields:
            status_user.save(update_fields=update_fields)

        return status_user.pk

    user = User.objects.create_user(username=username, email=email, password=token_hex(TOKEN_LENGTH), built_in=True)
    return user.pk


def _create_system_user() -> None:
    username = "system"
    email = f"{username}@example.com"

    system_user = User.objects.filter(username=username).only("email").first()
    if system_user is None:
        User.objects.create_user(username=username, email=email, password=None, is_active=False, built_in=True)
        return
    update_fields = []
    if system_user.email != email:
        system_user.email = email
        update_fields.append("email")
    if system_user.is_active:
        system_user.is_active = False
        update_fields.append("is_active")
    if update_fields:
        system_user.save(update_fields=update_fields)


def _ensure_status_user_token_set(user_id: int, token: str) -> None:
    Token.objects.filter(user_id=user_id).delete()
    Token.objects.create(user_id=user_id, key=token)


def clear_temp_tables():
    CheckLog.objects.all().delete()
    GroupCheckLog.objects.all().delete()


def set_local_tasks_to_broken():
    TaskLog.objects.filter(executor__environment=TaskRunnerEnvironment.LOCAL, status__in=UNFINISHED_STATUSES).update(
        status=ExecutionStatus.BROKEN
    )


def remove_orphan_and_local_locks():
    ConcernItem.objects.filter(
        Q(type=ConcernType.LOCK)
        & (Q(tasklog__isnull=True) | Q(tasklog__executor__environment=TaskRunnerEnvironment.LOCAL))
    ).delete()


def recheck_issues():
    """
    Drop old issues and re-check from scratch
    Could slow down startup process
    """
    ConcernItem.objects.filter(type=ConcernType.ISSUE).delete()
    for model in [ADCM, Cluster, Provider]:
        for obj in model.objects.order_by("id"):
            update_hierarchy_issues(obj)


def init(container: dishka.Container, adcm_conf_file: Path | None = None):
    logger.info("Start initializing ADCM DB...")

    _create_admin_user()
    _create_system_user()
    user_id = _create_status_user()
    secrets_backend = container.get(SecretsBackend)
    status_user_token = secrets_backend.read(Secret.STATUS_SERVICE_ADCM_TOKEN)
    _ensure_status_user_token_set(user_id=user_id, token=status_user_token)

    set_local_tasks_to_broken()
    remove_orphan_and_local_locks()
    clear_temp_tables()

    adcm_conf_file = adcm_conf_file.parent if adcm_conf_file else container.get(ADCMBundleDir)

    container.get(bundle.InitOrUpgradeADCM).do(alternative_adcm_dir=adcm_conf_file)

    recheck_issues()

    logger.info("ADCM DB is initialized")


if __name__ == "__main__":
    container = make_container(*get_main_providers())

    logging.config.dictConfig(startup_logging_config_from_env())

    init(container=container)
