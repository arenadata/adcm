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
from operator import attrgetter
from typing import Any, Iterable

from cm.errors import AdcmEx
from cm.services.adcm import retrieve_password_requirements
from core.errors import NotFoundError
from core.rbac.dto import UserCreateDTO, UserUpdateDTO
from core.rbac.errors import UpdateLDAPUserError
from core.rbac.operations import (
    add_user_to_groups,
    block_users,
    create_new_user,
    remove_user_from_groups,
    unblock_users,
    update_user_information,
    update_user_password,
)
from core.rbac.types import GroupBasicInfo, GroupID, SourceType, UserBasicInfo, UserID
from core.types import ShortObjectInfo
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.transaction import atomic
from rest_framework.authtoken.models import Token

from rbac.models import Group, OriginType, User
from rbac.utils import Empty, set_not_empty_attr
from rbac.validators import ADCMLengthPasswordValidator


class UserDB:
    @staticmethod
    def get_users_info(ids: Iterable[UserID]) -> Iterable[UserBasicInfo]:
        return (
            UserBasicInfo(
                id=user["id"],
                built_in=user["built_in"],
                type=SourceType(user["type"]),
                is_superuser=user["is_superuser"],
            )
            for user in User.objects.values("id", "built_in", "type", "is_superuser").filter(id__in=ids)
        )

    @staticmethod
    def get_user_by_username(username: str) -> ShortObjectInfo | None:
        user = User.objects.values("id", name=F("username")).filter(username=username).first()
        if not user:
            return user

        return ShortObjectInfo(**user)

    @staticmethod
    def get_user_by_email(email: str) -> ShortObjectInfo | None:
        user = User.objects.values("id", name=F("username")).filter(email=email).first()
        if not user:
            return user

        return ShortObjectInfo(**user)

    @staticmethod
    def create_user(data: UserCreateDTO) -> UserID:
        return User.objects.create_user(**data.dict()).pk

    @staticmethod
    def update_user(user_id: UserID, **fields: Any) -> UserID:
        if not fields:
            return user_id

        User.objects.filter(id=user_id).update(**fields)

        return user_id

    @staticmethod
    def set_password(user_id: UserID, password: str) -> UserID:
        user = User.objects.get(id=user_id)
        user.set_password(password)
        user.save(update_fields=["password"])
        return user_id

    @staticmethod
    def remove_login_attempts_block(user_ids: Iterable[UserID]) -> None:
        User.objects.filter(id__in=user_ids).update(failed_login_attempts=0, blocked_at=None)

    @staticmethod
    def activate_users(user_ids: Iterable[UserID]) -> None:
        User.objects.filter(id__in=user_ids).update(is_active=True)

    @staticmethod
    def deactivate_users(user_ids: Iterable[UserID]) -> None:
        User.objects.filter(id__in=user_ids).update(is_active=False)


class GroupDB:
    @staticmethod
    def get_groups_info(ids: Iterable[GroupID]) -> Iterable[GroupBasicInfo]:
        return (
            GroupBasicInfo(id=group["id"], built_in=group["built_in"], type=SourceType(group["type"]))
            for group in Group.objects.values("id", "built_in", "type").filter(id__in=ids)
        )

    @staticmethod
    def add_user_to_groups(user_id: UserID, groups: Iterable[GroupID]) -> None:
        m2m_model = Group.user_set.through
        records = tuple(m2m_model(user_id=user_id, group_id=group_id) for group_id in groups)
        m2m_model.objects.bulk_create(records)

    @staticmethod
    def remove_user_from_groups(user_id: UserID, groups: Iterable[GroupID]) -> None:
        m2m_model = Group.user_set.through
        m2m_model.objects.filter(user_id=user_id, group_id__in=groups).delete()

    @staticmethod
    def get_user_groups(user_id: UserID) -> Iterable[GroupBasicInfo]:
        m2m_model = Group.user_set.through
        return (
            GroupBasicInfo(id=group["id"], built_in=group["built_in"], type=SourceType(group["type"]))
            for group in Group.objects.values("id", "built_in", "type").filter(
                id__in=m2m_model.objects.values_list("id", flat=True).filter(user_id=user_id)
            )
        )


def drop_user_connections(user_ids: Iterable[UserID]) -> None:
    # sessions will expire "by default" Django mechanism
    Token.objects.filter(user_id__in=user_ids).delete()


def perform_user_creation(create_data: UserCreateDTO, groups: Iterable[GroupID]) -> UserID:
    password_requirements = retrieve_password_requirements()

    with atomic():
        user_id = create_new_user(
            data=create_data,
            db=UserDB,
            password_requirements=password_requirements,
        )
        if groups:
            add_user_to_groups(user_id=user_id, groups=groups, db=GroupDB)

    return user_id


def perform_user_update_as_superuser(
    user_id: UserID, update_data: UserUpdateDTO, new_password: str | None, new_user_groups: set[GroupID] | None
):
    return _perform_user_update(
        user_id=user_id, update_data=update_data, new_password=new_password, new_user_groups=new_user_groups
    )


def perform_regular_user_update(user_id: UserID, update_data: UserUpdateDTO, new_password: str | None) -> UserID:
    # users can't change `is_superuser` flag if is not superuser themselves,
    # so we need to nullify it here
    update_data.is_superuser = None

    return _perform_user_update(
        user_id=user_id, update_data=update_data, new_password=new_password, new_user_groups=None
    )


def perform_users_block(users: Iterable[UserID]) -> Iterable[UserID]:
    user_ids = tuple(users)

    with atomic():
        block_users(users=user_ids, db=UserDB)
        drop_user_connections(user_ids=user_ids)

    return user_ids


def perform_users_unblock(users: Iterable[UserID]) -> Iterable[UserID]:
    user_ids = tuple(users)

    with atomic():
        unblock_users(users=user_ids, db=UserDB)

    return user_ids


def _perform_user_update(
    user_id: UserID, update_data: UserUpdateDTO, new_password: str | None, new_user_groups: set[GroupID] | None
) -> UserID:
    users = tuple(UserDB.get_users_info(ids=[user_id]))
    if not users:
        raise NotFoundError("User not found")

    user, *_ = users
    if user.type == SourceType.LDAP:
        raise UpdateLDAPUserError()

    with atomic():
        update_user_information(user_id=user_id, data=update_data, db=UserDB)

        if isinstance(new_password, str):
            update_user_password(
                user_id=user_id,
                new_password=new_password,
                db=UserDB,
                password_requirements=retrieve_password_requirements(),
            )
            drop_user_connections(user_ids=[user_id])

        if new_user_groups is not None:
            current_groups = set(map(attrgetter("id"), GroupDB.get_user_groups(user_id=user_id)))
            add_user_to_groups(user_id=user_id, groups=new_user_groups - current_groups, db=GroupDB)
            remove_user_from_groups(user_id=user_id, groups=current_groups - new_user_groups, db=GroupDB)

    return user_id


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
