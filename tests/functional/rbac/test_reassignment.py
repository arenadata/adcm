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
from typing import Collection, Dict, Generator, List, Tuple

import allure
import pytest
from adcm_client.objects import (
    ADCMClient,
    Bundle,
    Cluster,
    Host,
    Policy,
    Provider,
    Role,
    Service,
    User,
)
from adcm_pytest_plugin.utils import get_data_dir
from tests.functional.rbac.conftest import (
    TEST_USER_CREDENTIALS,
    BusinessRoles,
    RbacRoles,
    as_user_objects,
    is_allowed,
    is_denied,
)
from tests.functional.tools import AnyADCMObject, get_object_represent

pytestmark = [pytest.mark.extra_rbac]


def upload_bundle(client: ADCMClient, bundle_name: str) -> Bundle:
    """Upload bundle by directory name"""
    return client.upload_from_fs(get_data_dir(__file__, bundle_name))


@contextmanager
def new_client_instance(user: str, password: str, url: str) -> Generator[ADCMClient, None, None]:
    """
    Creates new ADCM client instance.
    Use it to "refresh" permissions.
    """
    yield ADCMClient(user=user, password=password, url=url)


class TestReapplyTriggers:
    """Test reapply cases"""

    def test_add_remove_host_from_cluster(self, clients, is_denied_to_user, prepare_objects, user):
        """Test that policies are applied after host add/remove after the policy was assigned at first"""
        admin_cluster, *_, admin_provider, admin_host = prepare_objects
        admin_another_host = admin_provider.host_create(fqdn="another-host")

        with allure.step("Check that edit hosts and cluster are forbidden for user"):
            is_denied_to_user(admin_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)
            is_denied_to_user(admin_another_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)
            is_denied_to_user(admin_cluster, BusinessRoles.MAP_HOSTS)

        self.grant_role(clients.admin, user, RbacRoles.CLUSTER_ADMINISTRATOR, admin_cluster)
        clients.user.reread()

        user_cluster, *_ = as_user_objects(clients.user, admin_cluster)
        is_denied_to_user(admin_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)

        is_allowed(user_cluster, BusinessRoles.MAP_HOSTS, admin_host)
        user_host, *_ = as_user_objects(clients.user, admin_host)
        is_allowed(user_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)
        is_denied_to_user(admin_another_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)

        is_allowed(user_cluster, BusinessRoles.MAP_HOSTS, admin_another_host)
        user_another_host, *_ = as_user_objects(clients.user, admin_another_host)
        is_allowed(user_another_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)

        is_allowed(user_cluster, BusinessRoles.UNMAP_HOSTS, user_host)
        is_denied_to_user(admin_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)
        is_allowed(user_another_host, BusinessRoles.EDIT_HOST_CONFIGURATIONS)

    def test_add_remove_service_from_cluster(self, clients, is_denied_to_user, prepare_objects, user):
        """Test that policies are applied/removed after service add/remove after the policy was assigned at first"""
        admin_cluster, admin_service, *_ = prepare_objects

        with allure.step("Check that edit service and cluster are forbidden for user"):
            is_denied_to_user(admin_cluster, BusinessRoles.ADD_SERVICE)
            is_denied_to_user(admin_service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)

        self.grant_role(clients.admin, user, RbacRoles.CLUSTER_ADMINISTRATOR, admin_cluster)
        clients.user.reread()
        cluster, service = as_user_objects(clients.user, admin_cluster, admin_service)

        is_allowed(service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)
        new_service = is_allowed(cluster, BusinessRoles.ADD_SERVICE)
        with new_client_instance(*TEST_USER_CREDENTIALS, url=clients.admin.url) as client:
            user_cluster, user_new_service = as_user_objects(client, cluster, new_service)
            is_allowed(user_new_service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)
            is_allowed(user_cluster, BusinessRoles.REMOVE_SERVICE, new_service)

        is_allowed(service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)

    # pylint: disable=too-many-locals
    def test_change_hostcomponent(self, clients, prepare_objects, user):
        """Test that change of HC map correctly affects access to components"""
        admin_cluster, admin_service, *_, admin_provider, admin_host = prepare_objects
        admin_new_service = admin_cluster.service_add(name="new_service")
        admin_another_host = admin_provider.host_create(fqdn="another-host")
        admin_cluster.host_add(admin_host)
        admin_cluster.host_add(admin_another_host)

        def _check_host_configs(allowed_on: Collection[Host] = (), denied_on: Collection[Host] = ()):
            with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
                for obj in as_user_objects(user_client, *allowed_on):
                    is_allowed(obj, BusinessRoles.VIEW_HOST_CONFIGURATIONS)
                # is_denied uses user_client to check permissions, so no need to convert
                for obj in denied_on:
                    is_denied(obj, BusinessRoles.VIEW_HOST_CONFIGURATIONS, client=user_client)

        with allure.step("Check configs of hosts aren't allowed to view before Service Admin is granted to user"):
            _check_host_configs([], [admin_host, admin_another_host])

        self.grant_role(clients.admin, user, RbacRoles.SERVICE_ADMINISTRATOR, admin_service)

        with allure.step("Check configs of hosts aren't allowed to view before HC map is set"):
            _check_host_configs([], [admin_host, admin_another_host])

        with allure.step(f"Assign component of test_service on host {admin_host.fqdn}"):
            admin_cluster.hostcomponent_set((admin_host, admin_service.component(name="test_component")))
            host, *_ = as_user_objects(clients.user, admin_host)
            _check_host_configs([host], [admin_another_host])

        with allure.step("Assign components of new_service on two hosts"):
            admin_cluster.hostcomponent_set(
                (host, admin_new_service.component(name="test_component")),
                (admin_another_host, admin_new_service.component(name="new_component")),
            )
            _check_host_configs([], [host, admin_another_host])

        with allure.step(
            f"Assign components of new_service on two hosts, and component of test_service on {admin_another_host.fqdn}"
        ):
            admin_cluster.hostcomponent_set(
                (host, admin_new_service.component(name="test_component")),
                (admin_another_host, admin_new_service.component(name="new_component")),
                (admin_another_host, admin_service.component(name="new_component")),
            )
            another_host, *_ = as_user_objects(clients.user, admin_another_host)
            _check_host_configs([another_host], [host])

    def grant_role(self, client: ADCMClient, user: User, role: RbacRoles, *objects: AnyADCMObject) -> Policy:
        """Grant RBAC default role to a user"""
        with allure.step(f'Grant role "{role.value}" to user {user.username}'):
            return client.policy_create(
                name=f"{user.username} is {role.value}",
                role=client.role(name=role.value),
                objects=objects,
                user=[user],
            )

    def test_add_remove_user_from_group_and_policy(self, clients, is_denied_to_user, prepare_objects, user):
        """Test that user added/removed to the policy directly or as a part of a group"""

        admin_cluster, admin_service, admin_component, *_ = prepare_objects

        with allure.step("Check that edit cluster, service and component configurations are forbidden for user"):
            is_denied_to_user(admin_cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS)
            is_denied_to_user(admin_service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)
            is_denied_to_user(admin_component, BusinessRoles.EDIT_COMPONENT_CONFIGURATIONS)
        with allure.step(f"Create user group with {user.username}"):
            test_group = clients.admin.group_create("Test_group", user=[{"id": user.id}])
        with allure.step('Create a "Cluster Administrator" policy for a group'):
            test_policy = clients.admin.policy_create(
                name="Test_policy",
                role=clients.admin.role(name=RbacRoles.CLUSTER_ADMINISTRATOR.value),
                user=[],
                group=[test_group],
                objects=[admin_cluster],
            )
            clients.user.reread()
        user_cluster, user_service, user_component = as_user_objects(
            clients.user, admin_cluster, admin_service, admin_component
        )
        with allure.step("Check that edit cluster, service and component configurations are allowed for user"):
            is_allowed(user_cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS)
            is_allowed(user_service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)
            is_allowed(user_component, BusinessRoles.EDIT_COMPONENT_CONFIGURATIONS)
        with allure.step("Change group: delete user"):
            test_group.update(user=[])
        with allure.step("Check that edit cluster, service and component configurations are forbidden for user"):
            is_denied_to_user(admin_cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS)
            is_denied_to_user(admin_service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)
            is_denied_to_user(admin_component, BusinessRoles.EDIT_COMPONENT_CONFIGURATIONS)
        with allure.step("Change test policy: add user"):
            test_policy.update(user=[{"id": user.id}])
        with allure.step("Check that edit cluster, service and component configurations are allowed for user"):
            is_allowed(user_cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS)
            is_allowed(user_service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)
            is_allowed(user_component, BusinessRoles.EDIT_COMPONENT_CONFIGURATIONS)
        with allure.step("Change test policy: delete user"):
            test_policy.update(user=[])
        with allure.step("Check that edit cluster, service and component configurations are forbidden for user"):
            is_denied_to_user(admin_cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS)
            is_denied_to_user(admin_service, BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS)
            is_denied_to_user(admin_component, BusinessRoles.EDIT_COMPONENT_CONFIGURATIONS)

    def test_add_remove_cluster_from_policy(self, clients, is_denied_to_user, prepare_objects, user):
        """Test that policies are applied after cluster add/remove to the policy"""

        admin_cluster, *_ = prepare_objects
        role_to_check = BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS

        with allure.step("Create two clusters"):
            bundle = upload_bundle(clients.admin, "cluster")
            first_cluster = bundle.cluster_create(name="Test Cluster 1")
            second_cluster = bundle.cluster_create(name="Test Cluster 2")

        with allure.step(f"Check that {role_to_check.name} is denied for user"):
            is_denied_to_user(admin_cluster, role_to_check)
            is_denied_to_user(first_cluster, role_to_check)
            is_denied_to_user(second_cluster, role_to_check)

        with allure.step("Create a test policy with user and first cluster"):
            test_policy = clients.admin.policy_create(
                name="Test_policy",
                role=clients.admin.role(name=RbacRoles.CLUSTER_ADMINISTRATOR.value),
                user=[user],
                objects=[first_cluster],
            )
            clients.user.reread()
        with allure.step(f"Check that {role_to_check.name} is allowed for user for first cluster and denied for other"):
            is_allowed(as_user_objects(clients.user, first_cluster)[0], role_to_check)
            is_denied_to_user(admin_cluster, role_to_check)
            is_denied_to_user(second_cluster, role_to_check)
        with allure.step("Change test policy: first cluster to second cluster"):
            test_policy.update(object=[{"id": second_cluster.id, "type": "cluster"}])
        with allure.step(
            f"Check that {role_to_check.name} is allowed for user for second cluster and denied for other"
        ):
            is_allowed(as_user_objects(clients.user, second_cluster)[0], role_to_check)
            is_denied_to_user(admin_cluster, role_to_check)
            is_denied_to_user(first_cluster, role_to_check)

    def test_add_remove_service_from_policy(self, clients, is_denied_to_user, prepare_objects, user):
        """Test that policies are applied after service add/remove to the policy"""

        _, admin_service, *_ = prepare_objects
        role_to_check = BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS
        with allure.step("Create a cluster with two services"):
            cluster = upload_bundle(clients.admin, "cluster").cluster_create(name="Test Cluster 1")
            first_service = cluster.service_add(name="test_service")
            second_service = cluster.service_add(name="test_service_2")

        with allure.step(f"Check that {role_to_check.name} is denied for user"):
            is_denied_to_user(admin_service, role_to_check)
            is_denied_to_user(first_service, role_to_check)
            is_denied_to_user(second_service, role_to_check)

        with allure.step("Create a test policy with user and first service"):
            test_policy = clients.admin.policy_create(
                name="Test_policy",
                role=clients.admin.role(name=RbacRoles.SERVICE_ADMINISTRATOR.value),
                user=[user],
                objects=[first_service],
            )
            clients.user.reread()

        with allure.step(f"Check that {role_to_check.name} is allowed for user for first service and denied for other"):
            is_allowed(as_user_objects(clients.user, first_service)[0], role_to_check)
            is_denied_to_user(admin_service, role_to_check)
            is_denied_to_user(second_service, role_to_check)
        with allure.step("Change test policy: first service to second service"):
            test_policy.update(object=[{"id": second_service.id, "type": "service"}])
        with allure.step(
            f"Check that {role_to_check.name} is allowed for user for second service and denied for other"
        ):
            is_allowed(as_user_objects(clients.user, second_service)[0], role_to_check)
            is_denied_to_user(admin_service, role_to_check)
            is_denied_to_user(first_service, role_to_check)

    def test_add_remove_provider_from_policy(self, clients, is_denied_to_user, prepare_objects, user):
        """Test that policies are applied after provider add/remove to the policy"""

        _, _, _, admin_provider, _ = prepare_objects
        role_to_check = BusinessRoles.EDIT_PROVIDER_CONFIGURATIONS
        with allure.step("Create two providers"):
            bundle = upload_bundle(clients.admin, "provider")
            first_provider = bundle.provider_create(name="Test provider 1")
            second_provider = bundle.provider_create(name="Test provider 2")
        with allure.step(f"Check that {role_to_check.name} is denied for user"):
            is_denied_to_user(admin_provider, role_to_check)
            is_denied_to_user(first_provider, role_to_check)
            is_denied_to_user(second_provider, role_to_check)

        with allure.step("Create a test policy with user and first provider"):
            test_policy = clients.admin.policy_create(
                name="Test_policy",
                role=clients.admin.role(name=RbacRoles.PROVIDER_ADMINISTRATOR.value),
                user=[user],
                objects=[first_provider],
            )
            clients.user.reread()
        with allure.step(
            f"Check that {role_to_check.name} is allowed for user for first provider and denied for other"
        ):
            is_allowed(as_user_objects(clients.user, first_provider)[0], role_to_check)
            is_denied_to_user(admin_provider, role_to_check)
            is_denied_to_user(second_provider, role_to_check)
        with allure.step("Change test policy: first provider to second provider"):
            test_policy.update(object=[{"id": second_provider.id, "type": "provider"}])
        with allure.step(
            f"Check that {role_to_check.name} is allowed for user for second provider and denied for other"
        ):
            is_allowed(as_user_objects(clients.user, second_provider)[0], role_to_check)
            is_denied_to_user(admin_provider, role_to_check)
            is_denied_to_user(first_provider, role_to_check)


