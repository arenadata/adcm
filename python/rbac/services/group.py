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

"""Service functions for working with Group model"""
import functools

from cm.errors import raise_adcm_ex
from cm.status_api import send_object_update_event
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.transaction import on_commit

from rbac import models
from rbac.utils import Empty, set_not_empty_attr


def _update_users(group: models.Group, users: [Empty, list[dict]]) -> None:
    if users is Empty:
        return
    if group.type == models.OriginType.LDAP:
        raise_adcm_ex("GROUP_CONFLICT", msg="You can't change users in LDAP group")
    group_users = {u.id: u for u in group.user_set.order_by("id")}
    new_users = [u["id"] for u in users]

    for user_id in new_users:
        if user_id in group_users:
            continue
        try:
            user = models.User.objects.get(id=user_id)
        except ObjectDoesNotExist:
            msg = f"User with ID {user_id} was not found"
            raise_adcm_ex("GROUP_UPDATE_ERROR", msg=msg)
        group.user_set.add(user)
        group_users[user_id] = user

    for user_id, user in group_users.items():
        if user_id in new_users:
            continue
        group.user_set.remove(user)


@transaction.atomic
def create(
    *,
    name_to_display: str,
    description: str = "",
    user_set: list[dict] = None,
) -> models.Group:
    """Create Group"""
    try:
        group = models.Group.objects.create(name=name_to_display, description=description)
    except IntegrityError as e:
        raise_adcm_ex("GROUP_CREATE_ERROR", msg=f"Group creation failed with error {e}")
    _update_users(group, user_set or [])
    return group


@transaction.atomic
def update(
    group: models.Group,
    *,
    partial: bool = False,
    name_to_display: str = Empty,
    description: str = Empty,
    user_set: list[dict] = Empty,
) -> models.Group:
    """Full or partial Group object update"""
    if group.type == models.OriginType.LDAP:
        raise_adcm_ex("GROUP_CONFLICT", msg="You cannot change LDAP type group")
    set_not_empty_attr(group, partial, "name", name_to_display)
    set_not_empty_attr(group, partial, "description", description, "")
    try:
        group.save()
    except IntegrityError as e:
        raise_adcm_ex("GROUP_CONFLICT", msg=f"Group update failed with error {e}")
    _update_users(group, user_set)
    on_commit(
        func=functools.partial(
            send_object_update_event,
            object_=group,
            changes={
                "displayName": name_to_display,
                "description": description,
                "users": [u.pk for u in group.user_set.all()],
            },
        )
    )
    return group
