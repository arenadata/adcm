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

"""Test that action permissions works and are applies to action running"""

# pylint: disable=too-many-locals

import itertools
import os
from contextlib import contextmanager
from typing import Optional, Tuple, Union

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Component, Provider, Service, User
from tests.functional.rbac.action_role_utils import (
    action_business_role,
    create_action_policy,
)
from tests.functional.rbac.actions.conftest import DATA_DIR
from tests.functional.rbac.conftest import (
    BusinessRole,
    as_user_objects,
    delete_policy,
    is_allowed,
    is_denied,
)
from tests.functional.tools import AnyADCMObject, get_object_represent

DO_NOTHING_ACTION = "Do nothing"

CONFIG_FIELD_TO_CHANGE = "longstring"
ACTION_CONFIG_ARGUMENT = "valofarg"
CHANGE_ACTION_NAME_TEMPLATE = "Change {object_type} Configuration"


def _do_nothing_action_not_presented(obj):
    """Filter for removing objects that doesn't have "Do nothing" action"""
    return DO_NOTHING_ACTION not in (a.display_name for a in obj.action_list())


# !===== Tests ======!


def test_cluster_basic(clients, user, actions_cluster, simple_cluster):
    """
    Test basic permissions on cluster objects' actions:
      - granted permission allows running only specified action on specified object;
      - other objects' actions are forbidden to run;
      - deleting policy actually removes right to run action.
    """
    cluster = actions_cluster
    service = cluster.service(name="actions_service")
    component = service.component(name="simple_component")
    all_objects = *get_all_cluster_tree_plain(actions_cluster), *get_all_cluster_tree_plain(simple_cluster)

    for adcm_object in (cluster, service, component):
        _test_basic_action_run_permissions(adcm_object, clients.admin, clients.user, user, all_objects)


def test_provider_basic(clients, user, actions_provider, simple_provider):
    """
    Test basic permissions on provider objects' actions:
      - granted permission allows running only specified action on specified object;
      - other objects' actions are forbidden to run;
      - deleting policy actually removes right to run action.
    """
    provider = actions_provider
    host = actions_provider.host()
    all_objects = provider, host, simple_provider, simple_provider.host()

    for adcm_object in (provider, host):
        _test_basic_action_run_permissions(adcm_object, clients.admin, clients.user, user, all_objects)


def _test_basic_action_run_permissions(adcm_object, admin_sdk, user_sdk, user, all_objects):
    """Check that granting and withdrawn of permission to run action works as expected"""
    with allure.step(
        f'Check that granting policy allows to run action "{DO_NOTHING_ACTION}" on {get_object_represent(adcm_object)}'
    ):
        business_role = action_business_role(adcm_object, DO_NOTHING_ACTION)
        policy = create_action_policy(admin_sdk, adcm_object, business_role, user=user)

        check_single_action_is_allowed_on_object(DO_NOTHING_ACTION, adcm_object, user_sdk, business_role)

    with allure.step(f"Check that granted permission doesn't allow running '{DO_NOTHING_ACTION}' on other objects"):
        for obj in filter(
            lambda x: not _is_the_same(x, adcm_object) and not _do_nothing_action_not_presented(x),
            all_objects,
        ):
            is_denied(obj, action_business_role(obj, DO_NOTHING_ACTION), client=user_sdk)

    with allure.step("Check permission withdrawn"):
        delete_policy(policy)
        is_denied(adcm_object, business_role, client=user_sdk)


def _is_the_same(first_object, second_object) -> bool:
    return first_object.__class__ == second_object.__class__ and first_object.id == second_object.id


