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

from typing import Mapping, Pattern, TypeAlias
import re

from pydantic import BaseModel, Field

DistinguishedName: TypeAlias = str
LDAPAttributes: TypeAlias = Mapping
LDAPUser: TypeAlias = tuple[DistinguishedName, LDAPAttributes]
LDAPGroup: TypeAlias = tuple[DistinguishedName, LDAPAttributes]


class FrozenBaseModel(BaseModel):
    class Config:
        frozen = True


class ConnectionSettings(FrozenBaseModel):
    uri: str = Field(alias="ldap_uri")
    bind_dn: str = Field(alias="ldap_user")
    bind_password: str = Field(alias="ldap_password")
    tls_enabled: bool
    tls_ca_cert_file: str | None = None


class UserSettings(FrozenBaseModel):
    search_base: str = Field(alias="user_search_base")
    search_filter: str | None = Field(default=None, alias="user_search_filter")
    object_class: str = Field(default="*", alias="user_object_class")
    name_attribute: str = Field(alias="user_name_attribute")
    attr_map: dict[str, str]
    active_attribute: str = "userAccountControl"
    group_membership_attribute: str = "memberOf"
    group_dn_adcm_admin: list[DistinguishedName]


class GroupSettings(FrozenBaseModel):
    search_base: str | None = Field(default=None, alias="group_search_base")
    search_filter: str | None = Field(default=None, alias="group_search_filter")
    object_class: str = Field(alias="group_object_class")
    name_attribute: str = Field(alias="group_name_attribute")
    member_attribute_name: str = Field(alias="group_member_attribute_name")


class LDAPSettings(FrozenBaseModel):
    connection: ConnectionSettings
    user: UserSettings
    group: GroupSettings
    sync_interval: int
    dn_attribute: str = "distinguishedName"
    cn_pattern: Pattern = re.compile("CN=(?P<common_name>.*?)[,$]", re.IGNORECASE)


class LDAPUserAttrs(FrozenBaseModel):
    username: str
    first_name: str
    last_name: str
    email: str
    groups: list[DistinguishedName]
    is_active: bool
    is_superuser: bool
