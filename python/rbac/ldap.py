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
from contextlib import contextmanager, suppress

import ldap
from django.contrib.auth.models import Group as DjangoGroup
from django.db.transaction import atomic
from django_auth_ldap.backend import LDAPBackend
from django_auth_ldap.config import LDAPSearch, MemberDNGroupType

from cm.adcm_config import ansible_decrypt
from cm.logger import logger
from cm.models import ADCM, ConfigLog
from rbac.models import Group, OriginType, User

CERT_ENV_KEY = 'LDAPTLS_CACERT'


def _process_extra_filter(filterstr: str) -> str:
    filterstr = filterstr or ''
    if filterstr == '':
        return filterstr

    # simple single filter ex: `primaryGroupID=513`
    if '(' not in filterstr and ')' not in filterstr:
        return f'({filterstr})'
    else:
        # assume that composed filter is syntactically valid
        return filterstr


def configure_tls(enabled, cert_filepath='', conn=None):
    os.environ.pop(CERT_ENV_KEY, None)
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    if not enabled:
        return None

    if cert_filepath:
        os.environ[CERT_ENV_KEY] = cert_filepath

    opts = {
        ldap.OPT_X_TLS_CACERTFILE: cert_filepath,
        ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_ALLOW,
        ldap.OPT_X_TLS_NEWCTX: 0,
    }

    if not conn:
        return opts

    for opt_key, opt_val in opts.items():
        conn.set_option(opt_key, opt_val)
    return None


def is_tls(ldap_uri):
    if 'ldaps://' in ldap_uri.lower():
        return True
    return False


def _get_ldap_default_settings():
    configure_tls(enabled=False)

    adcm_object = ADCM.objects.get(id=1)
    current_configlog = ConfigLog.objects.get(
        obj_ref=adcm_object.config, id=adcm_object.config.current
    )

    if current_configlog.attr['ldap_integration']['active']:
        ldap_config = current_configlog.config['ldap_integration']

        user_search = LDAPSearch(
            base_dn=ldap_config['user_search_base'],
            scope=ldap.SCOPE_SUBTREE,
            filterstr=f'(&'
            f'(objectClass={ldap_config.get("user_object_class") or "*"})'
            f'({ldap_config["user_name_attribute"]}=%(user)s)'
            f'{_process_extra_filter(ldap_config.get("user_search_filter"))}'
            f')',
        )
        group_search = LDAPSearch(
            base_dn=ldap_config['group_search_base'],
            scope=ldap.SCOPE_SUBTREE,
            filterstr=f'(objectClass={ldap_config.get("group_object_class") or "*"})'
            f'{_process_extra_filter(ldap_config.get("group_search_filter"))}',
        )
        user_attr_map = {
            "username": ldap_config["user_name_attribute"],
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
            'USER_OBJECT_CLASS': ldap_config.get("user_object_class", "*"),
            'USER_FILTER': _process_extra_filter(ldap_config.get("user_search_filter", '')),
            'GROUP_SEARCH': group_search,
            'GROUP_TYPE': group_type,
            'GROUP_FILTER': _process_extra_filter(ldap_config.get("group_search_filter", '')),
            'GROUP_OBJECT_CLASS': ldap_config.get("group_object_class", "*"),
            'USER_ATTR_MAP': user_attr_map,
            'MIRROR_GROUPS': True,
            'ALWAYS_UPDATE_USER': True,
            'FIND_GROUP_PERMS': True,
            'CACHE_TIMEOUT': 3600,
        }

        if is_tls(ldap_config['ldap_uri']):
            cert_filepath = ldap_config.get('tls_ca_cert_file', '')
            if not cert_filepath or not os.path.exists(cert_filepath):
                msg = 'NO_CERT_FILE'
                logger.warning(msg)
                return {}, msg
            connection_options = configure_tls(enabled=True, cert_filepath=cert_filepath)
            default_settings.update({'CONNECTION_OPTIONS': connection_options})

        return default_settings, None

    return {}, 'NO_LDAP_SETTINGS'


