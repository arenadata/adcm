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

"""Test policies, roles, permissions created after bundle upload"""

import allure

from tests.functional.rbac.action_role_utils import (
    check_cluster_actions_roles_are_created_correctly,
    check_provider_based_object_action_roles_are_created_correctly,
    check_roles_does_not_have_category,
    check_service_and_components_roles_are_created_correctly,
    get_bundle_prefix_for_role_name,
    get_roles_of_type,
)
from tests.functional.rbac.actions.conftest import ALL_SERVICE_NAMES
from tests.functional.rbac.conftest import RoleType, extract_role_short_info

# !===== Tests ======!


def test_roles_creation_on_cluster_bundle_upload(sdk_client_fs, actions_cluster_bundle):
    """
    1. Upload cluster bundle.
    2. Check for cluster, services and components in bundle that:
        - for each action hidden role was created with correct name;
        - all hidden roles are bonded to corresponding business action role;
        - cluster-level actions business roles are added to Cluster Administrator role;
        - service- and component-level actions business roles are added to Cluster and Service Administrator roles.
    3. Check that all action business roles that were affected by this upload have corresponding category.
    """
    bundle = actions_cluster_bundle
    hidden_role_prefix = get_bundle_prefix_for_role_name(bundle)

    with allure.step("Get info about roles created right after bundle upload"):
        hidden_role_names = {role.name for role in get_roles_of_type(RoleType.HIDDEN, sdk_client_fs)}

    cluster = bundle.cluster_create("Test Cluster")
    check_cluster_actions_roles_are_created_correctly(sdk_client_fs, cluster, hidden_role_names, hidden_role_prefix)
    for service_name in ALL_SERVICE_NAMES:
        check_service_and_components_roles_are_created_correctly(
            sdk_client_fs,
            cluster.service_add(name=service_name),
            hidden_role_names,
            hidden_role_prefix,
        )


def test_roles_creation_on_provider_bundle_upload(sdk_client_fs, actions_provider_bundle):
    """
    1. Upload provider bundle.
    2. Check for provider and host in bundle that:
        - for each action hidden role was created with correct name;
        - all hidden roles are bonded to corresponding business action role.
    3. Check no business role have category equal to provider prototype display name.
    """
    bundle = actions_provider_bundle
    hidden_role_prefix = get_bundle_prefix_for_role_name(bundle)

    with allure.step("Get info about roles created right after bundle upload"):
        hidden_role_names = {role.name for role in get_roles_of_type(RoleType.HIDDEN, sdk_client_fs)}

    check_provider_based_object_action_roles_are_created_correctly(
        bundle.provider_prototype(),
        sdk_client_fs,
        hidden_role_names,
        hidden_role_prefix,
    )

    provider = bundle.provider_create("Test Provider")
    host = provider.host_create(fqdn="test-host")
    check_provider_based_object_action_roles_are_created_correctly(
        host.prototype(),
        sdk_client_fs,
        hidden_role_names,
        hidden_role_prefix,
    )

    check_roles_does_not_have_category(
        bundle.provider_prototype().display_name,
        map(extract_role_short_info, get_roles_of_type(RoleType.BUSINESS, sdk_client_fs)),
    )
