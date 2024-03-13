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

from contextlib import contextmanager
import os

import ldap

from rbac.services.ldap.errors import LDAPConnectionError
from rbac.services.ldap.types import ConnectionSettings

CERT_ENV_KEY = "LDAPTLS_CACERT"


@contextmanager
def get_connection(settings: ConnectionSettings) -> ldap.ldapobject.LDAPObject:
    ldap.set_option(ldap.OPT_REFERRALS, 0)

    connection = ldap.initialize(settings.uri)
    connection.protocol_version = ldap.VERSION3

    if settings.tls_enabled:
        _enable_tls(connection=connection, cert_filepath=settings.tls_ca_cert_file)
    else:
        _disable_tls(connection=connection)

    try:
        connection.simple_bind_s(who=settings.bind_dn, cred=settings.bind_password)
        yield connection
    except ldap.LDAPError as e:
        raise LDAPConnectionError(f"Can't connect to `{settings.uri}` with bind_dn `{settings.bind_dn}`") from e
    finally:
        connection.unbind_s()


def _enable_tls(connection: ldap.ldapobject.LDAPObject, cert_filepath: str) -> None:
    os.environ[CERT_ENV_KEY] = cert_filepath
    connection.set_option(ldap.OPT_X_TLS_CACERTFILE, cert_filepath)
    connection.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)
    connection.set_option(ldap.OPT_X_TLS_NEWCTX, 0)


def _disable_tls(connection: ldap.ldapobject.LDAPObject) -> None:
    os.environ.pop(CERT_ENV_KEY, None)
    connection.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
