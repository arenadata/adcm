import ldap
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
        }
    return {}


class CustomLDAPBackend(LDAPBackend):
    default_settings = _get_ldap_default_settings()

    def get_user_model(self):
        return User
