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

from traceback import format_exception
from typing import Iterable, Pattern
import os
import sys

os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']}:/adcm/python/"
sys.path.append("/adcm/python/")

import adcm.init_django  # noqa: F401 # isort:skip

from django.db.models import Q
from django.db.transaction import atomic
from rbac.models import Group, OriginType, User
from rbac.services.ldap import LDAPQuery, LDAPSettings, get_connection, get_ldap_settings
from rbac.services.ldap.errors import LDAPDataError
from rbac.services.ldap.types import DistinguishedName, LDAPAttributes, LDAPGroup, LDAPUser, LDAPUserAttrs
from rbac.services.ldap.utils import str_join_attr_list
from rbac.utils import get_group_name_display_name

UNIQUE_FIELDS = {User.__name__: (("username",),), Group.__name__: (("display_name", "type"), ("name",))}


def _process_groups(groups: Iterable[LDAPGroup], group_name_attribute: str) -> dict[str, str]:
    sys.stdout.write(f"Synchronizing groups...{os.linesep}")

    dn_adcm_name_map: dict[str, str] = {}
    for group_dn, group_attrs in groups:
        dn_adcm_name_map[group_dn.lower()] = str_join_attr_list(
            ldap_attributes=group_attrs, target_attr=group_name_attribute
        )

    ldap_groups_qs = Group.objects.filter(type=OriginType.LDAP)
    existing_groups = ldap_groups_qs.filter(display_name__in=dn_adcm_name_map.values()).values("id", "display_name")

    to_delete_groups = ldap_groups_qs.exclude(id__in=(group["id"] for group in existing_groups))
    if to_delete_groups.exists():
        deleted_group_names = os.linesep.join(
            f" - {name}" for name in to_delete_groups.values_list("display_name", flat=True)
        )
        to_delete_groups.delete()
        sys.stdout.write(f"Groups deleted:{os.linesep}{deleted_group_names}{os.linesep}")

    created = []
    errors = []
    for adcm_group_name in set(dn_adcm_name_map.values()).difference(
        {group["display_name"] for group in existing_groups}
    ):
        name, display_name = get_group_name_display_name(name=adcm_group_name, type_=OriginType.LDAP.value)
        kwargs_get = {
            "name": name,
            "display_name": display_name,
            "type": OriginType.LDAP.value,
            "built_in": False,
        }
        group, _ = _safe_get_or_create(model=Group, kwargs_get=kwargs_get)
        if group is not None:
            created.append(f" - {adcm_group_name}")
        else:
            errors.append(f" - {adcm_group_name}")

    if created:
        sys.stdout.write(f"Create group(s):{os.linesep}{os.linesep.join(created)}{os.linesep}")

    if errors:
        sys.stderr.write(f"Error synchronizing group(s):{os.linesep}{os.linesep.join(errors)}{os.linesep}")

    sys.stdout.write(f"Groups synchronization finished{os.linesep}")

    return dn_adcm_name_map


def _process_users(users: Iterable[LDAPUser], group_dn_adcm_name_map: dict[str, str], settings: LDAPSettings) -> None:
    sys.stdout.write(f"Synchronizing users...{os.linesep}")

    all_users_attrs = []
    for _, ldap_user_attrs in users:
        all_users_attrs.append(_extract_user_attributes(user_attrs=ldap_user_attrs, settings=settings))

    active_usernames = [user_attrs.username for user_attrs in all_users_attrs if user_attrs.is_active]
    to_delete_users = User.objects.filter(type=OriginType.LDAP)
    if active_usernames:
        to_delete_users = to_delete_users.exclude(username__iregex=f"({'|'.join(active_usernames)})")

    if to_delete_users.exists():
        to_delete_usernames = os.linesep.join(
            f" - {name}" for name in to_delete_users.values_list("username", flat=True)
        )
        to_delete_users.delete()
        sys.stdout.write(f"Delete user(s):{os.linesep}{to_delete_usernames}{os.linesep}")

    for user_attrs in all_users_attrs:
        if not user_attrs.is_active:
            continue

        _sync_ldap_user(attrs=user_attrs, group_dn_adcm_name_map=group_dn_adcm_name_map, settings=settings)

    sys.stdout.write(f"Users synchronization finished{os.linesep}")


