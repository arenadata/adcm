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

from hashlib import sha256
from itertools import compress
from typing import Iterable, Iterator

from cm.models import Action, ADCMEntity
from django.conf import settings
from rbac.models import User

from adcm.permissions import ADD_TASK_PERM, RUN_ACTION_PERM_PREFIX


def get_str_hash(value: str) -> str:
    return sha256(value.encode(settings.ENCODING_UTF_8)).hexdigest()


def get_run_actions_permissions(actions: Iterable[Action]) -> list[str]:
    return [f"{RUN_ACTION_PERM_PREFIX}{get_str_hash(value=action.name)}" for action in actions]


def filter_actions_by_user_perm(user: User, obj: ADCMEntity, actions: Iterable[Action]) -> Iterator[Action]:
    mask = [user.has_perm(perm=perm, obj=obj) for perm in get_run_actions_permissions(actions=actions)]

    return compress(data=actions, selectors=mask)


def check_run_perms(user: User, action: Action, obj: ADCMEntity) -> bool:
    if user.has_perm(perm=ADD_TASK_PERM):
        return True

    return user.has_perm(perm=get_run_actions_permissions(actions=[action])[0], obj=obj)
