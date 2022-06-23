import os
import sys
import ldap

os.environ["PYTHONPATH"] = "/adcm/python/"
sys.path.append(os.path.join(os.getcwd(), '../'))
sys.path.append("/adcm/python/")

import adcm.init_django
from cm.models import ADCM, ConfigLog
from cm.adcm_config import ansible_decrypt


def bind():
    adcm = ADCM.objects.get()
    configlog = ConfigLog.objects.get(
        obj_ref=adcm.config, id=adcm.config.current
    )
    if configlog.attr['ldap_integration']['active']:
        ldap_config = configlog.config['ldap_integration']

        ldap.set_option(ldap.OPT_REFERRALS, 0)
        ldap_URI = ldap_config.get('ldap_uri')
        BASE_USER = ldap_config.get('ldap_user')
        BASE_PASS = ansible_decrypt(ldap_config.get('ldap_password'))
        try:
            l = ldap.initialize(ldap_URI)
            l.protocol_version = ldap.VERSION3
            l.simple_bind_s(BASE_USER, BASE_PASS)
        except ldap.LDAPError as e:
            print(f"Can't connect to {ldap_URI} with user: {BASE_USER} {BASE_PASS}. Error: {e}")
            raise
        print(f"Connection successful to {ldap_URI}")


if __name__ == '__main__':
    bind()
