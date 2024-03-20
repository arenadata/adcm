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

from typing import Iterable

from django_auth_ldap.config import LDAPSearch
import ldap

from rbac.services.ldap.errors import LDAPConfigurationError
from rbac.services.ldap.types import DistinguishedName, LDAPGroup, LDAPSettings, LDAPUser


class LDAPQuery:
    def __init__(self, connection: ldap.ldapobject.LDAPObject, settings: LDAPSettings) -> None:
        self._connection = connection
        self._settings = settings

    def users(self, target_group_dns: Iterable[DistinguishedName] | None = None) -> Iterable[LDAPUser]:
        group_filter = ""
        for group_dn in target_group_dns or []:
            group_filter += f"({self._settings.user.group_membership_attribute}={group_dn})"
        if group_filter:
            group_filter = f"(|{group_filter})"

        filterstr = (
            "(&"
            f"(objectClass={self._settings.user.object_class})"
            f"{self._process_extra_filter(filterstr=self._settings.user.search_filter)}"
            f"{group_filter}"
            ")"
        )

        return LDAPSearch(
            base_dn=self._settings.user.search_base,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=filterstr,
        ).execute(self._connection)

    def groups(self) -> Iterable[LDAPGroup]:
        if not self._settings.group.search_base:
            raise LDAPConfigurationError("Can't search LDAP groups. Configure `Group search base` settings parameter")

        filterstr = (
            "(&"
            f"(objectClass={self._settings.group.object_class})"
            f"{self._process_extra_filter(filterstr=self._settings.group.search_filter)}"
            ")"
        )

        return LDAPSearch(
            base_dn=self._settings.group.search_base,
            scope=ldap.SCOPE_SUBTREE,
            filterstr=filterstr,
        ).execute(self._connection)

    @staticmethod
    def _process_extra_filter(filterstr: str) -> str:
        filterstr = filterstr or ""

        if filterstr == "":
            return filterstr

        # simple single filter ex: `primaryGroupID=513`
        if not (filterstr.startswith("(") and filterstr.endswith(")")):
            return f"({filterstr})"

        # assume that composed filter is syntactically valid
        return filterstr
