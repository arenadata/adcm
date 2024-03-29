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


from cm.errors import AdcmEx
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from rbac.models import Group, OriginType, User
from rbac.utils import Empty, set_not_empty_attr
from rest_framework.authtoken.models import Token

from api.rbac.validators import ADCMLengthPasswordValidator


def _set_password(user: User, value: str) -> None:
    if not value:
        raise AdcmEx(code="USER_UPDATE_ERROR", msg="Password could not be empty")

    if value is Empty or user.check_password(value):
        return

    user.set_password(value)
    _regenerate_token(user)


def _update_groups(user: User, groups: [Empty, list[dict]]) -> None:
    if groups is Empty:
        return

    user_groups = {g.id: g.group for g in user.groups.order_by("id")}
    new_groups = [g["id"] for g in groups]

    for group_id in new_groups:
        if group_id in user_groups:
            continue

        try:
            group = Group.objects.get(id=group_id)
        except ObjectDoesNotExist as e:
            msg = f"Group with ID {group_id} was not found"
            raise AdcmEx(code="USER_UPDATE_ERROR", msg=msg) from e

        if group and group.type == OriginType.LDAP:
            raise AdcmEx(code="USER_CONFLICT", msg="You cannot add user to LDAP group")

        user.groups.add(group)
        user_groups[group_id] = group

    for group_id, group in user_groups.items():
        if group_id in new_groups:
            continue

        if group.type == OriginType.LDAP:
            raise AdcmEx(code="USER_CONFLICT", msg="You cannot remove user from original LDAP group")

        user.groups.remove(group)


def _regenerate_token(user: User) -> Token:
    Token.objects.filter(user=user).delete()
    token = Token(user=user)
    token.save()

    return token


@transaction.atomic
def update_user(
    user: User,
    context_user: User = None,  # None is for use outside of web context
    *,
    partial: bool = False,
    need_current_password: bool = True,
    username: str = Empty,
    first_name: str = Empty,
    last_name: str = Empty,
    email: str = Empty,
    is_superuser: bool = Empty,
    password: str = Empty,
    current_password: str = Empty,
    profile: dict = Empty,
    groups: list = Empty,
    is_active: bool = Empty,
) -> User:
    if (username is not Empty) and (username != user.username):
        raise AdcmEx(code="USER_CONFLICT", msg="Username could not be changed")

    args = (username, first_name, last_name, email, is_superuser, is_active)
    if not partial and not all(arg is not Empty for arg in args):
        raise AdcmEx(code="USER_UPDATE_ERROR", msg="Full User update with partial argset is forbidden")

    user_exist = User.objects.filter(email=email).exists()
    if user_exist and (email != ""):
        email_user = User.objects.get(email=email)
        if email_user != user:
            raise AdcmEx(code="USER_CONFLICT", msg="User with the same email already exist")

    names = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "is_active": is_active,
    }
    if user.type == OriginType.LDAP and any(
        (value is not Empty and getattr(user, key) != value) for key, value in names.items()
    ):
        raise AdcmEx(code="USER_CONFLICT", msg='You can change only "profile" for LDAP type user')

    is_password_changing = password is not Empty and not user.check_password(raw_password=password)
    if is_password_changing:
        if need_current_password and (
            current_password is Empty or not user.check_password(raw_password=current_password)
        ):
            raise AdcmEx(code="USER_PASSWORD_CURRENT_PASSWORD_REQUIRED_ERROR")

        validate_password(
            password=password,
            password_validators=[ADCMLengthPasswordValidator()],
        )

    set_not_empty_attr(user, partial, "first_name", first_name, "")
    set_not_empty_attr(user, partial, "last_name", last_name, "")
    set_not_empty_attr(user, partial, "email", email, "")
    set_not_empty_attr(user, partial, "profile", profile, "")
    set_not_empty_attr(user, partial, "is_active", is_active, True)
    _set_password(user, password)

    if context_user is None or context_user.is_superuser:
        set_not_empty_attr(user, partial, "is_superuser", is_superuser, False)
        _update_groups(user, groups)

    user.save()

    return user


@transaction.atomic
def create_user(
    *,
    username: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    is_superuser: bool = False,
    profile: str = "",
    groups: list = None,
    is_active: bool = True,
) -> User:
    func = User.objects.create_superuser if is_superuser else User.objects.create_user

    user_exist = User.objects.filter(email=email).exists()
    if user_exist and (email != ""):
        raise AdcmEx(code="USER_CREATE_ERROR", msg="User with the same email already exist")

    validate_password(
        password=password,
        password_validators=[ADCMLengthPasswordValidator()],
    )

    user = None
    try:
        user = func(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            profile=profile,
            is_active=is_active,
        )
    except IntegrityError as e:
        raise AdcmEx(code="USER_CREATE_ERROR", msg=f"User creation failed with error {e}") from e

    if not User:
        raise AdcmEx(code="USER_CREATE_ERROR", msg="User creation failed")

    _update_groups(user, groups or [])
    _regenerate_token(user)

    return user
