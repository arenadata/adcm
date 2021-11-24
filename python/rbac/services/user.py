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

from typing import Any, List

from adwp_base.errors import AdwpEx
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token

from rbac import models, log

PASSWORD_MASK = '*****'


class _Empty:
    """Same as None but useful when None is valid value"""

    def __bool__(self):
        return False


def _set_not_empty_attr(obj, partial: bool, attr: str, value: Any, default: Any = None) -> None:
    if partial:
        if value is not _Empty:
            setattr(obj, attr, value)
    else:
        value = value if value is not _Empty else default
        setattr(obj, attr, value)


def _set_password(user: AbstractUser, value: str) -> None:
    if value is _Empty or value == PASSWORD_MASK:
        return

    if not value:
        raise AdwpEx('USER_UPDATE_ERROR', msg='Password could not be empty')

    new_password = make_password(value)
    if user.password == new_password:
        return

    user.set_password(value)
    _regenerate_token(user)


def _update_profile(user: AbstractUser, profile_data: Any) -> None:
    if profile_data is _Empty:
        return
    profile, _ = models.UserProfile.objects.get_or_create(user=user)
    profile.profile = profile_data if profile_data is not None else ''
    profile.save()


def _update_groups(user: AbstractUser, groups: [_Empty, List[dict]]) -> None:
    if groups is _Empty:
        return

    user_groups = {g.id: g for g in user.groups.all()}
    new_groups = [g['id'] for g in groups]

    for group_id in new_groups:
        if group_id in user_groups:
            continue
        try:
            group = models.Group.objects.get(id=group_id)
        except ObjectDoesNotExist:
            log.error('Attempt to add user %s to non-existing group %s', user, group_id)
            continue
        user.groups.add(group)
        user_groups[group_id] = group

    for group_id, group in user_groups.items():
        if group_id in new_groups:
            continue
        user.groups.remove(group)


def _regenerate_token(user: AbstractUser) -> Token:
    Token.objects.filter(user=user).delete()
    token = Token(user=user)
    token.save()
    return token


@transaction.atomic
def update(
    user: AbstractUser,
    *,
    partial: bool = False,
    username: str = _Empty,
    first_name: str = _Empty,
    last_name: str = _Empty,
    email: str = _Empty,
    is_superuser: bool = _Empty,
    password: str = _Empty,
    profile: dict = _Empty,
    groups: list = _Empty,
) -> AbstractUser:
    if (partial and username is not _Empty) or (not partial and username != user.username):
        raise AdwpEx('USER_UPDATE_ERROR', msg='Username could not be changed')

    _set_not_empty_attr(user, partial, 'first_name', first_name, '')
    _set_not_empty_attr(user, partial, 'last_name', last_name, '')
    _set_not_empty_attr(user, partial, 'email', email, '')
    _set_not_empty_attr(user, partial, 'is_superuser', is_superuser, False)
    _set_password(user, password)
    _update_profile(user, profile)
    _update_groups(user, groups)
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
    groups: list = None,
) -> AbstractUser:
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
        )
    except IntegrityError as exc:
        raise AdwpEx('USER_CREATE_ERROR', msg=f'User creation failed with error {exc}') from exc

    _update_groups(user, groups or [])
    _update_profile(user, profile)
    _regenerate_token(user)
    return user
