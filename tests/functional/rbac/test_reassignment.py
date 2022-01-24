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

"""Test roles reassignment in various situations"""

from contextlib import contextmanager
from typing import Dict, List, Generator

from adcm_client.objects import ADCMClient, Bundle

from tests.functional.rbac.conftest import BusinessRoles, is_allowed, is_denied, as_user_objects, TEST_USER_CREDENTIALS


@contextmanager
def new_client_instance(user: str, password: str, url: str) -> Generator[ADCMClient, None, None]:
    """
    Creates new ADCM client instance.
    Use it to "refresh" permissions.
    """
    yield ADCMClient(user=user, password=password, url=url)


def test_child_role_update_after_assignment(clients, user, cluster_bundle, provider_bundle):
    """
    Test that permissions are updated when child of previously assigned role is updated
    """
    check_role_wo_parametrization(clients, user, cluster_bundle, provider_bundle)
    check_role_with_parametrization(clients, user, cluster_bundle, provider_bundle)


def check_role_wo_parametrization(clients, user, cluster_bundle, provider_bundle):
    """Check that update of role without parametrization leads to correct permissions update"""
    role_name = "Role without parametrization"
    role = clients.admin.role_create(
        name=role_name, display_name=role_name, child=_form_children(clients.admin, BusinessRoles.CreateCluster)
    )
    policy = clients.admin.policy_create(name="User policy", role=role, user=[user])
    with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
        cluster_bundle, provider_bundle = as_user_objects(user_client, cluster_bundle, provider_bundle)
        is_allowed(cluster_bundle, BusinessRoles.CreateCluster)
        is_denied(provider_bundle, BusinessRoles.CreateHostProvider)
    role.update(child=_form_children(clients.admin, BusinessRoles.CreateHostProvider))
    with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
        cluster_bundle, provider_bundle = as_user_objects(user_client, cluster_bundle, provider_bundle)
        is_denied(cluster_bundle, BusinessRoles.CreateCluster)
        is_allowed(provider_bundle, BusinessRoles.CreateHostProvider)
    policy.delete()
    role.delete()


def check_role_with_parametrization(clients, user, cluster_bundle: Bundle, provider_bundle: Bundle):
    """Check that update of role with parametrization leads to correct permissions update"""
    cluster, provider = cluster_bundle.cluster_create('clusteraster'), provider_bundle.provider_create('provideraider')
    role_name = "Role with parametrization"

    role = clients.admin.role_create(
        name=role_name,
        display_name=role_name,
        child=_form_children(clients.admin, BusinessRoles.EditClusterConfigurations),
    )
    policy = clients.admin.policy_create(name="User policy", role=role, objects=[cluster], user=[user])
    with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
        user_cluster, user_provider = as_user_objects(user_client, cluster, provider)
        is_allowed(user_cluster, BusinessRoles.EditClusterConfigurations)
        is_denied(user_provider, BusinessRoles.EditProviderConfigurations)
    role.update(child=_form_children(clients.admin, BusinessRoles.EditProviderConfigurations))
    with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
        user_cluster, user_provider = as_user_objects(user_client, cluster, provider)
        is_denied(user_cluster, BusinessRoles.EditClusterConfigurations)
        is_denied(user_provider, BusinessRoles.EditProviderConfigurations)
    policy.update(object=[{'type': 'provider', 'id': provider.id}])
    with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
        user_cluster, user_provider = as_user_objects(user_client, cluster, provider)
        is_denied(user_cluster, BusinessRoles.EditClusterConfigurations)
        is_allowed(user_provider, BusinessRoles.EditProviderConfigurations)
    policy.delete()
    role.delete()


def _form_children(admin_client: ADCMClient, *business_roles: BusinessRoles) -> List[Dict[str, int]]:
    """Create list of children for role based on business roles"""
    return [{"id": admin_client.role(name=role.value.role_name).id} for role in business_roles]