@pytest.mark.extra_rbac()
def test_config_change_via_plugin(clients, user, actions_cluster, actions_provider):
    """
    Test that permission on action run is enough for changing configuration with plugins.
    Config change action has its own config.
    """
    cluster = actions_cluster
    service = actions_cluster.service(name="config_changing_service")
    component = service.component(name="config_changing_component")

    provider, host = actions_provider, actions_provider.host()

    _test_config_change(cluster, (cluster,), user=user, user_client=clients.user, admin_client=clients.admin)
    _test_config_change(service, (cluster, service), user=user, user_client=clients.user, admin_client=clients.admin)
    _test_config_change(
        component,
        (cluster, service, component),
        user=user,
        user_client=clients.user,
        admin_client=clients.admin,
    )

    _test_config_change(provider, (provider,), user=user, user_client=clients.user, admin_client=clients.admin)
    _test_config_change(host, (provider, host), user=user, user_client=clients.user, admin_client=clients.admin)


def _test_config_change(
    action_owner_object: AnyADCMObject,
    objects_to_change: Tuple[AnyADCMObject, ...],
    admin_client: ADCMClient,
    user_client: ADCMClient,
    user: User,
) -> None:
    """
    Grant policy to user to run actions that change config of objects.
    Then try to change config of an object via adcm_config plugin without having explicit permission to change config.

    :param action_owner_object: Object on which to run action that changes config.
    :param objects_to_change: Plain collection of objects (e.g. tuple) containing objects which config should be changed
                              by corresponding action on `action_owner_object`.
                              These objects should be from user SDK.
    :param admin_client: Admin SDK to check config.
    :param user: User instance to apply policy to.
    """
    owner_object_represent = get_object_represent(action_owner_object)
    action_names = [CHANGE_ACTION_NAME_TEMPLATE.format(object_type=obj.__class__.__name__) for obj in objects_to_change]
    business_roles = [action_business_role(action_owner_object, action_name) for action_name in action_names]
    object_role_map = tuple(zip(objects_to_change, business_roles))

    with allure.step(
        f'Apply policy on "{owner_object_represent}" and check config change is allowed without explicit permission'
    ):
        policy = create_action_policy(admin_client, action_owner_object, *business_roles, user=user)
        user_object, *_ = as_user_objects(user_client, action_owner_object)

        for admin_object, business_role in object_role_map:
            config_field_value = admin_object.config()[CONFIG_FIELD_TO_CHANGE]
            new_value = f"{config_field_value}_{admin_object.__class__.__name__}"
            with allure.step(f"Try to change {get_object_represent(admin_object)} from {owner_object_represent}"):
                task = is_allowed(user_object, business_role, config={ACTION_CONFIG_ARGUMENT: new_value})
                assert task.wait() == "success", "Action should succeeded"
                assert (
                    admin_object.config()[CONFIG_FIELD_TO_CHANGE] == new_value
                ), f"Config of object {get_object_represent(admin_object)} should've been changed"

    with allure.step("Delete policy and check actions are denied and config stays the same"):
        delete_policy(policy)
        for admin_object, business_role in object_role_map:
            with allure.step(f"Try to change {get_object_represent(admin_object)} from {owner_object_represent}"):
                config_val_before = admin_object.config()[CONFIG_FIELD_TO_CHANGE]
                is_denied(
                    action_owner_object,
                    business_role,
                    data={"config": {ACTION_CONFIG_ARGUMENT: "This you seen't"}},
                    client=user_client,
                )
                config_val_after = admin_object.config()[CONFIG_FIELD_TO_CHANGE]
                assert (
                    config_val_before == config_val_after
                ), f"Config value should stay the same for object {get_object_represent(admin_object)}"


