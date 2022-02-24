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
Test that granting any permission on object allows user to:
- see this object in the list of objects
- get this object from ADCM client
"""
import os.path
from contextlib import contextmanager
from typing import Callable, Set

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import catch_failed

from tests.library.utils import lower_class_name
from tests.functional.tools import get_object_represent
from tests.functional.rbac.conftest import (
    DATA_DIR,
    BusinessRoles as BR,
    get_as_client_object,
    delete_policy,
    create_policy,
    RbacRoles,
)
from tests.functional.rbac.action_role_utils import create_action_policy, action_business_role

# pylint: disable=no-self-use


@contextmanager
def granted_policy(client, business_role, adcm_object, user):
    """Create policy based on business role and delete if afterwards"""
    policy = create_policy(client, business_role, [adcm_object], [user], [])
    yield policy
    delete_policy(policy)


class TestAccessToBasicObjects:
    """
    Test granting access to default objects:
    cluster, service, component, provider, host
    """

    def test_access_to_cluster_from_service_role(self, clients, user, prepare_objects, second_objects):
        """
        Test that granting permission on service grants permission to "view" service and cluster
        """
        all_objects = prepare_objects + second_objects
        cluster, service, *component_and_provider_objects = prepare_objects
        cluster_and_service = (cluster, service)

        for business_role in (
            BR.ViewServiceConfigurations,
            BR.EditServiceConfigurations,
            BR.ViewImports,
            BR.ManageServiceImports,
            BR.ViewAnyObjectConfiguration,
        ):
            with allure.step(
                f'Check that granting "{business_role.value.role_name}" role to service gives access to "view" cluster'
            ):
                check_objects_are_not_viewable(clients.user, all_objects)
                with granted_policy(clients.admin, business_role, service, user):
                    check_objects_are_viewable(clients.user, cluster_and_service)
                    check_objects_are_not_viewable(clients.user, component_and_provider_objects + second_objects)
                check_objects_are_not_viewable(clients.user, all_objects)

    def test_access_to_parents_from_component_role(self, clients, user, prepare_objects, second_objects):
        """
        Test that granting permission on component grants permission to "view" component, service and cluster
        """
        all_objects = prepare_objects + second_objects
        cluster, service, component, *provider_objects = prepare_objects
        cluster_objects = (cluster, service, component)

        for business_role in (BR.ViewComponentConfigurations, BR.EditComponentConfigurations):
            with allure.step(
                f'Check that granting "{business_role.value.role_name}" role to component '
                'gives access to "view" cluster'
            ):
                check_objects_are_not_viewable(clients.user, all_objects)
                with granted_policy(clients.admin, business_role, component, user):
                    check_objects_are_viewable(clients.user, cluster_objects)
                    check_objects_are_not_viewable(clients.user, provider_objects + second_objects)
                check_objects_are_not_viewable(clients.user, all_objects)

    @pytest.mark.extra_rbac()
    def test_hierarchy_access_to_host(self, clients, user, cluster_bundle, provider_bundle):
        """
        Test that user can get host
        when it is bonded to a cluster (user has permission to get this cluster),
        when host is added to a cluster
        when permission is granted before/after host is added
        """
        cluster = cluster_bundle.cluster_create(name='Test Cluster')
        provider = provider_bundle.provider_create(name='Test Provider')
        first_host, second_host = provider.host_create('host-1'), provider.host_create('host-2')

        with allure.step('Add host to a cluster and check "view" permissions are granted'):
            cluster.host_add(first_host)
            check_objects_are_not_viewable(clients.user, [first_host, second_host])

        with allure.step('Create policy on cluster and check "view" permission exists on added host'):
            policy = clients.admin.policy_create(
                name='Test Policy',
                role=clients.admin.role(name=RbacRoles.ClusterAdministrator.value),
                objects=[cluster],
                user=[user],
            )
            check_objects_are_viewable(clients.user, [first_host])
            check_objects_are_not_viewable(clients.user, [second_host])

        with allure.step('Add second host and check "view" permission is granted on it'):
            cluster.host_add(second_host)
            check_objects_are_viewable(clients.user, [first_host, second_host])

        with allure.step('Remove policy and check "view" permissions were withdrawn'):
            delete_policy(policy)
            check_objects_are_not_viewable(clients.user, [first_host, second_host])

    @pytest.mark.extra_rbac()
    def test_hostcomponent_set(self, clients, user, prepare_objects, second_objects):
        """
        Test that hostcomponent can be set via ADCM client: user can get component and hosts on cluster
        """
        cluster, service, component, provider, host = prepare_objects
        check_objects_are_not_viewable(clients.user, prepare_objects + second_objects)
        with granted_policy(clients.admin, BR.EditHostComponents, cluster, user):
            cluster.host_add(host)
            check_objects_are_viewable(clients.user, [cluster, service, component, host])
            check_objects_are_not_viewable(clients.user, [provider] + list(second_objects))
        check_objects_are_not_viewable(clients.user, prepare_objects + second_objects)


class TestActionBasedAccess:
    """Test that granting permission to run action grants "view" permissions on an owner object"""

    @pytest.fixture()
    def cluster_with_host_action(self, sdk_client_fs):
        """Create cluster with host action"""
        bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "cluster_with_host_action"))
        return bundle.cluster_create(name='Cool Test Cluster')

    @pytest.fixture()
    def host(self, cluster_with_host_action, provider_bundle):
        """Host object from "regular" provider that is added to cluster with host action"""
        provider = provider_bundle.provider_create(name='Cool Test Provider')
        return cluster_with_host_action.host_add(provider.host_create('see-mee-with-action'))

    def test_action_permission_grants_access_to_owner_object(self, clients, user, prepare_objects, second_objects):
        """
        Test that permission on action of an object grants permission to "view" this object
        """
        objects = set(prepare_objects)
        another_objects = set(second_objects)
        all_objects = objects | another_objects

        for adcm_object in objects:
            with allure.step(
                f'Add permission to run action on {adcm_object.__class__.__name__} and check if it became visible'
            ):
                check_objects_are_not_viewable(clients.user, all_objects)
                policy = create_action_policy(
                    clients.admin,
                    adcm_object,
                    action_business_role(adcm_object, 'No config action', no_deny_checker=True),
                    user=user,
                )
                check_objects_are_viewable(clients.user, [adcm_object])
                check_objects_are_not_viewable(clients.user, all_objects - {adcm_object})
                delete_policy(policy)
                check_objects_are_not_viewable(clients.user, all_objects)

    @pytest.mark.extra_rbac()
    def test_host_action_permission_grants_access_to_owner_object(self, clients, user, host):
        """
        Test that permission on host actions grants permission to "view" host
        """
        cluster = host.cluster()
        check_objects_are_not_viewable(clients.user, [cluster, host])
        policy = create_action_policy(
            clients.admin,
            cluster,
            action_business_role(cluster, 'Host action', no_deny_checker=True),
            user=user,
        )
        check_objects_are_viewable(clients.user, [host])
        check_objects_are_not_viewable(clients.user, [cluster])
        with allure.step('Change host state and check nothing broke'):
            host.action(name='host_action').run().wait()
            check_objects_are_viewable(clients.user, [host])
            check_objects_are_not_viewable(clients.user, [cluster])
        delete_policy(policy)
        check_objects_are_not_viewable(clients.user, [cluster, host])


def _get_objects_id(get_objects_list: Callable) -> Set[int]:
    return {obj.id for obj in get_objects_list()}


def check_objects_are_viewable(user_client: ADCMClient, objects):
    """Check that user can see objects in list and get them by id"""
    client_username = user_client.me().username
    api = user_client._api  # pylint: disable=protected-access
    for adcm_object in objects:
        object_represent = get_object_represent(adcm_object)
        with allure.step(f'Check that "{object_represent}" is available to user {client_username}'):
            object_type_name = lower_class_name(adcm_object)
            list_objects = getattr(user_client, f'{object_type_name}_list')
            available_objects_ids = _get_objects_id(list_objects)
            assert (
                adcm_object.id in available_objects_ids
            ), f'Object "{object_represent}" should be listed in the list of {object_type_name}s'
            with catch_failed(ObjectNotFound, f'Object "{object_represent}" should be available directly via client'):
                get_as_client_object(api, adcm_object)


def check_objects_are_not_viewable(user_client: ADCMClient, objects):
    """Check that user can't see objects in list and get them by id"""
    client_username = user_client.me().username
    api = user_client._api  # pylint: disable=protected-access
    for adcm_object in objects:
        object_represent = get_object_represent(adcm_object)
        with allure.step(f'Check that "{object_represent}" is not available to user {client_username}'):
            object_type_name = lower_class_name(adcm_object)
            list_objects = getattr(user_client, f'{object_type_name}_list')
            available_objects_ids = _get_objects_id(list_objects)
            assert (
                adcm_object.id not in available_objects_ids
            ), f'Object "{object_represent}" should not be listed in the list of {object_type_name}s'
            try:
                get_as_client_object(api, adcm_object)
            except ObjectNotFound:
                pass
            else:
                raise AssertionError('Object "%s" should not be available directly via client' % object_represent)
