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
from typing import Iterable
import os
import sys

os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']}:/adcm/python/"
sys.path.append("/adcm/python/")

import adcm.init_django  # noqa: F401 # isort:skip

from django.db import DataError, IntegrityError
from django.db.models import Q
from django.db.transaction import atomic
from rbac.models import Group, OriginType, User
from rbac.services.ldap import LDAPQuery, LDAPSettings, get_connection, get_ldap_settings
from rbac.services.ldap.errors import LDAPDataError
from rbac.services.ldap.types import LDAPAttributes, LDAPGroup, LDAPUser, LDAPUserAttrs
from rbac.services.ldap.utils import str_join_attr_list


def _process_groups(groups: Iterable[LDAPGroup], group_name_attribute: str) -> dict[str, str]:
    sys.stdout.write(f"Synchronizing groups...{os.linesep}")

    dn_adcm_name_map: dict[str, str] = {}
    for group_dn, group_attrs in groups:
        dn_adcm_name_map[group_dn.lower()] = str_join_attr_list(
            ldap_attributes=group_attrs, target_attr=group_name_attribute
        )

    ldap_groups_qs = Group.objects.filter(type=OriginType.LDAP)
    existing_groups = ldap_groups_qs.filter(display_name__in=dn_adcm_name_map.values())

    to_delete_group_ids = set(ldap_groups_qs.values_list("id", flat=True)).difference(
        set(existing_groups.values_list("id", flat=True))
    )
    to_delete_groups = Group.objects.filter(id__in=to_delete_group_ids)
    if to_delete_groups.exists():
        deleted_group_names = os.linesep.join(
            [f" - {name}" for name in to_delete_groups.values_list("display_name", flat=True)]
        )
        to_delete_groups.delete()
        sys.stdout.write(f"Groups deleted:{os.linesep}{deleted_group_names}{os.linesep}")

    created = []
    errors = []
    for adcm_group_name in set(dn_adcm_name_map.values()).difference(
        set(existing_groups.values_list("display_name", flat=True))
    ):
        try:
            Group.objects.create(name=adcm_group_name, type=OriginType.LDAP, built_in=False)
            created.append(f" - {adcm_group_name}")
        except (IntegrityError, DataError) as e:
            errors.append(f" - {adcm_group_name}")
            continue

    if created:
        sys.stdout.write(f"Create group(s):{os.linesep}{os.linesep.join(created)}{os.linesep}")

    if errors:
        sys.stderr.write(f"Can't synchronize group(s):{os.linesep}{os.linesep.join(errors)}{os.linesep}")

    sys.stdout.write(f"Groups synchronization finished{os.linesep}")

    return dn_adcm_name_map


def _process_users(users: Iterable[LDAPUser], group_dn_adcm_name_map: dict[str, str], settings: LDAPSettings) -> None:
    sys.stdout.write(f"Synchronizing users...{os.linesep}")

    all_users_attrs = []
    for _, ldap_user_attrs in users:
        all_users_attrs.append(_extract_user_attributes(user_attrs=ldap_user_attrs, settings=settings))

    active_usernames = [user_attrs.username for user_attrs in all_users_attrs if user_attrs.is_active]
    to_delete_users = User.objects.filter(type=OriginType.LDAP).exclude(
        username__iregex=f"({'|'.join(active_usernames)})"
    )
    if to_delete_users.exists():
        to_delete_usernames = os.linesep.join(
            [f" - {name}" for name in to_delete_users.values_list("username", flat=True)]
        )
        to_delete_users.delete()
        sys.stdout.write(f"Delete user(s):{os.linesep}{to_delete_usernames}{os.linesep}")

    for user_attrs in all_users_attrs:
        if not user_attrs.is_active:
            continue

        _sync_ldap_user(
            attrs=user_attrs, user_attr_map=settings.user.attr_map, group_dn_adcm_name_map=group_dn_adcm_name_map
        )

    sys.stdout.write(f"Users synchronization finished{os.linesep}")


def _sync_ldap_user(
    attrs: LDAPUserAttrs, user_attr_map: dict[str, str], group_dn_adcm_name_map: dict[str, str]
) -> None:
    actual_user_attrs = {key: value for key, value in attrs.dict().items() if key in user_attr_map}
    user, created = User.objects.get_or_create(
        username__iexact=attrs.username, type=OriginType.LDAP, defaults=actual_user_attrs
    )

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

    user_group_names = [
        group_dn_adcm_name_map[group_dn] for group_dn in attrs.groups if group_dn in group_dn_adcm_name_map
    ]

    to_remove_groups = Group.objects.filter(~Q(display_name__in=user_group_names), user=user, type=OriginType.LDAP)
    if to_remove_groups.exists():
        to_remove_names = os.linesep.join(
            [f" - {name}" for name in to_remove_groups.values_list("display_name", flat=True)]
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
        to_add_names = os.linesep.join([f" - {name}" for name in to_add_groups.values_list("display_name", flat=True)])
        user.groups.add(*to_add_groups)
        sys.stdout.write(f"Add user {user.username} to group(s):{os.linesep}{to_add_names}{os.linesep}")


def _extract_user_attributes(user_attrs: LDAPAttributes, settings: LDAPSettings) -> LDAPUserAttrs:
    attributes = {}

    for adcm_attr_name, ldap_attr_name in settings.user.attr_map.items():
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
    attributes["groups"] = [group_dn.lower() for group_dn in user_attrs[settings.user.group_membership_attribute]]

    return LDAPUserAttrs(**attributes)


@atomic()
def main() -> None:
    ldap_settings = get_ldap_settings()

    with get_connection(settings=ldap_settings.connection) as connection:
        ldap_query = LDAPQuery(connection=connection, settings=ldap_settings)

        groups = None
        if ldap_settings.group.search_base is not None:
            groups = ldap_query.groups()

            if not groups:
                sys.stdout.write("No groups found. Aborting synchronization")
                return

        users = ldap_query.users(target_group_dns=(group[0] for group in groups) if groups else None)

    dn_adcm_group_name_map = _process_groups(
        groups=groups or [], group_name_attribute=ldap_settings.group.name_attribute
    )
    _process_users(users=users, group_dn_adcm_name_map=dn_adcm_group_name_map, settings=ldap_settings)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(
            f"Synchronization error:{os.linesep}{''.join(format_exception(type(e), e, e.__traceback__))}{os.linesep}"
        )
