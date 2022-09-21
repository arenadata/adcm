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
Test audit operations with "operation_type == DELETE"
"""

from typing import Tuple

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import Bundle, Cluster, Group, Host, Policy, Provider, Role, User

from tests.functional.audit.checks import check_audit_cef_logs
from tests.functional.audit.conftest import BUNDLES_DIR, NEW_USER
from tests.functional.audit.conftest import CreateDeleteOperation as Delete
from tests.functional.audit.conftest import check_failed, check_succeed
from tests.functional.rbac.conftest import BusinessRoles as BR
from tests.functional.rbac.conftest import create_policy
from tests.library.audit.checkers import AuditLogChecker

# pylint: disable=redefined-outer-name


@pytest.fixture()
def bundles(sdk_client_fs) -> Tuple[Bundle, Bundle]:
    """Upload two bundles: cluster and provider"""
    return (
        sdk_client_fs.upload_from_fs(BUNDLES_DIR / "create" / "cluster"),
        sdk_client_fs.upload_from_fs(BUNDLES_DIR / "create" / "provider"),
    )


@pytest.fixture()
def adcm_objects(bundles) -> Tuple[Cluster, Provider, Host, Host]:
    """
    Create ADCM objects: cluster, provider, two hosts
    Add service to cluster
    Create group config on each cluster object
    """
    cluster = bundles[0].cluster_create("cluster")
    provider = bundles[1].provider_create("provider")
    host_1 = provider.host_create("host-1")
    host_2 = provider.host_create("host-2")
    service = cluster.service_add(name="service")
    for obj in cluster, service, service.component():
        obj.group_config_create(f"{obj.__class__.__name__.lower()}-group")
    return cluster, provider, host_1, host_2


@pytest.fixture()
def rbac_objects(sdk_client_fs, rbac_create_data) -> Tuple[User, Group, Role, Policy]:
    """Create RBAC objects (user may be taken, if already created)"""
    policy_data = {**rbac_create_data["policy"]}
    try:
        user = sdk_client_fs.user(username=NEW_USER["username"])
    except ObjectNotFound:
        user = sdk_client_fs.user_create(**NEW_USER)
    return (
        user,
        sdk_client_fs.group_create(**rbac_create_data["group"]),
        sdk_client_fs.role_create(**rbac_create_data["role"]),
        sdk_client_fs.policy_create(
            policy_data["name"],
            sdk_client_fs.role(id=policy_data["role"]["id"]),
            [sdk_client_fs.user(id=sdk_client_fs.me().id)],
        ),
    )


@pytest.fixture()
def grant_view_config_permissions_on_adcm_objects(sdk_client_fs, adcm_objects, new_user_client):
    """Create policies that allow new user to get ADCM objects (via View Configuration)"""
    cluster, provider, host_1, host_2 = adcm_objects
    user = sdk_client_fs.user(id=new_user_client.me().id)
    create_policy(
        sdk_client_fs,
        [BR.ViewClusterConfigurations, BR.ViewServiceConfigurations, BR.ViewComponentConfigurations],
        [cluster, (s := cluster.service()), s.component()],
        users=[user],
        groups=[],
        use_all_objects=True,
    )
    create_policy(
        sdk_client_fs,
        [BR.ViewProviderConfigurations, BR.ViewHostConfigurations],
        [provider, host_1, host_2],
        users=[user],
        groups=[],
        use_all_objects=True,
    )


@pytest.mark.parametrize('parse_with_context', ['delete_objects.yaml'], indirect=True)
@pytest.mark.usefixtures(
    "grant_view_config_permissions_on_adcm_objects"
)  # pylint: disable-next=too-many-locals,too-many-arguments
def test_delete(
    parse_with_context,
    sdk_client_fs,
    delete,
    new_user_client,
    unauthorized_creds,
    rbac_objects,
    bundles,
    adcm_objects,
    adcm_fs,
):
    """Test audit DELETE operations of: ADCM objects, group configs and RBAC objects"""
    context = {"username": new_user_client.me().username}
    cluster, provider, host_1, host_2 = adcm_objects
    from_provider = (Delete.HOST_FROM_PROVIDER, host_2.id)
    provider_path_fmt = {"path_fmt": {"provider_id": provider.id}}
    cluster.host_add(host_1)
    cluster.host_add(host_2)
    component = (service := cluster.service()).component()

    with allure.step("Try to delete objects as an unauthorized user"):
        for obj in (cluster, provider, host_1, *bundles, *rbac_objects):
            endpoint = _get_endpoint_by_object(obj)
            check_failed(delete(endpoint, obj.id, headers=unauthorized_creds), 403)
        check_failed(delete(*from_provider, **provider_path_fmt, headers=unauthorized_creds), 403)
        for group_config in (o.group_config()[0] for o in (cluster, service, component)):
            check_failed(delete(Delete.GROUP_CONFIG, group_config.id, headers=unauthorized_creds), 403)
    with allure.step("Fail to delete objects"):
        for obj in (provider, host_1, *bundles):
            endpoint = _get_endpoint_by_object(obj)
            check_failed(delete(endpoint, obj.id), 409)
        check_failed(delete(*from_provider, **provider_path_fmt), 409)
        role = sdk_client_fs.role(built_in=True)
        context["built_in_role"] = role.name
        check_failed(delete(Delete.ROLE, role.id), 405)
    audit_checker = AuditLogChecker(parse_with_context(context))
    audit_checker.set_user_map(sdk_client_fs)
    with allure.step("Delete objects"):
        for group_config in (obj.group_config()[0] for obj in (cluster, service, component)):
            check_succeed(delete(Delete.GROUP_CONFIG, group_config.id))
        check_succeed(delete(Delete.CLUSTER, cluster.id))
        check_succeed(delete(*from_provider, **provider_path_fmt))
        for obj in (host_1, provider, *bundles, *rbac_objects):
            endpoint = _get_endpoint_by_object(obj)
            check_succeed(delete(endpoint, obj.id))
    audit_checker.check(sdk_client_fs.audit_operation_list(paging={"limit": 300}))
    check_audit_cef_logs(sdk_client_fs, adcm_fs.container)


def _get_endpoint_by_object(obj) -> str:
    return getattr(Delete, obj.__class__.__name__.upper())