def _sync_ldap_user(attrs: LDAPUserAttrs, group_dn_adcm_name_map: dict[str, str], settings: LDAPSettings) -> None:
    actual_user_attrs = attrs.dict(include=settings.user.attr_map.keys())

    kwargs_get = {
        "username__iexact": attrs.username,
        "type": OriginType.LDAP.value,
        "built_in": False,
    }
    kwargs_create = {
        "type": OriginType.LDAP.value,
        **actual_user_attrs,
    }
    user, created = _safe_get_or_create(model=User, kwargs_get=kwargs_get, kwargs_create=kwargs_create)
    if user is None:
        sys.stderr.write(f"Error synchronizing user {attrs.username}{os.linesep}")
        return

    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
        sys.stdout.write(f"User created: {user.username}{os.linesep}")
    else:
        update_fields = []
        for key, value in actual_user_attrs.items():
            if getattr(user, key, None) != value:
                setattr(user, key, value)
                update_fields.append(key)

        if update_fields:
            user.save(update_fields=update_fields)
            sys.stdout.write(f"User updated: {user.username}{os.linesep}")

    if not user.is_superuser and attrs.is_superuser:
        user.is_superuser = True
        user.save(update_fields=["is_superuser"])
        sys.stdout.write(f"Grant admin rights to {user.username}\n")
    elif user.is_superuser and not attrs.is_superuser:
        user.is_superuser = False
        user.save(update_fields=["is_superuser"])
        sys.stdout.write(f"Remove admin rights from {user.username}\n")

    if settings.group.search_base:
        user_group_names = [
            group_dn_adcm_name_map[group_dn.lower()]
            for group_dn in attrs.groups
            if group_dn.lower() in group_dn_adcm_name_map
        ]
    else:
        sys.stdout.write(
            f"`Group search base` is not configured. Getting all {user.username}'s ldap groups{os.linesep}"
        )
        user_group_names = _create_user_groups(group_dns=attrs.groups, cn_pattern=settings.cn_pattern)

    to_remove_groups = Group.objects.filter(~Q(display_name__in=user_group_names), user=user, type=OriginType.LDAP)
    if to_remove_groups.exists():
        to_remove_names = os.linesep.join(
            f" - {name}" for name in to_remove_groups.values_list("display_name", flat=True)
        )
        user.groups.remove(*to_remove_groups)
        sys.stdout.write(f"Remove user {user.username} from group(s):{os.linesep}{to_remove_names}{os.linesep}")

    to_add_groups = Group.objects.filter(
        display_name__in=set(user_group_names).difference(
            set(Group.objects.filter(user=user, type=OriginType.LDAP).values_list("display_name", flat=True))
        ),
        type=OriginType.LDAP,
    )
    if to_add_groups.exists():
        to_add_names = os.linesep.join(f" - {name}" for name in to_add_groups.values_list("display_name", flat=True))
        user.groups.add(*to_add_groups)
        sys.stdout.write(f"Add user {user.username} to group(s):{os.linesep}{to_add_names}{os.linesep}")


def _create_user_groups(group_dns: list[DistinguishedName], cn_pattern: Pattern) -> list[str]:
    """Returns list of user's groups' display_names"""
    errors = []
    created = []
    adcm_group_names = []
    for group_dn in group_dns:
        adcm_group_name = " ".join(sorted(cn_pattern.findall(group_dn)))

        name, display_name = get_group_name_display_name(name=adcm_group_name, type_=OriginType.LDAP.value)
        kwargs_get = {
            "name": name,
            "display_name": display_name,
            "type": OriginType.LDAP.value,
            "built_in": False,
        }
        group, created_ = _safe_get_or_create(model=Group, kwargs_get=kwargs_get)

        if group is not None:
            adcm_group_names.append(adcm_group_name)
            if created_:
                created.append(adcm_group_name)
        else:
            errors.append(adcm_group_name)

    if created:
        sys.stdout.write(
            f"Create group(s):{os.linesep}"
            f"{os.linesep.join([f' - {group_name}' for group_name in created])}{os.linesep}"
        )

    if errors:
        sys.stderr.write(f"Can't synchronize group(s):{os.linesep}{os.linesep.join(errors)}{os.linesep}")

    return adcm_group_names