class TestMultiplePolicyReapply:
    """
    Test that change of parametrization object in one of multiple policies granted to same user
    doesn't lead to any kind of unpredictable behavior.
    """

    @pytest.fixture()
    def objects(self, cluster_bundle, provider_bundle) -> Tuple[Cluster, Cluster, Service, Service, Provider]:
        """Prepare various objects for multiple policies test"""
        first_cluster = cluster_bundle.cluster_create(name="Test Cluster 1")
        second_cluster = cluster_bundle.cluster_create(name="Test Cluster 2")
        test_service = second_cluster.service_add(name="test_service")
        new_service = second_cluster.service_add(name="new_service")
        provider = provider_bundle.provider_create(name="Test Provider 1")
        return first_cluster, second_cluster, test_service, new_service, provider

    @pytest.fixture()
    def admin_roles(self, sdk_client_fs) -> Tuple[Role, Role, Role]:
        """
        Find and return roles (in order):
        - Cluster Administrator
        - Service Administrator
        - Provider Administrator
        """
        cluster_admin = sdk_client_fs.role(name=RbacRoles.CLUSTER_ADMINISTRATOR.value)
        service_admin = sdk_client_fs.role(name=RbacRoles.SERVICE_ADMINISTRATOR.value)
        provider_admin = sdk_client_fs.role(name=RbacRoles.PROVIDER_ADMINISTRATOR.value)
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
        clients.user.reread()
        self.check_edit_is_allowed(clients.user, first_cluster, test_service, provider)
        self.check_edit_is_denied(clients.user, second_cluster, new_service)
        _, service_policy, _ = policies
        service_policy.update(object=[{"id": new_service.id, "type": "service"}])
        self.check_edit_is_allowed(clients.user, first_cluster, new_service, provider)
        self.check_edit_is_denied(clients.user, second_cluster, test_service)

    @allure.step("Grant policies on Cluster #1, service of Cluster #2 and Provider #1")
    def grant_policies_to_user(self, admin_client, cluster_service_provider, admin_roles, user) -> List[Policy]:
        """Grant policies to user (different policy for each role)"""
        return [
            admin_client.policy_create(
                name=f"Policy on {get_object_represent(obj)}", role=role, objects=[obj], user=[user]
            )
            for role, obj in zip(admin_roles, cluster_service_provider)
        ]

    @allure.step("Check edit is allowed")
    def check_edit_is_allowed(self, user_client, *objects):
        """Check edit is allowed"""
        for obj in as_user_objects(user_client, *objects):
            is_allowed(obj, BusinessRoles.edit_config_of(obj))

    @allure.step("Check edit is denied")
    def check_edit_is_denied(self, user_client, *objects):
        """Check edit is denied"""
        for obj in objects:
            is_denied(obj, BusinessRoles.edit_config_of(obj), client=user_client)


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
        name=role_name,
        display_name=role_name,
        child=_form_children(clients.admin, BusinessRoles.CREATE_CLUSTER),
    )
    policy = clients.admin.policy_create(name="User policy", role=role, user=[user])
    with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
        user_cluster_bundle, *_ = as_user_objects(user_client, cluster_bundle)
        is_allowed(user_cluster_bundle, BusinessRoles.CREATE_CLUSTER)
        is_denied(provider_bundle, BusinessRoles.CREATE_HOST_PROVIDER, client=clients.user)
    role.update(child=_form_children(clients.admin, BusinessRoles.CREATE_HOST_PROVIDER))
    with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
        user_provider_bundle, *_ = as_user_objects(user_client, provider_bundle)
        is_denied(cluster_bundle, BusinessRoles.CREATE_CLUSTER, client=clients.user)
        is_allowed(user_provider_bundle, BusinessRoles.CREATE_HOST_PROVIDER)
    policy.delete()
    role.delete()