class CustomLDAPBackend(LDAPBackend):
    def __init__(self):
        self.default_settings = {}
        self.is_tls = False

    def authenticate_ldap_user(self, ldap_user, password):
        self.default_settings, _ = _get_ldap_default_settings()
        if not self.default_settings:
            return None
        self.is_tls = is_tls(self.default_settings['SERVER_URI'])

        try:
            if not self.__check_user(ldap_user):
                return None
            # pylint: disable=protected-access
            user_local_groups = self.__get_local_groups_by_username(ldap_user._username)
            user_or_none = super().authenticate_ldap_user(ldap_user, password)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(e)
            return None

        if isinstance(user_or_none, User):
            user_or_none.type = OriginType.LDAP
            user_or_none.save()
            self.__process_groups(user_or_none, user_local_groups)

        return user_or_none

    @staticmethod
    def __get_local_groups_by_username(username):
        groups = []
        with suppress(User.DoesNotExist):
            user = User.objects.get(username__iexact=username, type=OriginType.LDAP)
            groups = [g.group for g in user.groups.all() if g.group.type == OriginType.Local]
        return groups

    def get_user_model(self):
        return User

    @contextmanager
    def __ldap_connection(self):
        ldap.set_option(ldap.OPT_REFERRALS, 0)
        conn = ldap.initialize(self.default_settings['SERVER_URI'])
        conn.protocol_version = ldap.VERSION3
        configure_tls(self.is_tls, os.environ.get(CERT_ENV_KEY, ''), conn)
        conn.simple_bind_s(self.default_settings['BIND_DN'], self.default_settings['BIND_PASSWORD'])
        try:
            yield conn
        finally:
            conn.unbind_s()

    def __get_groups_by_group_search(self):
        with self.__ldap_connection() as conn:
            groups = self.default_settings['GROUP_SEARCH'].execute(conn)
        logger.debug('Found %s groups: %s', len(groups), [i[0] for i in groups])
        return groups

    def __process_groups(self, user, additional_groups=()):
        ldap_groups = list(zip(user.ldap_user.group_names, user.ldap_user.group_dns))

        # ladp-backend managed auth_groups
        for group in user.groups.filter(name__in=[i[0] for i in ldap_groups]):
            ldap_group_dn = self.__get_ldap_group_dn(group.name, ldap_groups)
            rbac_group = self.__get_rbac_group(group, ldap_group_dn)
            group.user_set.remove(user)
            rbac_group.user_set.add(user)
            if group.user_set.count() == 0:
                group.delete()
        for g in additional_groups:
            g.user_set.add(user)

    def __check_user(self, ldap_user):
        user_dn = ldap_user.dn
        username = ldap_user._username  # pylint: disable=protected-access

        if User.objects.filter(username__iexact=username, type=OriginType.Local).exists():
            logger.exception('usernames collision: `%s`', username)
            return False

        group_member_attr = self.default_settings['GROUP_TYPE'].member_attr
        for _, group_attrs in self.__get_groups_by_group_search():
            if user_dn.lower() in [i.lower() for i in group_attrs.get(group_member_attr, [])]:
                break
        else:
            return False

        return True

    @staticmethod
    def __get_ldap_group_dn(group_name: str, ldap_groups: list) -> str:
        group_dn = ''
        with suppress(IndexError):
            group_dn = [i for i in ldap_groups if i[0] == group_name][0][1]
        return group_dn

    @staticmethod
    def __get_rbac_group(group, ldap_group_dn):
        """
        Get corresponding rbac_group for auth_group or create `ldap` type rbac_group if not exists
        """
        if isinstance(group, Group):
            return group
        elif isinstance(group, DjangoGroup):
            try:
                # maybe we'll need more accurate filtering here
                return Group.objects.get(
                    name=f'{group.name} [{OriginType.LDAP.value}]', type=OriginType.LDAP.value
                )
            except Group.DoesNotExist:
                with atomic():
                    rbac_group = Group.objects.create(
                        name=group.name,
                        type=OriginType.LDAP,
                        description=ldap_group_dn,
                    )
                    return rbac_group
        else:
            raise ValueError('wrong group type')
