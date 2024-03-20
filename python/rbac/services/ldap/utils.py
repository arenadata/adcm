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


from cm.adcm_config.ansible import ansible_decrypt
from cm.services.adcm import adcm_config, get_adcm_config_id

from rbac.services.ldap.errors import LDAPConfigurationError
from rbac.services.ldap.types import ConnectionSettings, GroupSettings, LDAPAttributes, LDAPSettings, UserSettings


def str_join_attr_list(ldap_attributes: LDAPAttributes, target_attr: str, sort: bool = True) -> str:
    values = ldap_attributes.get(target_attr, [])
    if not isinstance(values, list):
        values = [values]

    if sort:
        values = sorted(values)

    return " ".join(values)


def get_ldap_settings() -> LDAPSettings:
    adcm_config_attr = adcm_config(config_id=get_adcm_config_id())

    if not adcm_config_attr.attr["ldap_integration"]["active"]:
        raise LDAPConfigurationError("LDAP integration is disabled")

    ldap_config = adcm_config_attr.config["ldap_integration"]
    ldap_config["ldap_password"] = ansible_decrypt(msg=ldap_config["ldap_password"])
    ldap_config["group_dn_adcm_admin"] = [group_dn.lower() for group_dn in ldap_config["group_dn_adcm_admin"] or []]

    tls_enabled = "ldaps://" in ldap_config["ldap_uri"].lower()
    user_attr_map = {
        "username": ldap_config["user_name_attribute"],
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    }

    return LDAPSettings(
        connection=ConnectionSettings(**ldap_config, tls_enabled=tls_enabled),
        user=UserSettings(**ldap_config, attr_map=user_attr_map),
        group=GroupSettings(**ldap_config),
        **ldap_config,
    )
