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

"""Test relations between LDAP objects """
from typing import Collection, Tuple, Union

import allure
import pytest
from adcm_client.objects import ADCMClient
from tests.api.utils.tools import random_string
from tests.functional.conftest import only_clean_adcm
from tests.functional.ldap_auth.utils import (
    get_ldap_group_from_adcm,
    get_ldap_user_from_adcm,
)
from tests.library.ldap_interactions import LDAPEntityManager

pytestmark = [only_clean_adcm, pytest.mark.usefixtures('configure_adcm_ldap_ad'), pytest.mark.ldap()]


# pylint: disable-next=too-few-public-methods
class TestLDAPEntitiesRelationsInADCM:
    """Test that relations from LDAP are correctly integrated to ADCM"""

    ldap: LDAPEntityManager
    groups_ou_dn: str
    users_ou_dn: str

    pytestmark = [pytest.mark.usefixtures('_bind_ldap_related_values')]

    @pytest.fixture()
    def _bind_ldap_related_values(self, ldap_ad, ldap_basic_ous):
        self.ldap = ldap_ad
        groups_ou, users_ou = ldap_basic_ous
        self.groups_ou_dn = groups_ou
        self.users_ou_dn = users_ou

    def test_user_group_relations(self, sdk_client_fs):
        """
        Test that users and groups from LDAP are correctly related in ADCM.
        """
        groups_at_start = len(sdk_client_fs.group_list())
        # pylint: disable=unbalanced-tuple-unpacking
        user_1, user_2 = self._create_users('first-user', 'second-user')
        group_1, group_2, _ = self._create_groups('first-group', 'second-group', 'empty-group')
        # pylint: enable=unbalanced-tuple-unpacking
        self._add_users_to_groups((group_1, (user_1, user_2)), (group_2, [user_1]))
        self._login_as_users(sdk_client_fs, user_2)
        with allure.step('Check that correct group is retrieved from LDAP and it has correct user'):
            expected_groups_amount = groups_at_start + 1
            assert len(sdk_client_fs.group_list()) == expected_groups_amount, 'More than one group were created'
            self._check_user_is_in_group(sdk_client_fs, user_2, group_1)
        self._login_as_users(sdk_client_fs, user_1)
        with allure.step('Check that one more group is retrieved from LDAP and group users are correct'):
            expected_groups_amount += 1
            assert len(sdk_client_fs.group_list()) == expected_groups_amount, 'More than one group were created'
            self._check_user_is_in_group(sdk_client_fs, user_1, group_1)
            self._check_user_is_in_group(sdk_client_fs, user_2, group_1)
            self._check_user_is_in_group(sdk_client_fs, user_1, group_2)
            self._check_user_is_not_in_group(sdk_client_fs, user_2, group_2)

    def _create_users(self, *user_names: str, randomize: bool = True) -> Tuple[dict, ...]:
        created = []
        for name in user_names if not randomize else map(lambda name: f'{name}-{random_string(4)}', user_names):
            password = random_string(12)
            user_dn = self.ldap.create_user(name, password, custom_base_dn=self.users_ou_dn)
            created.append({'dn': user_dn, 'name': name, 'password': password})
        return tuple(created)

    def _create_groups(self, *group_names: str) -> Tuple[dict, ...]:
        created = []
        for name in group_names:
            group_dn = self.ldap.create_group(name, custom_base_dn=self.groups_ou_dn)
            created.append({'dn': group_dn, 'name': name})
        return tuple(created)

    def _add_users_to_groups(self, *group_users: Tuple[dict, Collection[dict]]):
        for group, users in group_users:
            with allure.step(f'Adding to group {group["name"]} users: {", ".join(u["name"] for u in users)}'):
                for user in users:
                    self.ldap.add_user_to_group(user['dn'], group['dn'])

    @allure.step('Check that user {user} is in group {group}')
    def _check_user_is_in_group(self, client: ADCMClient, user: Union[str, dict], group: Union[str, dict]):
        """Check if user is in group in ADCM"""
        adcm_user = get_ldap_user_from_adcm(client, user['name'] if isinstance(user, dict) else user)
        adcm_group = get_ldap_group_from_adcm(client, group['name'] if isinstance(group, dict) else group)
        assert adcm_user.id in [
            u.id for u in adcm_group.user_list()
        ], f'User {adcm_user.username} not found in group {adcm_group.name}'

    @allure.step('Check that user {user} is not in group {group}')
    def _check_user_is_not_in_group(self, client: ADCMClient, user: Union[str, dict], group: Union[str, dict]):
        adcm_user = get_ldap_user_from_adcm(client, user['name'] if isinstance(user, dict) else user)
        adcm_group = get_ldap_group_from_adcm(client, group['name'] if isinstance(group, dict) else group)
        assert adcm_user.id not in [
            u.id for u in adcm_group.user_list()
        ], f'User {adcm_user.username} should not be presented in group {adcm_group.name}'

    def _login_as_users(self, client: ADCMClient, *users: dict):
        for user in users:
            with allure.step(f'Login as LDAP user {user["name"]} to ADCM'):
                ADCMClient(url=client.url, user=user['name'], password=user['password'])
