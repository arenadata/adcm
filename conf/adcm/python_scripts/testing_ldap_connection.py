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
from cm.errors import AdcmEx
from rbac.ldap import configure_tls, get_ldap_default_settings, is_tls

CERT_ENV_KEY = "LDAPTLS_CACERT"


def bind() -> None:
    ldap_config, error_code = get_ldap_default_settings()
    if error_code is not None:
        error = AdcmEx(error_code)
        sys.stdout.write(error.msg)
        raise error
    if ldap_config:
        ldap.set_option(ldap.OPT_REFERRALS, 0)
        ldap_uri = ldap_config["SERVER_URI"]
        try:
            conn = ldap.initialize(ldap_uri)
            conn.protocol_version = ldap.VERSION3
            configure_tls(is_tls(ldap_uri), os.environ.get(CERT_ENV_KEY, ""), conn)
            conn.simple_bind_s(ldap_config["BIND_DN"], ldap_config["BIND_PASSWORD"])
        except ldap.LDAPError as e:
            sys.stdout.write(f"Can't connect to {ldap_uri} with user: {ldap_config['BIND_DN']}. Error: {e}\n")
            raise
        sys.stdout.write(f"Connection successful to {ldap_uri}\n")


if __name__ == "__main__":
    bind()