@pytest.mark.extra_rbac()
def test_host_actions(clients, actions_cluster, actions_cluster_bundle, actions_provider, user):
    """Test permissions on host actions"""
    host_action_template = "{object_type} ready for host"
    service_name, component_name = "actions_service", "single_component"

    actions_service = actions_cluster.service(name=service_name)
    single_component = actions_service.component(name=component_name)

    second_cluster = actions_cluster_bundle.cluster_create(name="Test Second Cluster")
    second_cluster.service_add(name=service_name)

    with allure.step("Add hosts to clusters"):
        first_host = actions_provider.host()
        second_host = actions_provider.host_create(fqdn="test-new-host")
        for cluster, host in ((actions_cluster, first_host), (second_cluster, second_host)):
            cluster.host_add(host)
            service = cluster.service(name=service_name)
            component = service.component(name=component_name)
            cluster.hostcomponent_set((host, component))

    cluster, *_ = cluster_objects = actions_cluster, actions_service, single_component

    with allure.step("Grant permission to run host actions on cluster, service and component"):
        business_roles = [
            action_business_role(
                obj,
                host_action_template.format(object_type=obj.__class__.__name__),
                action_on_host=first_host,
            )
            for obj in cluster_objects
        ]
        policy = create_action_policy(
            clients.admin,
            cluster,
            *business_roles,
            user=user,
        )

        host, *_ = as_user_objects(clients.user, first_host)

    with allure.step("Run host actions from cluster, service and component on host in and out of cluster"):
        for role in business_roles:
            is_allowed(host, role).wait()
            is_denied(second_host, role, client=clients.user)

    with allure.step("Check policy deletion leads to denial of host action execution"):
        delete_policy(policy)
        for role in business_roles:
            is_denied(first_host, role, client=clients.user)
            is_denied(second_host, role, client=clients.user)


@pytest.mark.extra_rbac()
def test_action_on_host_available_with_cluster_parametrization(clients, actions_cluster, actions_provider, user):
    """Test that host owned action is still available"""
    admin_host = actions_provider.host()
    admin_cluster = actions_cluster
    admin_cluster.host_add(admin_host)

    cluster_business_role, host_business_role = action_business_role(
        admin_cluster, DO_NOTHING_ACTION
    ), action_business_role(admin_host, DO_NOTHING_ACTION)
    policy = create_action_policy(clients.admin, admin_cluster, cluster_business_role, host_business_role, user=user)

    user_cluster, user_host = as_user_objects(clients.user, actions_cluster, admin_host)

    is_allowed(user_cluster, cluster_business_role).wait()
    is_allowed(user_host, host_business_role).wait()

    delete_policy(policy)
    is_denied(admin_cluster, cluster_business_role, client=clients.user)
    is_denied(admin_host, host_business_role, client=clients.user)


