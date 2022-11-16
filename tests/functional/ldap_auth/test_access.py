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

"""
Test granting RBAC access to "users from LDAP"
"""

from typing import Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, User
from adcm_pytest_plugin.utils import random_string
from tests.functional.conftest import only_clean_adcm
from tests.functional.ldap_auth.conftest import BASE_BUNDLES_DIR
from tests.functional.ldap_auth.utils import (
    get_ldap_group_from_adcm,
    get_ldap_user_from_adcm,
)
from tests.functional.rbac.conftest import (
    BusinessRoles,
    create_policy,
    delete_policy,
    is_allowed,
    is_denied,
)

pytestmark = [only_clean_adcm, pytest.mark.usefixtures('configure_adcm_ldap_ad'), pytest.mark.ldap()]


# pylint: disable=redefined-outer-name


@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    """Create cluster"""
    bundle = sdk_client_fs.upload_from_fs(BASE_BUNDLES_DIR / 'cluster')
    return bundle.cluster_create('Test Cluster')


def test_grant_policy_for_ldap_user(sdk_client_fs, cluster, ldap_user_in_group):
    """
    Test that granting policy for LDAP user in ADCM works the same way as with regular user.
    """
    username, password = ldap_user_in_group['name'], ldap_user_in_group['password']

    user_client, user = _login_as_ldap_user_and_check_no_access(sdk_client_fs, username, password, cluster)

    with allure.step('Grant access for a cluster and check it is granted'):
        policy = create_policy(sdk_client_fs, BusinessRoles.EditClusterConfigurations, [cluster], [user], [])
        user_client.reread()
        user_cluster = is_allowed(user_client, BusinessRoles.GetCluster, id=cluster.id)
        is_allowed(user_cluster, BusinessRoles.EditClusterConfigurations)

    with allure.step('Withdraw policy from LDAP user'):
        delete_policy(policy)
        is_denied(user_client, BusinessRoles.GetCluster, id=cluster.id)
        is_denied(user_cluster, BusinessRoles.EditClusterConfigurations, client=user_client)


# pylint: disable-next=unused-variable,too-many-arguments,too-many-locals
def test_grant_policy_for_ldap_group(sdk_client_fs, cluster, ldap_ad, ldap_basic_ous, ldap_group, ldap_user_in_group):
    """
    Test that granting policy for LDAP group in ADCM works the same way as with regular group.
    """
    _, users_ou = ldap_basic_ous
    username, password = ldap_user_in_group['name'], ldap_user_in_group['password']
    second_username, second_password = f'Newcomer_{random_string(6)}', random_string(12)

    user_client, _ = _login_as_ldap_user_and_check_no_access(sdk_client_fs, username, password, cluster)

    with allure.step('Grant access to group from LDAP and check permissions of existing users'):
        group = get_ldap_group_from_adcm(sdk_client_fs, ldap_group['name'])
        policy = create_policy(sdk_client_fs, BusinessRoles.EditClusterConfigurations, [cluster], [], [group])
        user_client.reread()
        user_cluster = is_allowed(user_client, BusinessRoles.GetCluster, id=cluster.id)
        is_allowed(user_cluster, BusinessRoles.EditClusterConfigurations)

    with allure.step('Create new LDAP user in group and check they will have permissions'):
        new_user_dn = ldap_ad.create_user(second_username, second_password, custom_base_dn=users_ou)
        ldap_ad.add_user_to_group(new_user_dn, ldap_group['dn'])
        second_user_client = ADCMClient(url=sdk_client_fs.url, user=second_username, password=second_password)
        second_user_cluster = is_allowed(second_user_client, BusinessRoles.GetCluster, id=cluster.id)
        is_allowed(second_user_cluster, BusinessRoles.EditClusterConfigurations)

    with allure.step('Withdraw policy from LDAP group and check users have no permissions'):
        delete_policy(policy)
        is_denied(user_client, BusinessRoles.GetCluster, id=cluster.id)
        is_denied(user_cluster, BusinessRoles.EditClusterConfigurations, client=user_client)
        is_denied(second_user_client, BusinessRoles.GetCluster, id=cluster.id)
        is_denied(second_user_cluster, BusinessRoles.EditClusterConfigurations, client=second_user_client)


def _login_as_ldap_user_and_check_no_access(client, username, password, cluster) -> Tuple[ADCMClient, User]:
    """:returns: New ADCM Client connection (logged as new user) and user (from admin perspective)"""
    with allure.step('Login as LDAP user and check user is created'):
        user_sdk = ADCMClient(url=client.url, user=username, password=password)
        user = get_ldap_user_from_adcm(client, username)

    with allure.step('Check no access'):
        is_denied(user_sdk, BusinessRoles.GetCluster, id=cluster.id)

    return user_sdk, user
