#!/usr/bin/env python3
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

import os
import sys

import ldap

os.environ["PYTHONPATH"] = "/adcm/python/"
sys.path.append("/adcm/python/")

import adcm.init_django  # noqa: F401 # isort:skip

from cm.errors import AdcmEx
from cm.logger import logger
from django.db import DataError, IntegrityError
from rbac.ldap import (
    configure_tls,
    get_groups_by_user_dn,
    get_ldap_config,
    get_ldap_default_settings,
    get_user_search,
    is_tls,
)
from rbac.models import Group, OriginType, User

CERT_ENV_KEY = "LDAPTLS_CACERT"


class SyncLDAP:
    def __init__(self):
        self._settings = None
        self._conn = None

    @property
    def conn(self) -> ldap.ldapobject.LDAPObject:
        if self._conn is None:
            self._conn = self._bind()
        return self._conn

    @property
    def _group_search_configured(self) -> bool:
        return "GROUP_SEARCH" in self.settings and bool(self.settings.get("GROUP_SEARCH"))

    def _bind(self) -> ldap.ldapobject.LDAPObject:
        try:
            ldap.set_option(ldap.OPT_REFERRALS, 0)
            conn = ldap.initialize(self.settings["SERVER_URI"])
            conn.protocol_version = ldap.VERSION3
            configure_tls(is_tls(self.settings["SERVER_URI"]), os.environ.get(CERT_ENV_KEY, ""), conn)
            conn.simple_bind_s(self.settings["BIND_DN"], self.settings["BIND_PASSWORD"])
        except ldap.LDAPError as e:
            sys.stdout.write(
                f"Can't connect to {self.settings['SERVER_URI']} "
                f"with user: {self.settings['BIND_DN']}. Error: {e}\n"
            )
            raise
        return conn

    @staticmethod
    def _deactivate_extra_users(ldap_usernames: set):
        django_usernames = set(User.objects.filter(type=OriginType.LDAP).values_list("username", flat=True))
        for username in django_usernames - ldap_usernames:
            user = User.objects.get(username__iexact=username)
            sys.stdout.write(f"Delete user: {user}\n")
            user.delete()

    def unbind(self) -> None:
        if self._conn is not None:
            self.conn.unbind_s()
            self._conn = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings, error_code = get_ldap_default_settings()
            if error_code is not None:
                error = AdcmEx(error_code)
                sys.stdout.write(error.msg)
                raise error
            self._settings["DEFAULT_USER_SEARCH"] = get_user_search(get_ldap_config())
        return self._settings

    def sync(self) -> None:
        ldap_groups = self.sync_groups()
        self.sync_users(ldap_groups)

    def sync_groups(self) -> list:
        """Synchronize LDAP groups with group model and delete groups which is not found in LDAP"""
        ldap_groups = []
        if self._group_search_configured:
            self.settings["GROUP_SEARCH"].filterstr = (
                f"(&" f"(objectClass={self.settings['GROUP_OBJECT_CLASS']})" f"{self.settings['GROUP_FILTER']})"
            )
            ldap_groups = self.settings["GROUP_SEARCH"].execute(self.conn, {})
            self._sync_ldap_groups(ldap_groups)
            sys.stdout.write("Groups were synchronized\n")

        return ldap_groups

    def sync_users(self, ldap_groups: list) -> None:
        """Synchronize LDAP users with user model and delete users which is not found in LDAP"""
        if not ldap_groups and self._group_search_configured:
            sys.stdout.write("No groups found. Aborting sync users\n")
            self._deactivate_extra_users(set())
            return

        group_filter = ""
        for group_dn, _ in ldap_groups:
            group_filter += f"(memberOf={group_dn})"
        if group_filter:
            group_filter = f"(|{group_filter})"

        self.settings["USER_SEARCH"].filterstr = (
            f"(&"
            f"(objectClass={self.settings['USER_OBJECT_CLASS']})"
            f"{self.settings['USER_FILTER']}"
            f"{group_filter})"
        )
        ldap_users = self.settings["USER_SEARCH"].execute(self.conn, {"user": "*"}, True)

        self._sync_ldap_users(ldap_users, ldap_groups)
        sys.stdout.write("Users were synchronized\n")

    def _sync_ldap_groups(self, ldap_groups: list) -> None:
        new_groups = set()
        error_names = []
        for _, ldap_attributes in ldap_groups:
            try:
                name = ldap_attributes[self.settings["GROUP_TYPE"].name_attr][0]
            except KeyError:
                name = ""

            try:
                group, created = Group.objects.get_or_create(
                    name=f"{name} [ldap]", built_in=False, type=OriginType.LDAP
                )
                group.user_set.clear()
                new_groups.add(name)
            except (IntegrityError, DataError) as e:
                error_names.append(name)
                sys.stdout.write(f"Error creating group {name}: {e}\n")
                continue
            else:
                if created:
                    sys.stdout.write(f"Create new group: {name}\n")
        django_groups = set(Group.objects.filter(type=OriginType.LDAP).values_list("display_name", flat=True))
        for groupname in django_groups - new_groups:
            group = Group.objects.get(name__iexact=f"{groupname} [ldap]")
            sys.stdout.write(f"Delete this group: {group}\n")
            group.delete()
        msg = "Sync of groups ended successfully."
        msg = f"{msg} Couldn't synchronize groups: {error_names}" if error_names else f"{msg}"
        logger.debug(msg)

    def _sync_ldap_users(self, ldap_users: list, ldap_groups: list) -> None:
        ldap_group_names = [group[0].split(",")[0][3:] for group in ldap_groups]
        ldap_usernames = set()
        error_names = []
        deleted_names: list[str] = []

        for cname, ldap_attributes in ldap_users:
            defaults = {}
            for field, ldap_name in self.settings["USER_ATTR_MAP"].items():
                try:
                    defaults[field] = ldap_attributes[ldap_name][0]
                except KeyError:
                    defaults[field] = ""

            username = defaults["username"]
            kwargs = {
                "username__iexact": username,
                "type": OriginType.LDAP,
                "defaults": defaults,
            }

            try:
                user, created = User.objects.get_or_create(**kwargs)
            except (IntegrityError, DataError) as e:
                error_names.append(username)
                sys.stdout.write(f"Error creating user {username}: {e}\n")
                continue
            else:
                if not self._is_ldap_user_active(ldap_attrs=ldap_attributes):
                    deleted_names.append(user.username)
                    user.delete()
                    continue

                updated = False

                if created:
                    sys.stdout.write(f"Create user: {username}\n")
                    user.set_unusable_password()
                else:
                    for name, attr in defaults.items():
                        current_attr = getattr(user, name, None)
                        if current_attr != attr:
                            setattr(user, name, attr)
                            updated = True
                    if updated:
                        sys.stdout.write(f"Updated user: {username}\n")

                user.save()
                ldap_usernames.add(username)

                if not self._group_search_configured:
                    self._process_user_ldap_groups(user, cname)
                else:
                    for group in ldap_attributes.get("memberof", []):
                        name = group.split(",")[0][3:]
                        if name.lower() not in ldap_group_names:
                            continue
                        try:
                            group = Group.objects.get(name=f"{name} [ldap]", built_in=False, type=OriginType.LDAP)
                            group.user_set.add(user)
                            sys.stdout.write(f"Add user {user} to group {group}\n")
                        except (IntegrityError, DataError, Group.DoesNotExist) as e:
                            sys.stdout.write(f"Error getting group {name}: {e}\n")
        self._deactivate_extra_users(ldap_usernames)

        msg = "Sync of users ended successfully."
        if error_names:
            msg = f"{msg}{os.linesep}Couldn't synchronize users: {error_names}"
        if deleted_names:
            msg = f"{msg}{os.linesep}Deleted users (inactive in ldap): {deleted_names}"
        logger.debug(msg)

    def _process_user_ldap_groups(self, user: User, user_dn: str) -> None:
        ldap_group_names, err_msg = get_groups_by_user_dn(
            user_dn=user_dn, user_search=self.settings["DEFAULT_USER_SEARCH"], conn=self.conn
        )
        if err_msg:
            sys.stdout.write(f"Can't get groups of user `{user_dn}`: {err_msg}\n")
            raise RuntimeError(err_msg)

        for ldap_group_name in ldap_group_names:
            group_qs = Group.objects.filter(name=f"{ldap_group_name} [{OriginType.LDAP.value}]")
            if not group_qs.exists():
                group = Group.objects.create(name=ldap_group_name, type=OriginType.LDAP)
            else:
                group = group_qs[0]
            group.user_set.add(user)
            sys.stdout.write(f"Add user {user} to group {ldap_group_name}\n")

    @staticmethod
    def _is_ldap_user_active(ldap_attrs: dict) -> bool:
        target_attr = "useraccountcontrol"
        if ldap_attrs.get(target_attr) and not hex(int(ldap_attrs[target_attr][0])).endswith("2"):
            return True

        return False


if __name__ == "__main__":
    sync_ldap = SyncLDAP()
    sync_ldap.sync()
    sync_ldap.unbind()