class TestPluginsPermissions:
    """
    Test that ADCM plugins doesn't require any specific permissions on objects
    rather than permissions to run actions
    """

    NEW_HOST = "new-host"

    @pytest.fixture()
    def cluster(self, sdk_client_fs):
        """Create cluster"""
        bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "plugins", "cluster"))
        return bundle.cluster_create(name="test cluster")

    @pytest.fixture()
    def provider(self, sdk_client_fs):
        """Create provider"""
        bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "plugins", "provider"))
        return bundle.provider_create(name="test provider")

    @pytest.mark.full()
    def test_run_plugins(self, clients, cluster, provider, user):
        """
        Test that ADCM plugins doesn't require any specific permissions on objects
        rather than permissions to run actions
        """
        self.check_run_provider_based_plugins(clients, provider, user)
        self.check_run_cluster_based_plugins(clients, cluster, provider, user)

    def check_run_provider_based_plugins(self, clients, provider: Provider, user):
        """Check add_host and remove_host permissions"""
        admin: ADCMClient = clients.admin
        with allure.step("Check add host on provider"):
            with self._with_policy(admin, "add_host", provider, user) as business_role:
                user_provider, *_ = as_user_objects(clients.user, provider)
                self._is_allowed(user_provider, business_role)
                assert self.NEW_HOST in {
                    h.fqdn for h in provider.host_list()
                }, f"{self.NEW_HOST} should be among existing hosts"
                host = admin.host(fqdn=self.NEW_HOST)
        with allure.step("Check remove host on host"):
            with self._with_policy(admin, "remove_host", host, user) as business_role:
                user_host, *_ = as_user_objects(clients.user, host)
                self._is_allowed(user_host, business_role)
                assert self.NEW_HOST not in {
                    h.fqdn for h in provider.host_list()
                }, f"{self.NEW_HOST} should not be among existing hosts"

    def check_run_cluster_based_plugins(self, clients, cluster, provider, user):
        """Check adcm_add_host_to_cluster, adcm_remove_host_from_cluster and adcm_hc plugins"""
        admin = clients.admin
        host = provider.host_create(fqdn=self.NEW_HOST)
        with allure.step("Check adcm_add_host_to_cluster"):
            with self._with_policy(admin, "add_host", cluster, user) as business_role:
                user_cluster, *_ = as_user_objects(clients.user, cluster)
                self._is_allowed(user_cluster, business_role)
                assert host.fqdn in {
                    h.fqdn for h in cluster.host_list()
                }, f"Host {host.fqdn} should be added to cluster"
        with allure.step("Check adcm_remove_host_from_cluster"):
            with self._with_policy(admin, "remove_host", cluster, user) as business_role:
                self._is_allowed(user_cluster, business_role)
                assert host.fqdn not in {
                    h.fqdn for h in cluster.host_list()
                }, f"Host {host.fqdn} should be removed from cluster"
        self._check_hostcomponent_change(clients, cluster, provider, user)

    @allure.step("Check HC map change")
    def _check_hostcomponent_change(self, clients, cluster, provider, user):
        """Check hostcomponent change plugin"""
        admin = clients.admin
        first, second = provider.host_create("first-host"), provider.host_create("second-host")
        cluster.host_add(first)
        cluster.host_add(second)
        service = cluster.service_add(name="test_service")
        component = service.component()
        cluster.hostcomponent_set((first, component))
        expected_hc_map = ((second.id, component.id),)
        with self._with_policy(admin, "change_hc_map", cluster, user) as business_role:
            user_cluster, *_ = as_user_objects(clients.user, cluster)
            self._is_allowed(user_cluster, business_role)
            hc_map = tuple((hc["host_id"], hc["component_id"]) for hc in cluster.hostcomponent())
            assert hc_map == expected_hc_map, f"HC map should be {expected_hc_map}, not {hc_map}"

    @contextmanager
    def _with_policy(self, admin_client, action_name: str, adcm_object, user) -> BusinessRole:
        """Helper to create policy and remove it after"""
        business_role = action_business_role(adcm_object, action_name)
        policy = create_action_policy(admin_client, adcm_object, business_role, user=user)
        yield business_role
        delete_policy(policy)

    def _is_allowed(self, adcm_object, business_role):
        """Check if action run is allowed and it succeeds"""
        assert is_allowed(adcm_object, business_role).wait() == "success", "Action should succeed"


# !===== Steps and checks =====!


@allure.step("Check only one permitted action is allowed on object")
def check_single_action_is_allowed_on_object(
    action_display_name: str,
    adcm_object: AnyADCMObject,
    user_sdk: ADCMClient,
    business_role: Optional[BusinessRole] = None,
):
    """Check that only one action is allowed on object and the access to others is denied"""
    allowed_object, *_ = as_user_objects(user_sdk, adcm_object)
    business_role = business_role or action_business_role(allowed_object, action_display_name)

    is_allowed(allowed_object, business_role).wait()
    for action_name in (a.display_name for a in adcm_object.action_list() if a.display_name != action_display_name):
        is_denied(adcm_object, action_business_role(adcm_object, action_name), client=user_sdk)


# !===== Utilities =====!


def get_all_cluster_tree_plain(cluster: Cluster) -> Tuple[Union[Cluster, Service, Component], ...]:
    """Get all cluster related elements (services and component) as a plain structure"""
    services = cluster.service_list()
    components = tuple(itertools.chain(*[s.component_list() for s in services]))
    return cluster, *services, *components
