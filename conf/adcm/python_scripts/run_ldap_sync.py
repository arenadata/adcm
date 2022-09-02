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

import adcm.init_django  # pylint: disable=unused-import
from rbac.models import User, Group, OriginType
from rbac.ldap import _get_ldap_default_settings, configure_tls, is_tls
from cm.errors import AdcmEx
from cm.logger import logger
from django.db import DataError, IntegrityError

CERT_ENV_KEY = "LDAPTLS_CACERT"


class SyncLDAP:
    _settings = None
    _conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = self._bind()
        return self._conn

    def _bind(self):
        try:
            ldap.set_option(ldap.OPT_REFERRALS, 0)
            conn = ldap.initialize(self.settings["SERVER_URI"])
            conn.protocol_version = ldap.VERSION3
            configure_tls(is_tls(self.settings["SERVER_URI"]), os.environ.get(CERT_ENV_KEY, ""), conn)
            conn.simple_bind_s(self.settings["BIND_DN"], self.settings["BIND_PASSWORD"])
        except ldap.LDAPError as e:
            sys.stdout.write(f"Can't connect to {self.settings['SERVER_URI']} with user: {self.settings['BIND_DN']}. Error: {e}\n")
            raise
        return conn

    def unbind(self):
        if self._conn is not None:
            self.conn.unbind_s()
            self._conn = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings, error_code = _get_ldap_default_settings()
            if error_code is not None:
                error = AdcmEx(error_code)
                sys.stdout.write(error.msg)
                raise error
        return self._settings

    def sync(self):
        ldap_groups = self.sync_groups()
        if ldap_groups:
            self.sync_users(ldap_groups)
        else:
            sys.stdout.write("No groups found. Aborting sync users")

    def sync_groups(self):
        """Synchronize LDAP groups with group model and delete groups which is not found in LDAP"""
        self.settings["GROUP_SEARCH"].filterstr = f"(&" \
                                                  f"(objectClass={self.settings['GROUP_OBJECT_CLASS']})" \
                                                  f"{self.settings['GROUP_FILTER']})"
        ldap_groups = self.settings["GROUP_SEARCH"].execute(self.conn, {})
        self._sync_ldap_groups(ldap_groups)
        sys.stdout.write("Groups were synchronized\n")
        return ldap_groups

    def sync_users(self, ldap_groups):
        """Synchronize LDAP users with user model and delete users which is not found in LDAP"""
        group_filter = ""
        for group_dn, group_attrs in ldap_groups:
            group_filter += f"(memberOf={group_dn})"
        if group_filter:
            group_filter = f"(|{group_filter})"
        self.settings["USER_SEARCH"].filterstr = f"(&" \
                                                 f"(objectClass={self.settings['USER_OBJECT_CLASS']})" \
                                                 f"{self.settings['USER_FILTER']}" \
                                                 f"{group_filter})"
        ldap_users = self.settings["USER_SEARCH"].execute(self.conn, {"user": "*"}, True)
        self._sync_ldap_users(ldap_users)
        sys.stdout.write("Users were synchronized\n")

    def _sync_ldap_groups(self, ldap_groups):
        new_groups = set()
        error_names = []
        for cname, ldap_attributes in ldap_groups:
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
                sys.stdout.write("Error creating group %s: %s\n" % (name, e))
                continue
            else:
                if created:
                    sys.stdout.write("Create new group: %s\n" % name)
        django_groups = set(Group.objects.filter(type=OriginType.LDAP).values_list("display_name", flat=True))
        for groupname in django_groups - new_groups:
            group = Group.objects.get(name__iexact=f"{groupname} [ldap]")
            sys.stdout.write(f"Delete this group: {group}\n")
            group.delete()
        msg = "Sync of groups ended successfully."
        msg += f"Couldn\'t synchronize groups: {error_names}\n" if error_names else ""
        logger.debug(msg)

    def _sync_ldap_users(self, ldap_users):
        ldap_usernames = set()
        error_names = []
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
                sys.stdout.write("Error creating user %s: %s\n" % (username, e))
                continue
            else:
                updated = False
                user.is_active = False
                if not hex(int(ldap_attributes["useraccountcontrol"][0])).endswith("2"):
                    user.is_active = True
                if created:
                    sys.stdout.write("Create user: %s\n" % username)
                    user.set_unusable_password()
                else:
                    for name, attr in defaults.items():
                        current_attr = getattr(user, name, None)
                        if current_attr != attr:
                            setattr(user, name, attr)
                            updated = True
                    if updated:
                        sys.stdout.write("Updated user: %s\n" % username)

                # Remove condition after ADCM-2944
                if not user.is_active:
                    sys.stdout.write(f"Delete this user and deactivate his session: {user}\n")
                    user.delete()
                else:
                    user.save()
                    ldap_usernames.add(username)
                    for group in ldap_attributes.get("memberof", []):
                        name = group.split(",")[0][3:]
                        try:
                            group = Group.objects.get(name=f"{name} [ldap]", built_in=False,
                                                      type=OriginType.LDAP)
                            group.user_set.add(user)
                            sys.stdout.write(f"Add user {user} to group {group}\n")
                        except (IntegrityError, DataError) as e:
                            sys.stdout.write("Error getting group %s: %s\n" % (name, e))

        django_usernames = set(User.objects.filter(type=OriginType.LDAP).values_list("username", flat=True))
        for username in django_usernames - ldap_usernames:
            user = User.objects.get(username__iexact=username)
            sys.stdout.write(f"Delete this user and deactivate his session: {user}\n")
            user.delete()
            # Uncomment after ADCM-2944
            # user.is_active = False
            # user.save()
        msg = "Sync of users ended successfully."
        msg += f"Couldn\'t synchronize users: {error_names}\n" if error_names else ""
        logger.debug(msg)


if __name__ == "__main__":
    sync_ldap = SyncLDAP()
    sync_ldap.sync()
    sync_ldap.unbind()
