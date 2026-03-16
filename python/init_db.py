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
import logging

from dishka import make_container
import dishka

import adcm.init_django  # noqa: F401, isort:skip

from adcm.feature_flags import use_new_job_scheduler
from application.di.containers import get_main_providers
from cm.legacy.issue import update_hierarchy_issues
from cm.models import (
    ADCM,
    CheckLog,
    Cluster,
    ConcernItem,
    ConcernType,
    GroupCheckLog,
    Provider,
)
from core.secrets import Secret, SecretsBackend
from core.settings import Directories
from jobs.scheduler.recover import recover_statuses
from rbac.models import User
from rest_framework.authtoken.models import Token
from use_cases import bundle

TOKEN_LENGTH = 20


logger = logging.getLogger("stream_std")


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
        if status_user.email != email:
            status_user.email = email
            status_user.save(update_fields=["email"])

        return status_user.pk

    user = User.objects.create_superuser(
        username=username, email=email, password=token_hex(TOKEN_LENGTH), built_in=True
    )
    return user.pk


def _create_system_user() -> None:
    username = "system"
    email = f"{username}@example.com"

    system_user = User.objects.filter(username=username).only("email").first()
    if system_user is None:
        User.objects.create_superuser(username=username, email=email, password=None, built_in=True)
    elif system_user.email != email:
        system_user.email = email
        system_user.save(update_fields=["email"])


def _ensure_status_user_token_set(user_id: int, token: str) -> None:
    Token.objects.filter(user_id=user_id).delete()
    Token.objects.create(user_id=user_id, key=token)


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


def init(container: dishka.Container, adcm_conf_file: Path | None = None):
    logger.info("Start initializing ADCM DB...")

    _create_admin_user()
    _create_system_user()
    user_id = _create_status_user()
    secrets_backend = container.get(SecretsBackend)
    status_user_token = secrets_backend.read(Secret.STATUS_SERVICE_ADCM_TOKEN)
    _ensure_status_user_token_set(user_id=user_id, token=status_user_token)

    recover_statuses()
    clear_temp_tables()

    # maybe should be encapsulated in DI too
    adcm_conf_file = adcm_conf_file or container.get(Directories).code.parent / "conf" / "adcm" / "config.yaml"

    container.get(bundle.InitOrUpgradeADCM).do(alternative_adcm_dir=adcm_conf_file.parent)

    if not use_new_job_scheduler():
        drop_locks()
    recheck_issues()

    logger.info("ADCM DB is initialized")


if __name__ == "__main__":
    container = make_container(*get_main_providers())

    init(container=container)