def check_role_with_parametrization(clients, user, cluster_bundle: Bundle, provider_bundle: Bundle):
    """Check that update of role with parametrization leads to correct permissions update"""
    cluster, provider = cluster_bundle.cluster_create("clusteraster"), provider_bundle.provider_create("provideraider")
    role_name = "Role with parametrization"

    role = clients.admin.role_create(
        name=role_name,
        display_name=role_name,
        child=_form_children(clients.admin, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS),
    )
    with allure.step("Create policy with role (Edit cluster config) and expect cluster config is editable"):
        policy = clients.admin.policy_create(name="User policy", role=role, objects=[cluster], user=[user])
        with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
            user_cluster, *_ = as_user_objects(user_client, cluster)
            is_allowed(user_cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS)
            is_denied(provider, BusinessRoles.EDIT_PROVIDER_CONFIGURATIONS, client=user_client)
    with allure.step("Change role child to Edit provider config and expect both cluster and provider non editable"):
        role.update(child=_form_children(clients.admin, BusinessRoles.EDIT_PROVIDER_CONFIGURATIONS))
        with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
            is_denied(cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS, client=user_client)
            is_denied(provider, BusinessRoles.EDIT_PROVIDER_CONFIGURATIONS, client=user_client)
    with allure.step("Change policy object parametrization to provider and expect provider to be editable"):
        policy.update(object=[{"type": "provider", "id": provider.id}])
        with new_client_instance(*TEST_USER_CREDENTIALS, clients.user.url) as user_client:
            user_provider, *_ = as_user_objects(user_client, provider)
            is_denied(user_cluster, BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS, client=user_client)
            is_allowed(user_provider, BusinessRoles.EDIT_PROVIDER_CONFIGURATIONS)
    policy.delete()
    role.delete()


def _form_children(admin_client: ADCMClient, *business_roles: BusinessRoles) -> List[Dict[str, int]]:
    """Create list of children for role based on business roles"""
    return [{"id": admin_client.role(name=role.value.role_name).id} for role in business_roles]
