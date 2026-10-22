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

from cm.legacy.services.adcm import adcm_config_attr
from cm.models import ADCM, ConfigLog
from cm.transition.ansible import ansible_encrypt_and_format
from tests.suites import GenericTestCase

from rbac.services.ldap import get_ldap_settings
from rbac.services.ldap.errors import LDAPConfigurationError


class TestGetLDAPSettings(GenericTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls._initialize_roles_and_adcm()

    def setUp(self) -> None:
        super().setUp()

        adcm_config_attr.cache_clear()

    def test_disabled_integration_raises(self) -> None:
        with self.assertRaisesRegex(LDAPConfigurationError, "LDAP integration is disabled"):
            get_ldap_settings()

    def test_settings_are_read_from_config(self) -> None:
        self._enable_ldap_integration(
            ldap_config={
                "ldap_uri": "ldap://openldap:389",
                "ldap_user": "cn=admin,dc=example,dc=org",
                "ldap_password": ansible_encrypt_and_format(msg="secret"),
                "user_search_base": "ou=users,dc=example,dc=org",
                "user_object_class": "inetOrgPerson",
                "user_name_attribute": "uid",
                "group_search_base": "ou=groups,dc=example,dc=org",
                "group_object_class": "groupOfUniqueNames",
                "group_name_attribute": "cn",
                "group_member_attribute_name": "uniqueMember",
                "group_dn_adcm_admin": ["CN=adcm_admins,OU=groups,DC=example,DC=org"],
                "sync_interval": 30,
            }
        )

        settings = get_ldap_settings()

        self.assertEqual(settings.connection.uri, "ldap://openldap:389")
        self.assertEqual(settings.connection.bind_dn, "cn=admin,dc=example,dc=org")
        self.assertEqual(settings.connection.bind_password, "secret")
        self.assertFalse(settings.connection.tls_enabled)
        self.assertEqual(settings.user.search_base, "ou=users,dc=example,dc=org")
        self.assertEqual(settings.user.object_class, "inetOrgPerson")
        self.assertEqual(settings.user.name_attribute, "uid")
        self.assertEqual(settings.user.attr_map["username"], "uid")
        self.assertEqual(settings.user.group_dn_adcm_admin, ["cn=adcm_admins,ou=groups,dc=example,dc=org"])
        self.assertEqual(settings.group.search_base, "ou=groups,dc=example,dc=org")
        self.assertEqual(settings.group.object_class, "groupOfUniqueNames")
        self.assertEqual(settings.group.member_attribute_name, "uniqueMember")
        self.assertEqual(settings.sync_interval, 30)

    def test_ldaps_uri_enables_tls(self) -> None:
        self._enable_ldap_integration(
            ldap_config={"ldap_uri": "LDAPS://openldap:636", "ldap_password": ansible_encrypt_and_format(msg="secret")}
        )

        self.assertTrue(get_ldap_settings().connection.tls_enabled)

    def _enable_ldap_integration(self, ldap_config: dict) -> None:
        config_log = ConfigLog.objects.get(id=ADCM.objects.values_list("config__current", flat=True).get())
        config_log.config["ldap_integration"] |= {
            "ldap_user": "cn=admin,dc=example,dc=org",
            "user_search_base": "ou=users,dc=example,dc=org",
        } | ldap_config
        config_log.attr["ldap_integration"]["active"] = True
        config_log.save(update_fields=["config", "attr"])

        adcm_config_attr.cache_clear()
