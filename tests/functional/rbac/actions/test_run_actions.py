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
from collections import defaultdict
from contextlib import contextmanager
from typing import Type, Dict, Optional, List, Union, Callable, Tuple, Generator

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Service, Component, User

from tests.functional.tools import AnyADCMObject, get_object_represent
from tests.functional.rbac.conftest import BusinessRole, delete_policy, is_denied, is_allowed, as_user_objects
from tests.functional.rbac.actions.utils import action_business_role, create_action_policy


DO_NOTHING_ACTION = 'Do nothing'

CONFIG_FIELD_TO_CHANGE = 'longstring'
ACTION_CONFIG_ARGUMENT = 'valofarg'
CHANGE_ACTION_NAME_TEMPLATE = 'Change {object_type} Configuration'


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
    service = cluster.service(name='actions_service')
    component = service.component(name='simple_component')
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
        (user_object,) = as_user_objects(user_sdk, adcm_object)
        business_role = action_business_role(adcm_object, DO_NOTHING_ACTION)
        policy = create_action_policy(admin_sdk, adcm_object, business_role, user=user)

        check_single_action_is_allowed_on_object(DO_NOTHING_ACTION, adcm_object, user_sdk, business_role)

    with allure.step(f"Check that granted permission doesn't allow running '{DO_NOTHING_ACTION}' on other objects"):
        with user_objects_map(
            user_sdk,
            [adcm_object],
            *all_objects,
            exclude_predicate=_do_nothing_action_not_presented,
        ) as objects_map:
            check_action_is_not_allowed_on_objects(DO_NOTHING_ACTION, objects_map)

    with allure.step('Check permission withdrawn'):
        delete_policy(policy)
        is_denied(user_object, business_role)


@pytest.mark.extra_rbac()
def test_config_change_via_plugin(clients, user, actions_cluster, actions_provider):
    """
    Test that permission on action run is enough for changing configuration with plugins.
    Config change action has its own config.
    """
    cluster, service, component = as_user_objects(
        clients.user,
        actions_cluster,
        (serv := actions_cluster.service(name='config_changing_service')),
        serv.component(name='config_changing_component'),
    )
    provider, host = as_user_objects(clients.user, actions_provider, actions_provider.host())

    _test_config_change(cluster, (cluster,), user=user, admin_client=clients.admin)
    _test_config_change(service, (cluster, service), user=user, admin_client=clients.admin)
    _test_config_change(component, (cluster, service, component), user=user, admin_client=clients.admin)

    _test_config_change(provider, (provider,), user=user, admin_client=clients.admin)
    _test_config_change(host, (provider, host), user=user, admin_client=clients.admin)


