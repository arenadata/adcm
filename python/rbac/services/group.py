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

from typing import List

from adwp_base.errors import AdwpEx
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from rest_framework import status

from rbac import models
from rbac.utils import Empty, set_not_empty_attr


def _update_users(group: models.Group, users: [Empty, List[dict]]) -> None:
    if users is Empty:
        return
    if group.type == models.OriginType.LDAP:
        raise AdwpEx('GROUP_UPDATE_ERROR', msg="You can\'t change users in LDAP group")
    group_users = {u.id: u for u in group.user_set.all()}
    new_users = [u['id'] for u in users]

    for user_id in new_users:
        if user_id in group_users:
            continue
        try:
            user = models.User.objects.get(id=user_id)
        except ObjectDoesNotExist as exc:
            msg = f'User with ID {user_id} was not found'
            raise AdwpEx(
                'GROUP_UPDATE_ERROR', msg=msg, http_code=status.HTTP_400_BAD_REQUEST
            ) from exc
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
    description: str = None,
    user_set: List[dict] = None,
) -> models.Group:
    """Create Group"""
    try:
        group = models.Group.objects.create(name=name_to_display, description=description)
    except IntegrityError as exc:
        raise AdwpEx('GROUP_CREATE_ERROR', msg=f'Group creation failed with error {exc}') from exc
    _update_users(group, user_set or [])
    return group


@transaction.atomic
def update(
    group: models.Group,
    *,
    partial: bool = False,
    name_to_display: str = Empty,
    description: str = Empty,
    user_set: List[dict] = Empty,
) -> models.Group:
    """Full or partial Group object update"""
    if group.type == models.OriginType.LDAP:
        raise AdwpEx('GROUP_UPDATE_ERROR', msg='You cannot change LDAP type group')
    set_not_empty_attr(group, partial, 'name', name_to_display)
    set_not_empty_attr(group, partial, 'description', description, '')
    try:
        group.save()
    except IntegrityError as exc:
        raise AdwpEx('GROUP_UPDATE_ERROR', msg=f'Group update failed with error {exc}') from exc
    _update_users(group, user_set)
    return group
