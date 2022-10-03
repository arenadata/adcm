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

"""Test "generic" user manipulation scenarios"""

from typing import Tuple

import allure
import pytest
import requests
from adcm_client.audit import ObjectType
from adcm_client.objects import ADCMClient, Group, User
from adcm_pytest_plugin.docker_utils import ADCM
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from docker.models.containers import Container

from tests.functional.audit.conftest import make_auth_header
from tests.functional.conftest import only_clean_adcm
from tests.functional.ldap_auth.utils import get_ldap_user_from_adcm, login_should_fail, login_should_succeed
from tests.functional.tools import check_user_is_active, check_user_is_deactivated, run_ldap_sync
from tests.library.ldap_interactions import LDAPEntityManager

# pylint: disable=redefined-outer-name

DN = str
Username = str


@pytest.fixture()
def adcm_user(sdk_client_fs) -> User:
    """Create ADCM user"""
    username = "adcm_user"
    return sdk_client_fs.user_create(username, username)


@pytest.fixture()
def adcm_group(sdk_client_fs) -> Group:
    """Create group in ADCM"""
    return sdk_client_fs.group_create("justagroup")


@pytest.fixture()
def created_ldap_user(ldap_ad, ldap_basic_ous) -> Tuple[DN, Username]:
    """Create LDAP user in AD and return its DN and username"""
    username = "ldap_user"
    _, users_ou = ldap_basic_ous
    dn = ldap_ad.create_user(username, username, users_ou)
    return dn, username


@pytest.fixture()
def ldap_user(sdk_client_fs, created_ldap_user, configure_adcm_ldap_ad) -> User:
    """Login as LDAP user and return it as ADCM user"""
    _ = configure_adcm_ldap_ad
    sdk_client_fs.adcm().config_set_diff({"ldap_integration": {"group_search_base": None, "sync_interval": 0}})
    _, username = created_ldap_user
    login_should_succeed("login as newly created ldap user", sdk_client_fs, username, username)
    return get_ldap_user_from_adcm(sdk_client_fs, username)


@only_clean_adcm
@pytest.mark.ldap()
@pytest.mark.usefixtures("configure_adcm_ldap_ad")  # pylint: disable-next=too-many-arguments
def test_users_deactivation(
    adcm_user: User,
    ldap_user: User,
    adcm_group: Group,
    created_ldap_user: Tuple[DN, Username],
    adcm_fs: ADCM,
    sdk_client_fs: ADCMClient,
    ldap_ad: LDAPEntityManager,
):
    """Test deactivation of LDAP/ADCM users"""
    ldap_user_dn, _ = created_ldap_user
    for user in (adcm_user, ldap_user):
        add_user_to_group(sdk_client_fs, user, adcm_group)
        _check_user_appeared_in_audit(sdk_client_fs, user)
    deactivate_users(ldap_ad, ldap_user_dn, adcm_user)
    check_user_is_deactivated(adcm_user)
    login_should_fail("login as ldap user", sdk_client_fs, ldap_user.username, ldap_user.username)
    check_user_is_active(ldap_user)
    wait_for_task_and_assert_result(run_ldap_sync(sdk_client_fs), "success")
    check_user_is_deactivated(ldap_user)
    _check_none_of_audit_objects_is_deleted(adcm_fs.container)


def add_user_to_group(client: ADCMClient, user: User, group: Group) -> None:
    """Add user to group via API call to user endpoint"""
    with allure.step(f"Add user {user.username} to {group.name}"):
        response = requests.patch(
            f"{client.url}/api/v1/rbac/user/{user.id}/",
            json={"group": [{"id": group.id}]},
            headers=make_auth_header(client),
        )
        assert response.status_code == 200, "Failed to add user to group"


@allure.step("Deactivate users")
def deactivate_users(ldap_manager: LDAPEntityManager, ldap_user_dn: DN, user_from_adcm: User):
    """Deactivate LDAP user in AD, deactivate ADCM user"""
    user_from_adcm.delete()
    ldap_manager.deactivate_user(ldap_user_dn)


def _check_user_appeared_in_audit(client: ADCMClient, user: User) -> None:
    with allure.step(f"Check that there's a record in audit log about user {user.username}"):
        user_audit_record = next(
            filter(
                lambda operation: operation.object_type == ObjectType.USER and operation.object_name == user.username,
                client.audit_operation_list(),
            ),
            None,
        )
        assert user_audit_record, "No audit record found"


@allure.step("Check none of audit objects is deleted")
def _check_none_of_audit_objects_is_deleted(container: Container) -> None:
    exit_code, output = container.exec_run(
        [
            "sh",
            "-c",
            "source /adcm/venv/default/bin/activate "
            "&& python3 adcm/python/manage.py shell -c "
            "'from audit.models import AuditObject; print(AuditObject.objects.filter(is_deleted=True).count())'",
        ]
    )
    assert exit_code == 0, "docker exec failed"
    output: bytes
    amount_of_deleted = int(output.decode("utf-8").strip())
    assert amount_of_deleted == 0, "Amount of deleted audit objects should be 0"
