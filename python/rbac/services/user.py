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

from functools import partial
from operator import attrgetter
from typing import Any, Iterable

from cm.services.adcm import retrieve_password_requirements
from cm.status_api import send_user_update_event
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
from django.db.models import F
from django.db.transaction import atomic, on_commit
from djangorestframework_camel_case.util import camelize
from rest_framework.authtoken.models import Token

from rbac.models import Group, User


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
                id__in=m2m_model.objects.values_list("group_id", flat=True).filter(user_id=user_id)
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


def perform_regular_user_update(user_id: UserID, update_data: UserUpdateDTO) -> UserID:
    # users can't change `is_superuser` flag if is not superuser themselves,
    # so we need to nullify it here
    update_data.is_superuser = None

    return _perform_user_update(user_id=user_id, update_data=update_data, new_password=None, new_user_groups=None)


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

        on_commit(func=partial(send_user_update_event, user_id=user.id, changes=camelize(update_data.dict())))

    return user_id
