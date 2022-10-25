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
import warnings
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple
from zlib import crc32

import allure
import ldap
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.custom_types import SecureString
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from ldap.ldapobject import SimpleLDAPObject

from tests.library.utils import ConfigError

LDAP_PREFIX = "ldap://"
LDAPS_PREFIX = "ldaps://"


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

    _BASE_OU_MODLIST = [("objectClass", [b"top", b"organizationalUnit"])]
    _BASE_GROUP_MODLIST = [("objectClass", [b"top", b"group"])]
    _BASE_USER_MODLIST = [("objectClass", [b"top", b"person", b"organizationalPerson", b"user"])]

    _ACTIVE_USER_UAC = b"512"  # regular user
    _INACTIVE_USER_UAC = b"514"  # user, inactive
    _DEFAULT_USER_UAC = b"546"  # user, inactive, password not required

    _ATTR_MAP = {
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    }

    def __init__(self, config: LDAPTestConfig, test_name: str):
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)  # pylint: disable=no-member
        self.conn = ldap.initialize(config.uri)  # pylint: disable=no-member
        self.conn.simple_bind_s(config.admin_dn, config.admin_pass)

        self._created_records = []
        self._config = config
        self._uni = str(crc32(f"{test_name}{uuid.uuid4()}".encode("utf-8")))
        # for the cleanup we'll need the CN with uppercase node names, I think
        corrected_base_ou_dn = ",".join(
            map(
                lambda x: ((parts := x.split("=")) and f"{parts[0].upper()}={parts[1]}"),
                self._config.base_ou_dn.split(","),
            )
        )
        self.test_dn = self.create_ou(self._uni, corrected_base_ou_dn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clean_test_ou()
        self.conn.unbind()

    @allure.step("Create OU {name}")
    def create_ou(self, name: str, custom_base_dn: str = None) -> str:
        """Create OU (use for 'isolation' in tests)"""
        base_dn = custom_base_dn or self.test_dn
        new_dn = f"OU={name},{base_dn}"
        self.conn.add_s(new_dn, self._BASE_OU_MODLIST)
        self._created_records.append(new_dn)
        return new_dn

    @allure.step("Create group {name}")
    def create_group(self, name: str, custom_base_dn: str = None) -> str:
        """Create group (CN) that can include users"""
        base_dn = custom_base_dn or self.test_dn
        new_dn = f"CN={name},{base_dn}"
        self.conn.add_s(new_dn, self._BASE_GROUP_MODLIST)
        self._created_records.append(new_dn)
        return new_dn

    @allure.step("Create user {name} with password {password}")
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
        new_dn = f"CN={name},{base_dn}"
        self.conn.add_s(new_dn, self._BASE_USER_MODLIST + [("sAMAccountName", name.encode("utf-8"))] + extra_modlist)
        self._created_records.append(new_dn)
        self.set_user_password(new_dn, password)
        self.activate_user(new_dn)
        return new_dn

    def delete(self, dn: str) -> None:
        """Delete record from LDAP"""
        self.conn.delete_s(dn)
        self._created_records.remove(dn)

    @allure.step("Activate user {user_dn}")
    def activate_user(self, user_dn: str, uac: bytes = _ACTIVE_USER_UAC) -> None:
        """Activate user"""
        self.conn.modify_s(user_dn, [(ldap.MOD_REPLACE, "userAccountControl", uac)])  # pylint: disable=no-member

    @allure.step("Deactivate user {user_dn}")
    def deactivate_user(self, user_dn: str, uac: bytes = _INACTIVE_USER_UAC) -> None:
        """Deactivate user"""
        self.conn.modify_s(user_dn, [(ldap.MOD_REPLACE, "userAccountControl", uac)])  # pylint: disable=no-member

    @allure.step('Set password "{password}" for user {user_dn}')
    def set_user_password(self, user_dn: str, password: str) -> None:
        """Set password for an existing user"""
        pass_utf16 = f'"{password}"'.encode("utf-16-le")
        self.conn.modify_s(user_dn, [(ldap.MOD_REPLACE, "unicodePwd", [pass_utf16])])  # pylint: disable=no-member

    @allure.step("Update user in LDAP")
    def update_user(self, user_dn: str, **fields: str):
        """Update user record"""
        try:
            self.conn.modify_s(
                user_dn, [(ldap.MOD_REPLACE, self._ATTR_MAP[k], [v.encode("utf-8")]) for k, v in fields.items()]
            )
        except KeyError as e:
            unknown_fields = {k for k in fields if k in self._ATTR_MAP}
            raise ValueError(
                f'You can update only those fields: {", ".join(self._ATTR_MAP.keys())}\n'
                f'Input was: {", ".join(unknown_fields)}'
            ) from e

    @allure.step("Add user {user_dn} to {group_dn}")
    def add_user_to_group(self, user_dn: str, group_dn: str) -> None:
        """Add user to a group"""
        mod_group = [(ldap.MOD_ADD, "member", [user_dn.encode("utf-8")])]  # pylint: disable=no-member
        self.conn.modify_s(group_dn, mod_group)

    @allure.step("Remove user {user_dn} from {group_dn}")
    def remove_user_from_group(self, user_dn: str, group_dn: str) -> None:
        """Remove user from group"""
        mod_group = [(ldap.MOD_DELETE, "member", [user_dn.encode("utf-8")])]  # pylint: disable=no-member
        self.conn.modify_s(group_dn, mod_group)

    @allure.step("Cleat test OU")
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
            # error was leading to tests re-run that can make more "dead" objects
            warnings.warn(f"Not all entities in test OU were deleted: {entities}")
            return
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


# pylint: disable-next=too-many-arguments
def configure_adcm_for_ldap(
    client: ADCMClient,
    config: LDAPTestConfig,
    ssl_on: bool,
    ssl_cert: Optional[Path],
    user_base: str,
    group_base: Optional[str],
    extra_config: Optional[dict] = None,
):
    """Set ADCM settings to work with LDAP (for tests only)"""
    extra_config = extra_config or {}
    ssl_extra_config = {}
    uri = config.uri
    # we suggest that configuration is right
    if ssl_on:
        if config.uri.startswith(LDAP_PREFIX):
            uri = uri.replace(LDAP_PREFIX, LDAPS_PREFIX)
        if ssl_cert is None:
            raise ConfigError("AD SSL cert should be uploaded to ADCM")
        ssl_extra_config["tls_ca_cert_file"] = str(ssl_cert)
    elif not ssl_on and config.uri.startswith(LDAPS_PREFIX):
        uri = uri.replace(LDAPS_PREFIX, LDAP_PREFIX)

    adcm = client.adcm()
    adcm.config_set_diff(
        {
            "attr": {"ldap_integration": {"active": True}},
            "config": {
                "ldap_integration": {
                    "ldap_uri": uri,
                    "ldap_user": config.admin_dn,
                    "ldap_password": config.admin_pass,
                    "user_search_base": user_base,
                    "group_search_base": group_base,
                    **ssl_extra_config,
                    **extra_config,
                }
            },
        },
        attach_to_allure=False,
    )


@allure.step("Run ldap sync")
def sync_adcm_with_ldap(client: ADCMClient) -> None:
    """method to run ldap sync"""
    action = client.adcm().action(name="run_ldap_sync")
    wait_for_task_and_assert_result(action.run(), "success")


def change_adcm_ldap_config(client: ADCMClient, attach_to_allure: bool = False, **params) -> None:
    """method to change adcm ldap config"""
    client.adcm().config_set_diff({"ldap_integration": params}, attach_to_allure=attach_to_allure)
