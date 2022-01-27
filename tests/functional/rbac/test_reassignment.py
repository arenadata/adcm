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

# pylint: disable=no-self-use

"""Test roles reassignment in various situations"""

from contextlib import contextmanager
from typing import Dict, List, Generator, Collection, Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, User, Policy, Host, Cluster, Service, Provider, Role

from tests.functional.tools import AnyADCMObject, get_object_represent
from tests.functional.rbac.conftest import (
    BusinessRoles,
    is_allowed,
    is_denied,
    as_user_objects,
    TEST_USER_CREDENTIALS,
    RbacRoles,
)


@contextmanager
def new_client_instance(user: str, password: str, url: str) -> Generator[ADCMClient, None, None]:
    """
    Creates new ADCM client instance.
    Use it to "refresh" permissions.
    """
    yield ADCMClient(user=user, password=password, url=url)


class TestReapplyTriggers:
    """Test reapply cases"""

    def test_add_remove_host_from_cluster(self, clients, prepare_objects, user):
        """Test that policies are applied after host add/remove after the policy was assigned at first"""
        *_, admin_provider, _ = prepare_objects
        another_host = admin_provider.host_create(fqdn='another-host')
        cluster, *_, host, another_host = as_user_objects(clients.user, *prepare_objects, another_host)

        is_denied(host, BusinessRoles.EditHostConfigurations)
        is_denied(another_host, BusinessRoles.EditHostConfigurations)
        is_denied(cluster, BusinessRoles.MapHosts, host)

        self.grant_role(clients.admin, user, RbacRoles.ClusterAdministrator, cluster)

        is_denied(host, BusinessRoles.EditHostConfigurations)
        is_allowed(cluster, BusinessRoles.MapHosts, host)
        is_allowed(host, BusinessRoles.EditHostConfigurations)
        is_denied(another_host, BusinessRoles.EditHostConfigurations)
        is_allowed(cluster, BusinessRoles.MapHosts, another_host)
        is_allowed(another_host, BusinessRoles.EditHostConfigurations)

        is_allowed(cluster, BusinessRoles.UnmapHosts, host)
        is_denied(host, BusinessRoles.EditHostConfigurations)
        is_allowed(another_host, BusinessRoles.EditHostConfigurations)

    def test_add_remove_service_from_cluster(self, clients, prepare_objects, user):
        """Test that policies are applied/removed after service add/remove after the policy was assigned at first"""
        cluster, service, *_ = as_user_objects(clients.user, *prepare_objects)

        is_denied(cluster, BusinessRoles.AddService)
        is_denied(service, BusinessRoles.EditServiceConfigurations)

        self.grant_role(clients.admin, user, RbacRoles.ClusterAdministrator, cluster)

        is_allowed(service, BusinessRoles.EditServiceConfigurations)
        new_service = is_allowed(cluster, BusinessRoles.AddService)
        with new_client_instance(*TEST_USER_CREDENTIALS, url=clients.admin.url) as client:
            user_cluster, user_new_service = as_user_objects(client, cluster, new_service)
            is_allowed(user_new_service, BusinessRoles.EditServiceConfigurations)
            is_allowed(user_cluster, BusinessRoles.RemoveService, new_service)

        is_allowed(service, BusinessRoles.EditServiceConfigurations)

    # pylint: disable=too-many-locals
    def test_change_hostcomponent(self, clients, prepare_objects, user):
        """Test that change of HC map correctly affects access to components"""
        admin_cluster, *_, admin_provider, admin_host = prepare_objects
        admin_new_service = admin_cluster.service_add(name='new_service')
        another_host = admin_provider.host_create(fqdn='another-host')
        admin_cluster.host_add(admin_host)
        admin_cluster.host_add(another_host)

        _, test_service, *_, host, another_host = as_user_objects(clients.user, *prepare_objects, another_host)

        def _check_host_configs(allowed_on: Collection[Host] = (), denied_on: Collection[Host] = ()):
            with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
                for obj in as_user_objects(user_client, *allowed_on):
                    is_allowed(obj, BusinessRoles.ViewHostConfigurations)
                for obj in as_user_objects(user_client, *denied_on):
                    is_denied(obj, BusinessRoles.ViewHostConfigurations)

        with allure.step("Check configs of hosts aren't allowed to view before Service Admin is granted to user"):
            _check_host_configs([], [host, another_host])

        self.grant_role(clients.admin, user, RbacRoles.ServiceAdministrator, test_service)

        with allure.step("Check configs of hosts aren't allowed to view before HC map is set"):
            _check_host_configs([], [host, another_host])

        test_service_test_component, test_service_new_component = test_service.component(
            name='test_component'
        ), test_service.component(name='new_component')
        new_service_test_component, new_service_new_component = as_user_objects(
            clients.user,
            admin_new_service.component(name='test_component'),
            admin_new_service.component(name='new_component'),
        )

        with allure.step(f'Assign component of test_service on host {host.fqdn}'):
            admin_cluster.hostcomponent_set((host, test_service_test_component))
            _check_host_configs([host], [another_host])

        with allure.step('Assign components of new_service on two hosts'):
            admin_cluster.hostcomponent_set(
                (host, new_service_test_component), (another_host, new_service_new_component)
            )
            _check_host_configs([], [host, another_host])

        with allure.step(
            f'Assign components of new_service on two hosts, and component of test_service on {another_host.fqdn}'
        ):
            admin_cluster.hostcomponent_set(
                (host, new_service_test_component),
                (another_host, new_service_new_component),
                (another_host, test_service_new_component),
            )
            _check_host_configs([another_host], [host])

    # pylint: disable-next=no-self-use
    def grant_role(self, client: ADCMClient, user: User, role: RbacRoles, *objects: AnyADCMObject) -> Policy:
        """Grant RBAC default role to a user"""
        with allure.step(f'Grant role "{role.value}" to user {user.username}'):
            return client.policy_create(
                name=f'{user.username} is {role.value}', role=client.role(name=role.value), objects=objects, user=[user]
            )


