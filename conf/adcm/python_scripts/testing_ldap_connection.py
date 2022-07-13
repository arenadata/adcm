#!/usr/bin/env python3
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
import sys
import ldap

os.environ["PYTHONPATH"] = "/adcm/python/"
sys.path.append("/adcm/python/")

import adcm.init_django  # pylint: disable=unused-import
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
            sys.stderr.write(f"Can't connect to {ldap_URI} with user: {BASE_USER}. Error: {e}\n")
            raise
        sys.stdout.write(f"Connection successful to {ldap_URI}\n")


if __name__ == '__main__':
    bind()