def _extract_user_attributes(user_attrs: LDAPAttributes, settings: LDAPSettings) -> LDAPUserAttrs:
    attributes = {}

    for adcm_attr_name, ldap_attr_name in settings.user.attr_map.items():
        # LDAP attribute can be associated with multiple values and represented as a list of strings
        # if attribute is absent, default value ("") is used
        values = user_attrs.get(ldap_attr_name, [""])

        if len(values) != 1:
            raise LDAPDataError(
                f"Can't translate ldap `{ldap_attr_name}` attribute ({values}) of entity `"
                f"{user_attrs.get(settings.dn_attribute)}` to user's `{adcm_attr_name}` attribute"
            )

        attributes[adcm_attr_name] = values[0]

    # https://learn.microsoft.com/ru-ru/windows/win32/adschema/a-useraccountcontrol
    is_user_active = True
    if user_attrs.get(settings.user.active_attribute) and hex(
        int(user_attrs[settings.user.active_attribute][0])
    ).endswith("2"):
        is_user_active = False

    attributes["is_active"] = is_user_active
    attributes["groups"] = list(user_attrs.get(settings.user.group_membership_attribute, []))
    attributes["is_superuser"] = any(
        group_dn.lower() in settings.user.group_dn_adcm_admin for group_dn in attributes["groups"]
    )

    return LDAPUserAttrs(**attributes)


def _remove_all_ldap_users_and_groups() -> tuple[str, str]:
    """Returns formatted for writing to stdout removed users' usernames and removed groups' display_names"""

    ldap_users = User.objects.filter(type=OriginType.LDAP, built_in=False)
    ldap_groups = Group.objects.filter(type=OriginType.LDAP, built_in=False)

    user_usernames = ""
    if ldap_users.exists():
        user_usernames = os.linesep.join(f" - {username}" for username in ldap_users.values_list("username", flat=True))
        ldap_users.delete()

    group_display_names = ""
    if ldap_groups.exists():
        group_display_names = os.linesep.join(
            f" - {display_name}" for display_name in ldap_groups.values_list("display_name", flat=True)
        )
        ldap_groups.delete()

    return user_usernames, group_display_names


def _safe_get_or_create(
    model: type[User | Group], kwargs_get: dict, kwargs_create: dict | None = None
) -> tuple[User | Group | None, bool | None]:
    """
    Purpose of this function is to get or create `model` instance without raising database errors,
    since they are the reason of transaction rollback, even if handled. And this breaks ldap_sync logic.
    """

    qs = model.objects.filter(**kwargs_get)
    if qs.count() > 1:
        return None, None

    if qs.count() == 1:
        return qs.get(), False

    kwargs_create = kwargs_get if kwargs_create is None else kwargs_create

    model_constraints = UNIQUE_FIELDS[model.__name__]
    query_check_unique_constraints = Q(
        **{key: value for key, value in kwargs_create.items() if key in model_constraints[0]}
    )
    for unique_constraint in model_constraints[1:]:
        query_check_unique_constraints |= Q(
            **{key: value for key, value in kwargs_create.items() if key in unique_constraint}
        )

    if model.objects.filter(query_check_unique_constraints).exists():
        return None, None

    return model.objects.create(**kwargs_create), True


@atomic()
def main() -> None:
    ldap_settings = get_ldap_settings()

    with get_connection(settings=ldap_settings.connection) as connection:
        ldap_query = LDAPQuery(connection=connection, settings=ldap_settings)

        groups = None
        if ldap_settings.group.search_base:
            groups = ldap_query.groups()

            if not groups:
                sys.stdout.write(f"No groups found. Clearing ldap users and groups{os.linesep}")

                removed_users, removed_groups = _remove_all_ldap_users_and_groups()
                if removed_users:
                    sys.stdout.write(f"Users deleted:{os.linesep}{removed_users}{os.linesep}")
                if removed_groups:
                    sys.stdout.write(f"Users deleted:{os.linesep}{removed_groups}{os.linesep}")

                return

        users = ldap_query.users(target_group_dns=(group[0] for group in groups) if groups else None)

    dn_adcm_group_name_map = _process_groups(
        groups=groups or [], group_name_attribute=ldap_settings.group.name_attribute
    )
    _process_users(users=users, group_dn_adcm_name_map=dn_adcm_group_name_map, settings=ldap_settings)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(
            f"Synchronization error:{os.linesep}{''.join(format_exception(type(e), e, e.__traceback__))}{os.linesep}"
        )
        sys.exit(1)