def _test_config_change(
    action_owner_object: AnyADCMObject,
    objects_to_change: Tuple[AnyADCMObject, ...],
    admin_client: ADCMClient,
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

        for adcm_object, business_role in object_role_map:
            admin_object = as_user_objects(admin_client, adcm_object)[0]
            config_field_value = admin_object.config()[CONFIG_FIELD_TO_CHANGE]
            new_value = f'{config_field_value}_{adcm_object.__class__.__name__}'
            with allure.step(f'Try to change {get_object_represent(admin_object)} from {owner_object_represent}'):
                task = is_allowed(action_owner_object, business_role, config={ACTION_CONFIG_ARGUMENT: new_value})
                assert task.wait() == 'success', 'Action should succeeded'
                assert (
                    admin_object.config()[CONFIG_FIELD_TO_CHANGE] == new_value
                ), f"Config of object {get_object_represent(admin_object)} should've been changed"

    with allure.step('Delete policy and check actions are denied and config stays the same'):
        delete_policy(policy)
        for adcm_object, business_role in object_role_map:
            admin_object = as_user_objects(admin_client, adcm_object)[0]
            with allure.step(f'Try to change {get_object_represent(admin_object)} from {owner_object_represent}'):
                config_val_before = admin_object.config()[CONFIG_FIELD_TO_CHANGE]
                is_denied(action_owner_object, business_role, config={ACTION_CONFIG_ARGUMENT: "This you seen't"})
                config_val_after = admin_object.config()[CONFIG_FIELD_TO_CHANGE]
                assert (
                    config_val_before == config_val_after
                ), f'Config value should stay the same for object {get_object_represent(admin_object)}'


@pytest.mark.extra_rbac()
def test_host_actions(clients, actions_cluster, actions_cluster_bundle, actions_provider, user):
    """Test permissions on host actions"""
    host_action_template = '{object_type} ready for host'
    service_name, component_name = 'actions_service', 'single_component'

    actions_service = actions_cluster.service(name=service_name)
    single_component = actions_service.component(name=component_name)

    second_cluster = actions_cluster_bundle.cluster_create(name='Test Second Cluster')
    second_cluster.service_add(name=service_name)

    with allure.step('Add hosts to clusters'):
        first_host = actions_provider.host()
        second_host = actions_provider.host_create(fqdn='test-new-host')
        for cluster, host in ((actions_cluster, first_host), (second_cluster, second_host)):
            cluster.host_add(host)
            service = cluster.service(name=service_name)
            component = service.component(name=component_name)
            cluster.hostcomponent_set((host, component))

    host, second_host = as_user_objects(clients.user, first_host, second_host)
    cluster, _, _ = user_cluster_objects = as_user_objects(
        clients.user, actions_cluster, actions_service, single_component
    )

    with allure.step('Grant permission to run host actions on cluster, service and component'):
        business_roles = [
            action_business_role(obj, host_action_template.format(object_type=obj.__class__.__name__))
            for obj in user_cluster_objects
        ]
        policy = create_action_policy(
            clients.admin,
            cluster,
            *business_roles,
            user=user,
        )

    with allure.step('Run host actions from cluster, service and component on host in and out of cluster'):
        for role in business_roles:
            is_allowed(host, role).wait()
            is_denied(second_host, role)

    with allure.step('Check policy deletion leads to denial of host action execution'):
        delete_policy(policy)
        for role in business_roles:
            is_denied(host, role)
            is_denied(second_host, role)


@pytest.mark.extra_rbac()
def test_action_on_host_available_with_cluster_parametrization(clients, actions_cluster, actions_provider, user):
    """Test that host owned action is still available"""
    admin_host = actions_provider.host()
    actions_cluster.host_add(admin_host)
    user_cluster, user_host = as_user_objects(clients.user, actions_cluster, admin_host)
    cluster_business_role, host_business_role = action_business_role(
        user_cluster, DO_NOTHING_ACTION
    ), action_business_role(user_host, DO_NOTHING_ACTION)
    policy = create_action_policy(clients.admin, user_cluster, cluster_business_role, host_business_role, user=user)
    is_allowed(user_cluster, cluster_business_role).wait()
    is_allowed(user_host, host_business_role).wait()

    delete_policy(policy)
    is_denied(user_cluster, cluster_business_role)
    is_denied(user_host, host_business_role)


# !===== Steps and checks =====!


@allure.step("Check only one permitted action is allowed on object")
def check_single_action_is_allowed_on_object(
    action_display_name: str,
    adcm_object: AnyADCMObject,
    user_sdk: ADCMClient,
    business_role: Optional[BusinessRole] = None,
):
    """Check that only one action is allowed on object and the access to others is denied"""
    (allowed_object,) = as_user_objects(user_sdk, adcm_object)
    business_role = business_role or action_business_role(allowed_object, action_display_name)

    is_allowed(allowed_object, business_role).wait()
    for action_name in (a.display_name for a in adcm_object.action_list() if a.display_name != action_display_name):
        is_denied(allowed_object, action_business_role(allowed_object, action_name))


@allure.step("Check actions aren't allowed on objects they don't suppose to")
def check_action_is_not_allowed_on_objects(action_display_name: str, objects_to_deny: Dict[Type, Dict[int, object]]):
    """Check that provided action (by display name) is not allowed to run on any of provided objects"""
    for object_map in objects_to_deny.values():
        for adcm_object in object_map.values():
            is_denied(adcm_object, action_business_role(adcm_object, action_display_name))


# !===== Utilities =====!


@contextmanager
def user_objects_map(
    user_sdk,
    exclude_objects: List[AnyADCMObject],
    *objects: AnyADCMObject,
    exclude_predicate: Callable[[AnyADCMObject], bool] = None,
) -> Generator[Dict[Type, Dict[int, AnyADCMObject]], None, None]:
    """
    Get objects map in format:
    {
      classname: {
        object_id: object (from user sdk)
      }
    }

    Inside the context following objects are removed from map:
    1. Ones that are listed in `exclude_objects`.
    2. Ones that satisfies the exclude_predicate.
    After the context is left all excluded objects are returned to the map.

    P.S. You can improve this manager by adding `full_map` argument that will operate on existing map
         (if you'll need to reuse map that was constructed during previous call).
    """
    full_map = defaultdict(dict)
    user_objects = as_user_objects(user_sdk, *objects)

    for obj in user_objects:
        full_map[obj.__class__][obj.id] = obj

    filtered = list(filter(exclude_predicate, user_objects)) if exclude_predicate else []

    exclude_set = set((obj.__class__, obj.id) for obj in (exclude_objects + filtered))
    excluded = tuple((full_map[cls].pop(object_id) for cls, object_id in exclude_set))

    yield full_map

    for obj in excluded:
        full_map[obj.__class__][obj.id] = obj


def get_all_cluster_tree_plain(cluster: Cluster) -> Tuple[Union[Cluster, Service, Component], ...]:
    """Get all cluster related elements (services and component) as a plain structure"""
    services = cluster.service_list()
    components = tuple(itertools.chain(*[s.component_list() for s in services]))
    return cluster, *services, *components
