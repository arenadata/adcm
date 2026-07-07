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

from collections.abc import Iterable, Iterator
from hashlib import sha256
from itertools import compress
from typing import Literal

from adcm.permissions import RUN_ACTION_PERM_PREFIX
from cm.legacy.services.action_process.types import ProcessState
from cm.models import (
    Action,
    ADCMEntity,
    Component,
    Process,
)
from core.types import ActionTargetDescriptor
from django.conf import settings
from django.utils import timezone
from rbac.models import User


def get_str_hash(value: str) -> str:
    return sha256(value.encode(settings.ENCODING_UTF_8)).hexdigest()


def get_run_actions_permissions(actions: Iterable[Action]) -> list[str]:
    return [f"{RUN_ACTION_PERM_PREFIX}{get_str_hash(value=action.name)}" for action in actions]


def filter_actions_by_user_perm(user: User, obj: ADCMEntity, actions: Iterable[Action]) -> Iterator[Action]:
    mask = [user.has_perm(perm=perm, obj=obj) for perm in get_run_actions_permissions(actions=actions)]

    return compress(data=actions, selectors=mask)


def has_run_perms(user: User, action: Action, obj: ADCMEntity) -> bool:
    return user.has_perm(perm=f"{RUN_ACTION_PERM_PREFIX}{get_str_hash(value=action.name)}", obj=obj)


def unique_hc_entries(
    hc_create_data: list[dict[Literal["host_id", "component_id"], int]],
) -> list[dict[Literal["host_id", "component_id"], int]]:
    return [
        {"host_id": host_id, "component_id": component_id}
        for host_id, component_id in {(entry["host_id"], entry["component_id"]) for entry in hc_create_data}
    ]


def insert_service_ids(
    hc_create_data: list[dict[Literal["host_id", "component_id"], int]],
) -> list[dict[Literal["host_id", "component_id", "service_id"], int]]:
    component_ids = {single_hc["component_id"] for single_hc in hc_create_data}
    component_service_map = {
        component.pk: component.service_id for component in Component.objects.filter(pk__in=component_ids)
    }

    for single_hc in hc_create_data:
        single_hc["service_id"] = component_service_map[single_hc["component_id"]]

    return hc_create_data


def get_action_processes(action: Action, object_: ActionTargetDescriptor) -> list[Process]:
    # While we are returning one object, the last one is incomplete.
    if (
        process := Process.objects.filter(
            target_id=object_.id,
            target_type=object_.type,
            action=action,
            state=ProcessState.CREATED,
            created_at__gt=timezone.now() - settings.ACTION_PROCESS_STALE_STATE_TIMEOUT,
        )
        .order_by("id")
        .last()
    ):
        return [process]

    return []
