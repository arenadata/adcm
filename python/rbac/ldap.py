import ldap
from django.core.exceptions import ImproperlyConfigured
from django_auth_ldap.backend import LDAPBackend
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

from cm.models import ADCM, ConfigLog
from rbac.models import User


def _get_ldap_default_settings():
    adcm_object = ADCM.objects.get(id=1)
    current_configlog = ConfigLog.objects.get(
        obj_ref=adcm_object.config, id=adcm_object.config.current
    )

    if current_configlog.attr['ldap_integration']['active']:
        ldap_config = current_configlog.config['ldap_integration']
        return {
            'SERVER_URI': ldap_config['ldap_uri'],
            'BIND_DN': ldap_config['ldap_user'],
            'BIND_PASSWORD': ldap_config['ldap_password'],
            'USER_SEARCH': LDAPSearch(
                base_dn=ldap_config['user_search_base'],
                scope=ldap.SCOPE_SUBTREE,
                filterstr=ldap_config['user_search_filter'],
            ),
            'GROUP_SEARCH': LDAPSearch(
                base_dn=ldap_config['group_search_base'],
                scope=ldap.SCOPE_SUBTREE,
                filterstr=ldap_config['group_search_filter'],
            ),
            'USER_FLAGS_BY_GROUP': {
                'is_active': ldap_config['group_search_base'],
            },
            'GROUP_TYPE': GroupOfNamesType(name_attr="cn"),
            'USER_ATTR_MAP': {
                "first_name": "givenName",
                "last_name": "sn",
                "email": "mail",
            },
            # 'USER_FLAGS_BY_GROUP': {
            #     'is_active': 'cn=Managers,ou=Groups,dc=ad,dc=ranger-test',
            #     'is_staff': 'cn=Analysts, ou=Groups,dc=ad,dc=ranger-test',
            # },
            'ALWAYS_UPDATE_USER': True,
            'FIND_GROUP_PERMS': True,
            'CACHE_TIMEOUT': 3600,
        }
    return {}


class CustomLDAPBackend(LDAPBackend):
    default_settings = _get_ldap_default_settings()

    def authenticate_ldap_user(self, ldap_user, password):
        try:
            user_or_none = super().authenticate_ldap_user(ldap_user, password)
        except ImproperlyConfigured as e:
            user_or_none = None
            # return None  # returns `Forbidden (403) CSRF verification failed. Request aborted.`
        if isinstance(user_or_none, User):
            user_or_none.is_active = True
            user_or_none.save()
        else:
            raise RuntimeError
        return user_or_none

    def get_user_model(self):
        return User
