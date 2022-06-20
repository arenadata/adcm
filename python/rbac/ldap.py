import os

import ldap
from django.core.exceptions import ImproperlyConfigured
from django_auth_ldap.backend import LDAPBackend
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

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

        default_settings = {
            'SERVER_URI': ldap_config['ldap_uri'],
            'BIND_DN': ldap_config['ldap_user'],
            'BIND_PASSWORD': ldap_config['ldap_password'],
            'USER_SEARCH': LDAPSearch(
                base_dn=ldap_config['user_search_base'],
                scope=ldap.SCOPE_SUBTREE,
                # filterstr=f'(objectClass={ldap_config.get("user_object_class", "*")})',
                filterstr=f'{ldap_config["user_name_attribute"]}=%(user)s',
            ),
            'GROUP_SEARCH': LDAPSearch(
                base_dn=ldap_config['group_search_base'],
                scope=ldap.SCOPE_SUBTREE,
                filterstr=f'(objectClass={ldap_config.get("group_object_class", "*")})',
            ),
            'USER_FLAGS_BY_GROUP': {
                'is_active': ldap_config['group_search_base'],
            },
            'GROUP_TYPE': GroupOfNamesType(name_attr=ldap_config['group_name_attribute']),
            'USER_ATTR_MAP': {
                "first_name": ldap_config['user_name_attribute'],
                "last_name": "sn",
                "email": "mail",
            },
            'MIRROR_GROUPS': True,
            'ALWAYS_UPDATE_USER': True,
            'FIND_GROUP_PERMS': True,
            'CACHE_TIMEOUT': 3600,
        }

        if 'ldaps://' in ldap_config['ldap_uri'].lower():
            if not any(
                [
                    ldap_config.get('tls_ca_cert_file', None),
                    os.path.exists(ldap_config['tls_ca_cert_file']),
                ]
            ):
                raise ImproperlyConfigured('no cert file')

            default_settings.update(
                {
                    'CONNECTION_OPTIONS': {
                        ldap.OPT_X_TLS_CACERTFILE: ldap_config['tls_ca_cert_file'],
                        ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_ALLOW,
                        ldap.OPT_X_TLS_NEWCTX: 0,
                    }
                }
            )
            os.environ['CERT_ENV_KEY'] = ldap_config['tls_ca_cert_file']

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
