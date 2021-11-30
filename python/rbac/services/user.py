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

"""Service functions for working with User model"""

from typing import List

from adwp_base.errors import AdwpEx
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.authtoken.models import Token

from rbac import models
from rbac.utils import Empty, set_not_empty_attr

PW_MASK = '*****'


def _set_password(user: models.User, value: str) -> None:
    if value is Empty or value == PW_MASK:
        return

    if not value:
        raise AdwpEx('USER_UPDATE_ERROR', msg='Password could not be empty')

    new_password = make_password(value)
    if user.password == new_password:
        return

    user.set_password(value)
    _regenerate_token(user)


def _update_groups(user: models.User, groups: [Empty, List[dict]]) -> None:
    if groups is Empty:
        return

    user_groups = {g.id: g for g in user.group.all()}
    new_groups = [g['id'] for g in groups]

    for group_id in new_groups:
        if group_id in user_groups:
            continue
        try:
            group = models.Group.objects.get(id=group_id)
        except ObjectDoesNotExist as exc:
            msg = f'Group with ID {group_id} was not found'
            raise AdwpEx(
                'USER_UPDATE_ERROR', msg=msg, http_code=status.HTTP_400_BAD_REQUEST
            ) from exc
        user.group.add(group)
        user_groups[group_id] = group

    for group_id, group in user_groups.items():
        if group_id in new_groups:
            continue
        user.group.remove(group)


def _regenerate_token(user: models.User) -> Token:
    Token.objects.filter(user=user).delete()
    token = Token(user=user)
    token.save()
    return token


@transaction.atomic
def update(
    user: models.User,
    context_user: models.User = None,  # None is for use outside of web context
    *,
    partial: bool = False,
    username: str = Empty,
    first_name: str = Empty,
    last_name: str = Empty,
    email: str = Empty,
    is_superuser: bool = Empty,
    password: str = Empty,
    profile: dict = Empty,
    group: list = Empty,
) -> models.User:
    """Full or partial User update"""
    if (username is not Empty) and (username != user.username):
        raise AdwpEx('USER_UPDATE_ERROR', msg='Username could not be changed')

    args = (username, first_name, last_name, email, is_superuser)
    if not partial and not all((arg is not Empty for arg in args)):
        raise AdwpEx('USER_UPDATE_ERROR', msg='Full User update with partial argset is forbidden')

    set_not_empty_attr(user, partial, 'first_name', first_name, '')
    set_not_empty_attr(user, partial, 'last_name', last_name, '')
    set_not_empty_attr(user, partial, 'email', email, '')
    set_not_empty_attr(user, partial, 'profile', profile, '')
    _set_password(user, password)

    if context_user is None or context_user.is_superuser:
        set_not_empty_attr(user, partial, 'is_superuser', is_superuser, False)
        _update_groups(user, group)
    user.save()
    return user


@transaction.atomic
def create(
    *,
    username: str,
    password: str,
    first_name: str = None,
    last_name: str = None,
    email: str = None,
    is_superuser: bool = None,
    profile: dict = None,
    group: list = None,
) -> models.User:
    """Create User"""
    if is_superuser:
        func = models.User.objects.create_superuser
    else:
        func = models.User.objects.create_user
    try:
        user = func(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            profile=profile,
        )
    except IntegrityError as exc:
        raise AdwpEx('USER_CREATE_ERROR', msg=f'User creation failed with error {exc}') from exc

    _update_groups(user, group or [])
    _regenerate_token(user)
    return user
