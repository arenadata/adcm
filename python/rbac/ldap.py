import os

import ldap
from django.core.exceptions import ImproperlyConfigured
from django_auth_ldap.backend import LDAPBackend
from django_auth_ldap.config import LDAPSearch, MemberDNGroupType

from cm.adcm_config import ansible_decrypt
from cm.logger import log
from cm.models import ADCM, ConfigLog
from rbac.models import User, Group


CERT_ENV_KEY = 'LDAPTLS_CACERT'


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
            if not any(
                [
                    cert_filepath,
                    os.path.exists(cert_filepath),
                ]
            ):
                raise ImproperlyConfigured('no cert file')

            connection_options = {
                ldap.OPT_X_TLS_CACERTFILE: cert_filepath,
                ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_ALLOW,
                ldap.OPT_X_TLS_NEWCTX: 0,
            }
            default_settings.update({'CONNECTION_OPTIONS': connection_options})
            os.environ['CERT_ENV_KEY'] = cert_filepath

        return default_settings

    return {}


class CustomLDAPBackend(LDAPBackend):
    def authenticate_ldap_user(self, ldap_user, password):
        self.default_settings = _get_ldap_default_settings()

        try:
            user_or_none = super().authenticate_ldap_user(ldap_user, password)
        except ImproperlyConfigured as e:
            log.exception(e)
            user_or_none = None
        if isinstance(user_or_none, User):
            self.__create_rbac_groups(user_or_none)
        return user_or_none

    def get_user_model(self):
        return User

    @staticmethod
    def __create_rbac_groups(user):
        description = 'LDAP group'
        for group in user.groups.all():
            count = Group.objects.filter(group_ptr_id=group.pk, description=description).count()
            if count < 1:
                name = group.name
                Group.objects.create(group_ptr_id=group.pk, description=description)
                group.name = name
                group.save()
            elif count > 1:
                raise RuntimeError(f'More than one `#{group.pk} {description}` groups exist')