class TestMultiplePolicyReapply:
    """
    Test that change of parametrization object in one of multiple policies granted to same user
    doesn't lead to any kind of unpredictable behavior.
    """

    @pytest.fixture()
    def objects(self, cluster_bundle, provider_bundle) -> Tuple[Cluster, Cluster, Service, Service, Provider]:
        """Prepare various objects for multiple policies test"""
        first_cluster = cluster_bundle.cluster_create(name='Test Cluster #1')
        second_cluster = cluster_bundle.cluster_create(name='Test Cluster #2')
        test_service = second_cluster.service_add(name='test_service')
        new_service = second_cluster.service_add(name='new_service')
        provider = provider_bundle.provider_create(name='Test Provider #1')
        return first_cluster, second_cluster, test_service, new_service, provider

    @pytest.fixture()
    def admin_roles(self, sdk_client_fs) -> Tuple[Role, Role, Role]:
        """
        Find and return roles (in order):
        - Cluster Administrator
        - Service Administrator
        - Provider Administrator
        """
        cluster_admin = sdk_client_fs.role(name=RbacRoles.ClusterAdministrator.value)
        service_admin = sdk_client_fs.role(name=RbacRoles.ServiceAdministrator.value)
        provider_admin = sdk_client_fs.role(name=RbacRoles.ProviderAdministrator.value)
        return cluster_admin, service_admin, provider_admin

    def test_change_one_of_policies_parametrization(self, clients, objects, admin_roles, user):
        """
        Assign multiple policies on different objects for the same user.
        Change parametrization of one of policies.
        Check if permissions are correct
        """
        first_cluster, second_cluster, test_service, new_service, provider = objects
        policies = self.grant_policies_to_user(
            clients.admin, (first_cluster, test_service, provider), admin_roles, user
        )
        self.check_edit_is_allowed(clients.user, first_cluster, test_service, provider)
        self.check_edit_is_denied(clients.user, second_cluster, new_service)
        _, service_policy, _ = policies
        service_policy.update(object=[{'id': new_service.id, 'type': 'service'}])
        self.check_edit_is_allowed(clients.user, first_cluster, new_service, provider)
        self.check_edit_is_denied(clients.user, second_cluster, test_service)

    @allure.step('Grant policies on Cluster #1, service of Cluster #2 and Provider #1')
    def grant_policies_to_user(self, admin_client, cluster_service_provider, admin_roles, user) -> List[Policy]:
        """Grant policies to user (different policy for each role)"""
        return [
            admin_client.policy_create(
                name=f'Policy on {get_object_represent(obj)}', role=role, objects=[obj], user=[user]
            )
            for role, obj in zip(admin_roles, cluster_service_provider)
        ]

    @allure.step('Check edit is allowed')
    def check_edit_is_allowed(self, user_client, *objects):
        """Check edit is allowed"""
        for obj in as_user_objects(user_client, *objects):
            is_allowed(obj, BusinessRoles.edit_config_of(obj))

    @allure.step('Check edit is denied')
    def check_edit_is_denied(self, user_client, *objects):
        """Check edit is denied"""
        for obj in as_user_objects(user_client, *objects):
            is_denied(obj, BusinessRoles.edit_config_of(obj))


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
