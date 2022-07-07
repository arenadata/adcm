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

"""Simple working with LDAP for tests purposes"""

import uuid
from typing import NamedTuple, List, Optional, Tuple
from zlib import crc32

import allure
import ldap
from adcm_pytest_plugin.custom_types import SecureString
from ldap.ldapobject import SimpleLDAPObject


class LDAPTestConfig(NamedTuple):
    """Storage for required LDAP config"""

    uri: str
    admin_dn: str
    admin_pass: SecureString
    base_ou_dn: str
    cert: Optional[SecureString] = None


class LDAPEntityManager:
    """Basic manipulations with LDAP for test purposes"""

    conn: SimpleLDAPObject
    test_dn: str

    _config: LDAPTestConfig
    _created_records: List[str]
    # unique name identifier
    # it will be added to user/group names
    _uni: str

    _BASE_OU_MODLIST = [('objectClass', [b'top', b'organizationalUnit'])]
    _BASE_GROUP_MODLIST = [('objectClass', [b'top', b'group'])]
    _BASE_USER_MODLIST = [('objectClass', [b'top', b'person', b'organizationalPerson', b'user'])]

    _ACTIVE_USER_UAC = b'512'  # regular user
    _INACTIVE_USER_UAC = b'514'  # user, inactive
    _DEFAULT_USER_UAC = b'546'  # user, inactive, password not required

    def __init__(self, config: LDAPTestConfig, test_name: str):
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)  # pylint: disable=no-member
        self.conn = ldap.initialize(config.uri)  # pylint: disable=no-member
        self.conn.simple_bind_s(config.admin_dn, config.admin_pass)

        self._created_records = []
        self._config = config
        self._uni = str(crc32(f'{test_name}{uuid.uuid4()}'.encode('utf-8')))
        # for the cleanup we'll need the CN with uppercase node names, I think
        corrected_base_ou_dn = ','.join(
            map(
                lambda x: ((parts := x.split('=')) and f'{parts[0].upper()}={parts[1]}'),
                self._config.base_ou_dn.split(','),
            )
        )
        self.test_dn = self.create_ou(self._uni, corrected_base_ou_dn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_test_ou()
        self.conn.unbind()

    @allure.step('Create OU {name}')
    def create_ou(self, name: str, custom_base_dn: str = None) -> str:
        """Create OU (use for 'isolation' in tests)"""
        base_dn = custom_base_dn or self.test_dn
        new_dn = f'OU={name},{base_dn}'
        self.conn.add_s(new_dn, self._BASE_OU_MODLIST)
        self._created_records.append(new_dn)
        return new_dn

    @allure.step('Create group {name}')
    def create_group(self, name: str, custom_base_dn: str = None) -> str:
        """Create group (CN) that can include users"""
        base_dn = custom_base_dn or self.test_dn
        new_dn = f'CN={name},{base_dn}'
        self.conn.add_s(new_dn, self._BASE_GROUP_MODLIST)
        self._created_records.append(new_dn)
        return new_dn

    @allure.step('Create user {name} with password {password}')
    def create_user(
        self,
        name: str,
        password: str,
        custom_base_dn: str = None,
        extra_modlist: Optional[List[Tuple[str, List[bytes]]]] = None,
    ) -> str:
        """
        Create user (CN) and activate it.
        `name` is used both in CN and as sAMAccountName,
        so it should be unique not only in parent OU.
        """
        extra_modlist = extra_modlist or []
        base_dn = custom_base_dn or self.test_dn
        new_dn = f'CN={name},{base_dn}'
        self.conn.add_s(new_dn, self._BASE_USER_MODLIST + [('sAMAccountName', name.encode('utf-8'))] + extra_modlist)
        self._created_records.append(new_dn)
        self.set_user_password(new_dn, password)
        self.activate_user(new_dn)
        return new_dn

    def delete(self, dn: str) -> None:
        """Delete record from LDAP"""
        self.conn.delete_s(dn)
        self._created_records.remove(dn)

    @allure.step('Activate user {user_dn}')
    def activate_user(self, user_dn: str, uac: bytes = _ACTIVE_USER_UAC) -> None:
        """Activate user"""
        self.conn.modify_s(user_dn, [(ldap.MOD_REPLACE, 'userAccountControl', uac)])  # pylint: disable=no-member

    @allure.step('Deactivate user {user_dn}')
    def deactivate_user(self, user_dn: str, uac: bytes = _INACTIVE_USER_UAC) -> None:
        """Deactivate user"""
        self.conn.modify_s(user_dn, [(ldap.MOD_REPLACE, 'userAccountControl', uac)])  # pylint: disable=no-member

    @allure.step('Set password "{password}" for user {user_dn}')
    def set_user_password(self, user_dn: str, password: str) -> None:
        """Set password for an existing user"""
        pass_utf16 = f'"{password}"'.encode('utf-16-le')
        self.conn.modify_s(user_dn, [(ldap.MOD_REPLACE, 'unicodePwd', [pass_utf16])])  # pylint: disable=no-member

    @allure.step('Add user {user_dn} to {group_dn}')
    def add_user_to_group(self, user_dn: str, group_dn: str) -> None:
        """Add user to a group"""
        mod_group = [(ldap.MOD_ADD, 'member', [user_dn.encode('utf-8')])]  # pylint: disable=no-member
        self.conn.modify_s(group_dn, mod_group)

    @allure.step('Remove user {user_dn} from {group_dn}')
    def remove_user_from_group(self, user_dn: str, group_dn: str) -> None:
        """Remove user from group"""
        mod_group = [(ldap.MOD_DELETE, 'member', [user_dn.encode('utf-8')])]  # pylint: disable=no-member
        self.conn.modify_s(group_dn, mod_group)

    @allure.step('Cleat test OU')
    def clean_test_ou(self):
        """Remove every object in test OU"""
        if self.test_dn is None:
            return
        # not everything is deleted on first round
        for _ in range(10):
            entities = self._get_entities_from_test_ou()
            if len(entities) == 0:
                break
            for dn in entities:  # pylint: disable=invalid-name
                self.conn.delete(dn)
        else:
            raise RuntimeError(f'Not all entities in test OU were deleted: {entities}')
        self._created_records = []
        self.test_dn = None

    def _get_entities_from_test_ou(self):
        try:
            return sorted(
                (dn for dn, _ in self.conn.search_s(self.test_dn, ldap.SCOPE_SUBTREE)),  # pylint: disable=no-member
                key=len,
                reverse=True,
            )
        except ldap.NO_SUCH_OBJECT:  # pylint: disable=no-member
            return []
