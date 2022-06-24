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
from enum import Enum

import ldap
from django.contrib.auth.models import User as DjangoUser, Group as DjangoGroup
from django.core.exceptions import ImproperlyConfigured
from django_auth_ldap.backend import LDAPBackend
from django_auth_ldap.config import LDAPSearch, MemberDNGroupType

from cm.adcm_config import ansible_decrypt
from cm.errors import AdcmEx
from cm.logger import log
from cm.models import ADCM, ConfigLog
from rbac.models import User, Group, OriginType


CERT_ENV_KEY = 'LDAPTLS_CACERT'


class _GroupCreationPolicy(Enum):
    CONVERT_TO_LDAP = 'CONVERT_TO_LDAP'
    # ldap group with existing rbac group; only ldap users in this group
    LDAP_NO_ACTION = 'LDAP_NO_ACTION'
    # group has non-ldap users; raise an `group names collision exception`; remove user from group
    RAISE_EXC = 'RAISE_EXC'


class GroupNameCollision(Exception):
    pass


def _get_ldap_default_settings():
    os.environ.pop(CERT_ENV_KEY, None)

    adcm_object = ADCM.objects.get(id=1)
    current_configlog = ConfigLog.objects.get(
        obj_ref=adcm_object.config, id=adcm_object.config.current
    )

    if current_configlog.attr['ldap_integration']['active']:
        ldap_config = current_configlog.config['ldap_integration']

        user_search = LDAPSearch(
            base_dn=ldap_config['user_search_base'],
            scope=ldap.SCOPE_SUBTREE,
            filterstr=f'(&(objectClass={ldap_config.get("user_object_class", "*")})'
            f'({ldap_config["user_name_attribute"]}=%(user)s))',
        )
        group_search = LDAPSearch(
            base_dn=ldap_config['group_search_base'],
            scope=ldap.SCOPE_SUBTREE,
            filterstr=f'(objectClass={ldap_config.get("group_object_class", "*")})',
        )
        user_attr_map = {
            "first_name": 'givenName',
            "last_name": "sn",
            "email": "mail",
        }
        group_type = MemberDNGroupType(
            member_attr=ldap_config['group_member_attribute_name'],
            name_attr=ldap_config['group_name_attribute'],
        )

        default_settings = {
            'SERVER_URI': ldap_config['ldap_uri'],
            'BIND_DN': ldap_config['ldap_user'],
            'BIND_PASSWORD': ansible_decrypt(ldap_config['ldap_password']),
            'USER_SEARCH': user_search,
            'GROUP_SEARCH': group_search,
            'GROUP_TYPE': group_type,
            'USER_ATTR_MAP': user_attr_map,
            'MIRROR_GROUPS': True,
            'ALWAYS_UPDATE_USER': True,
            'FIND_GROUP_PERMS': True,
            'CACHE_TIMEOUT': 3600,
        }

        if 'ldaps://' in ldap_config['ldap_uri'].lower():
            cert_filepath = ldap_config.get('tls_ca_cert_file', '')
            if not cert_filepath or not os.path.exists(cert_filepath):
                raise AdcmEx('LDAP_NO_CERT_FILE')

            connection_options = {
                ldap.OPT_X_TLS_CACERTFILE: cert_filepath,
                ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_ALLOW,
                ldap.OPT_X_TLS_NEWCTX: 0,
            }
            default_settings.update({'CONNECTION_OPTIONS': connection_options})
            os.environ['CERT_ENV_KEY'] = cert_filepath

        return default_settings

    return None


class CustomLDAPBackend(LDAPBackend):
    def authenticate_ldap_user(self, ldap_user, password):
        self.default_settings = _get_ldap_default_settings()

        try:
            user_or_none = super().authenticate_ldap_user(ldap_user, password)
        except ImproperlyConfigured as e:
            log.exception(e)
            user_or_none = None
        except ValueError as e:
            if 'option error' in str(e).lower():
                raise AdcmEx('LDAP_BROKEN_CONFIG')
            raise e
        if isinstance(user_or_none, User):
            user_or_none.type = OriginType.LDAP
            user_or_none.save()
            self.__create_rbac_groups(user_or_none)
        return user_or_none

    def get_user_model(self):
        return User

    def __create_rbac_groups(self, user):
        ldap_groups = list(zip(user.ldap_user.group_names, user.ldap_user.group_dns))
        for group in user.groups.filter(name__in=[i[0] for i in ldap_groups]):
            group_creation_policy = self.__get_group_creation_policy(group)
            if group_creation_policy == _GroupCreationPolicy.LDAP_NO_ACTION:
                # user already added to right group
                pass
            elif group_creation_policy == _GroupCreationPolicy.CONVERT_TO_LDAP:
                rbac_group = self.__get_rbac_group(group)
                rbac_group.type = OriginType.LDAP
                rbac_group.description = self.__det_ldap_group_dn(group.name, ldap_groups)
                rbac_group.save()
            elif group_creation_policy == _GroupCreationPolicy.RAISE_EXC:
                group.user_set.remove(user)
                raise AdcmEx('LDAP_GROUP_NAMES_COLLISION')
            else:
                raise RuntimeError('not all cases covered')

    @staticmethod
    def __det_ldap_group_dn(group_name: str, ldap_groups: list) -> str:
        return [i for i in ldap_groups if i[0] == group_name][0][1]

    def __get_group_creation_policy(self, group):
        group = self.__get_rbac_group(group)
        if group.type == OriginType.LDAP:
            return _GroupCreationPolicy.LDAP_NO_ACTION
        else:
            # groups, created by this backend can't be empty, but just in case
            # empty existing groups will be converted to `ldap` type
            if all(
                [self.__get_rbac_user(u).type == OriginType.LDAP for u in group.user_set.all()]
                or [True]
            ):
                return _GroupCreationPolicy.CONVERT_TO_LDAP
            else:
                return _GroupCreationPolicy.RAISE_EXC

    @staticmethod
    def __get_rbac_user(user):
        if isinstance(user, User):
            return user
        elif isinstance(user, DjangoUser):
            return User.objects.get(user_ptr=user)
        else:
            raise ValueError('wrong user type')

    def __get_rbac_group(self, group):
        if isinstance(group, Group):
            return group
        elif isinstance(group, DjangoGroup):
            try:
                return Group.objects.get(group_ptr=group)
            except Group.DoesNotExist:
                name = group.name
                rbac_group = Group.objects.create(group_ptr_id=group.pk)
                group.name = name
                group.save()
                return rbac_group
        else:
            raise ValueError('wrong group type')
