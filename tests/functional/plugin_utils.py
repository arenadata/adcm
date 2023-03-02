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
Common functions and helpers for testing plugins (state, multi_state, config)
"""

from collections.abc import Callable, Collection
from contextlib import contextmanager
from operator import methodcaller
from typing import TypeVar

import allure
import pytest
from _pytest.mark.structures import ParameterSet
from adcm_client.objects import (
    Action,
    ADCMClient,
    Cluster,
    Component,
    Host,
    Provider,
    Service,
)
from adcm_pytest_plugin import utils as plugin_utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_host_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
    wait_for_task_and_assert_result,
)

from tests.functional.tools import (
    ADCMObjects,
    AnyADCMObject,
    ClusterRelatedObject,
    ProviderRelatedObject,
    get_objects_via_pagination,
)

# value of object's field (e.g. "created" as value for state)
ADCMObjectField = TypeVar("ADCMObjectField")

DEFAULT_OBJECT_NAMES = ("first", "second")


def create_two_clusters(adcm_client: ADCMClient, caller_file: str, bundle_dir: str) -> tuple[Cluster, Cluster]:
    """
    Create two clusters with two services on each with "default object names"
    :param adcm_client: ADCM client
    :param caller_file: Pass __file__ here (it will be passed to get_data_dir alongside bundle_dir)
    :param bundle_dir: Bundle directory name (e.g. "cluster", "provider")
    """
    uploaded_bundle = adcm_client.upload_from_fs(plugin_utils.get_data_dir(caller_file, bundle_dir))
    first_cluster = uploaded_bundle.cluster_create(name=DEFAULT_OBJECT_NAMES[0])
    second_cluster = uploaded_bundle.cluster_create(name=DEFAULT_OBJECT_NAMES[1])
    clusters = (first_cluster, second_cluster)
    for cluster in clusters:
        for name in DEFAULT_OBJECT_NAMES:
            cluster.service_add(name=name)
    return clusters


def create_two_providers(adcm_client: ADCMClient, caller_file: str, bundle_dir: str) -> tuple[Provider, Provider]:
    """
    Create two providers with two hosts
    :param adcm_client: ADCM client
    :param caller_file: Pass __file__ here (it will be passed to get_data_dir alongside bundle_dir)
    :param bundle_dir: Bundle directory name (e.g. "cluster", "provider")
    """
    uploaded_bundle = adcm_client.upload_from_fs(plugin_utils.get_data_dir(caller_file, bundle_dir))
    first_provider = uploaded_bundle.provider_create(name=DEFAULT_OBJECT_NAMES[0])
    second_provider = uploaded_bundle.provider_create(name=DEFAULT_OBJECT_NAMES[1])
    providers = (first_provider, second_provider)
    for provider in providers:
        for suffix in DEFAULT_OBJECT_NAMES:
            provider.host_create(fqdn=f"{provider.name}-{suffix}")
    return providers


def generate_cluster_success_params(action_prefix: str, id_template: str) -> list[ParameterSet]:
    """
    Generate successful multi_state_set params for cluster objects:

    - "Multi State Set" Action name (as string)
    - Tuple to identify object  that is going to be changed
    - Tuple to identify object  that is going to run action

    :param action_prefix: Prefix to `object` part of actions to run.
                          If you pass 'set', then actions will be like:
                          'set_component', 'set_first_service_first_component'.
    :param id_template: Template that will be used to compose an id.
                        It should be smt like 'set_{object_type}_multi_state'.
                        In that example id's will be like:
                        'set_cluster_multi_state_from_service',
                        'set_service_multi_state_from_component'.
    """
    cluster = ("first",)

    first_service = (*cluster, "first")
    first_service_first_component = (*first_service, "first")
    first_service_second_component = (*first_service, "second")

    second_service = (*cluster, "second")
    second_service_first_component = (*second_service, "first")
    return [
        *[
            pytest.param(
                f"{action_prefix}_cluster",
                cluster,
                from_obj_func,
                id=id_template.format("cluster") + f"_from_{from_obj_id}",
            )
            for from_obj_func, from_obj_id in (
                (cluster, "self"),
                (first_service, "service"),
                (first_service_first_component, "component"),
            )
        ],
        *[
            pytest.param(
                f"{action_prefix}_service",
                first_service,
                from_obj_func,
                id=id_template.format("service") + f"_from_{from_obj_id}",
            )
            for from_obj_func, from_obj_id in (
                (first_service, "self"),
                (first_service_first_component, "component"),
            )
        ],
        pytest.param(
            f"{action_prefix}_component",
            first_service_first_component,
            first_service_first_component,
            id=id_template.format("component") + "_from_self",
        ),
        *[
            pytest.param(
                f"{action_prefix}_first_service",
                first_service,
                from_obj_func,
                id=id_template.format("service") + f"_from_{from_obj_id}",
            )
            for from_obj_func, from_obj_id in (
                (first_service, "self_by_name"),
                (cluster, "cluster"),
                (second_service, "another_service"),
                (second_service_first_component, "another_service_component"),
            )
        ],
        *[
            pytest.param(
                f"{action_prefix}_first_component",
                first_service_first_component,
                from_obj_func,
                id=id_template.format("component") + f"_from_{from_obj_id}",
            )
            for from_obj_func, from_obj_id in (
                (first_service_first_component, "self_by_name"),
                (first_service, "service"),
                (first_service_second_component, "another_component"),
            )
        ],
        *[
            pytest.param(
                f"{action_prefix}_first_service_first_component",
                first_service_first_component,
                from_obj_func,
                id=id_template.format("component") + f"_from_{from_obj_id}",
            )
            for from_obj_func, from_obj_id in (
                (first_service_first_component, "self_by_service_component_name"),
                (cluster, "cluster"),
                (second_service, "another_service"),
                (second_service_first_component, "component_from_another_service"),
            )
        ],
    ]


def generate_provider_success_params(action_prefix: str, id_template: str) -> list[ParameterSet]:
    """
    Generate successful params for provider objects:

    - "Multi State Set" Action name (as string)
    - Tuple to identify object that is going to be changed
    - Tuple to identify object  that is going to run action

    :param action_prefix: Prefix to `object` part of actions to run.
                          If you pass 'set', then actions will be like:
                          'set_component', 'set_first_service_first_component'.
    :param id_template: Template that will be used to compose an id.
                        It should be smt like 'set_{object_type}_multi_state'.
                        In that example id's will be like:
                        'set_cluster_multi_state_from_service',
                        'set_service_multi_state_from_component'.
    """
    provider = ("first",)
    host = (*provider, "first-first")

    return [
        pytest.param(
            f"{action_prefix}_provider",
            provider,
            provider,
            id=id_template.format("provider") + "_from_self",
        ),
        pytest.param(
            f"{action_prefix}_provider",
            provider,
            host,
            id=id_template.format("provider") + "_from_host",
        ),
        pytest.param(f"{action_prefix}_host", host, host, id=id_template.format("host") + "_from_self"),
    ]


def get_cluster_related_object(
    client: ADCMClient,
    cluster: str = "first",
    service: str | None = None,
    component: str | None = None,
) -> ClusterRelatedObject:
    """
    Get function to get one of ADCM cluster objects:

    - Cluster (when all args are None)
    - Service (when only service argument is not None)
    - Component (when both arguments are not None)
    """
    if service is None and component is None:
        return client.cluster(name=cluster)
    if service and component is None:
        return client.cluster(name=cluster).service(name=service)
    if service and component:
        return client.cluster(name=cluster).service(name=service).component(name=component)
    raise ValueError('You can provide either only "service" argument or both "service" and "component" argument')


def get_provider_related_object(
    client: ADCMClient,
    provider: str = "first",
    host: str | None = None,
) -> ProviderRelatedObject:
    """
    Get function to get one of ADCM provider objects:

    - Provider (host is None)
    - Host (host FQDN is provided)
    """
    if host is None:
        return client.provider(name=provider)
    return client.provider(name=provider).host(fqdn=host)


def compose_name(adcm_object: AnyADCMObject) -> str:
    """
    Compose "good and readable" name from adcm_object
    based on description or name, but on FQDN if object is Host
    """
    if isinstance(adcm_object, Host):
        return f'Host "{adcm_object.fqdn}"'
    if description := getattr(adcm_object, "description", ""):
        return description
    return f'{adcm_object.__class__.__name__} "{adcm_object.name}"'


def build_objects_comparator(
    field_name: str,
    get_compare_value: Callable[[AnyADCMObject], ADCMObjectField],
    name_composer: Callable[[AnyADCMObject], str] = compose_name,
) -> Callable[[AnyADCMObject, ADCMObjectField], None]:
    """Get function to compare value of ADCM object's field with expected one"""

    def compare(adcm_object: AnyADCMObject, expected_value: ADCMObjectField):
        adcm_object_name = name_composer(adcm_object)
        adcm_object.reread()
        with allure.step(f"Assert that {adcm_object_name} has {expected_value} in {field_name.lower()} value"):
            assert (
                actual_value := get_compare_value(adcm_object)
            ) == expected_value, f"{field_name} of {adcm_object_name} should be {expected_value}, not {actual_value}"

    return compare


def build_objects_checker(
    changed: ADCMObjectField,
    extractor: Callable[[AnyADCMObject], ADCMObjectField],
    comparator: Callable[[AnyADCMObject, ADCMObjectField], None] | None = None,
    field_name: str | None = None,
) -> Callable[..., None]:
    """
    Get context manager to check that only particular objects were changed

    :param changed: Value expected to be found in ADCM object's attribute after changes made
    :param extractor: Function that returns value of ADCM object's attribute that will be compared
    :param comparator: Function that takes ADCM object and value to compare as arguments
                       and asserts that ADCM object's value is the same as given one.
                       If it's not provided, then default is build using build_objects_comparator.
                       If you use default, then it's better to provide field_name,
                       otherwise assertion message will be uninformative.
    :param field_name: Provide name of "to change" field to use default allure step title template
    """
    if comparator is None:
        comparator = build_objects_comparator(
            get_compare_value=extractor,
            field_name=field_name if field_name else "Attribute",
        )

    title = (
        f"Check {field_name.lower()} of presented objects changed correctly"
        if field_name
        else "Check objects changed correctly"
    )

    @contextmanager
    def wrapped(
        adcm_client: ADCMClient,
        changed_objects: Collection[ClusterRelatedObject] = (),
        changed: ADCMObjectField = changed,
        allure_step_title: str = title,
    ):
        unchanged_attributes = freeze_objects_attribute(
            adcm_client,
            extractor,
            to_ignore=_build_ignore_map(changed_objects),
        )

        yield

        with allure.step(allure_step_title):
            for adcm_object in changed_objects:
                comparator(adcm_object, changed)

        with allure.step("Check other objects was left intact"):
            unchanged_components = unchanged_attributes.pop(Component)
            for object_class, id_attr_map in unchanged_attributes.items():
                get_method_name = object_class.__name__.lower()
                for object_id, unchanged_value in id_attr_map.items():
                    get_object_by_id = methodcaller(get_method_name, id=object_id)
                    comparator(get_object_by_id(adcm_client), unchanged_value)
            __check_components(
                adcm_client,
                comparator,
                components=unchanged_components,
                service_ids=unchanged_attributes[Service].keys(),
            )

    return wrapped


@allure.step("Save objects configurations before changes")
def freeze_objects_attribute(
    adcm_client: ADCMClient,
    get_attribute_func: Callable[[AnyADCMObject], ADCMObjectField],
    to_ignore: dict[type[AnyADCMObject], set[int]],
):
    """
    Freeze all "dummies" (objects created before this fixture was called
    by getting some value from objects (with callable provided in param)
    and saving it to dict of following structure:
    {
        Cluster: {cluster_id: value},
        Service: {service_id: value},
        Component: {component_id: value},
        Provider: {provider_id: value},
        Host: {host_id: value},
    }
    """
    frozen_objects = {cls: {} for cls in ADCMObjects}

    def freeze(obj: AnyADCMObject):
        if (obj_id := obj.id) not in to_ignore[(obj_class := obj.__class__)]:
            frozen_objects[obj_class][obj_id] = get_attribute_func(obj)

    for cluster in adcm_client.cluster_list():
        freeze(cluster)
        for service in cluster.service_list():
            freeze(service)
            for component in get_objects_via_pagination(service.component_list):
                freeze(component)
    for provider in adcm_client.provider_list():
        freeze(provider)
        for host in get_objects_via_pagination(provider.host_list):
            freeze(host)
    return frozen_objects


def run_successful_task(action: Action, action_owner_name: str):
    """Run action and expect it succeeds"""
    task = action.run()
    try:
        wait_for_task_and_assert_result(task, status="success")
    except AssertionError as error:
        raise AssertionError(
            f"Action {action.name} should have succeeded when ran on {action_owner_name}:\n{error}",
        ) from error


def _build_ignore_map(objects_to_ignore: Collection[AnyADCMObject]):
    """Returns map with ids of objects to ignore grouped by class"""
    # may be empty
    ignore_map = {cls: set() for cls in ADCMObjects}
    for obj in objects_to_ignore:
        ignore_map[obj.__class__].add(obj.id)
    return ignore_map


def __check_components(
    adcm_client: ADCMClient,
    comparator: Callable,
    components: dict[int, ADCMObjectField],
    service_ids: Collection[int],
):
    """Check components config is intact since .component is not implemented"""
    component_ids = components.keys()
    for service in (adcm_client.service(id=sid) for sid in service_ids):
        for component in get_objects_via_pagination(service.component_list):
            if (component_id := component.id) in component_ids:
                comparator(component, components[component_id])


# !===== Common test classes =====!


class TestImmediateChange:
    """
    Utility class to test that config/state/multi-state has changed immediately in playbook.
    Value of _file will be passed to `get_data_dir` function as first argument.
    """

    _file = None
    _action = "check_multijob"
    _cluster_bundle_name = "immediate_change_cluster"
    _provider_bundle_name = "immediate_change_provider"

    @pytest.fixture()
    def provider_host(self, sdk_client_fs: ADCMClient) -> tuple[Provider, Host]:
        """Get provider and host created for immediate change testing"""
        uploaded_bundle = sdk_client_fs.upload_from_fs(
            plugin_utils.get_data_dir(self._file, self._provider_bundle_name),
        )
        provider = uploaded_bundle.provider_create("Nicer")
        return provider, provider.host_create("good-fqdn")

    @pytest.fixture()
    def cluster_service_component(
        self,
        provider_host: tuple[Provider, Host],
        sdk_client_fs: ADCMClient,
    ) -> tuple[Cluster, Service, Component]:
        """Get cluster, service and component with added service and host for immediate config change"""
        uploaded_bundle = sdk_client_fs.upload_from_fs(
            plugin_utils.get_data_dir(self._file, self._cluster_bundle_name),
        )
        cluster = uploaded_bundle.cluster_create("Cooler")
        _, host = provider_host
        cluster.host_add(host)
        service = cluster.service_add(name="test_service")
        component = service.component()
        cluster.hostcomponent_set((host, component))
        return cluster, service, component

    def run_immediate_change_test(
        self,
        provider_host: tuple[Provider, Host],
        cluster_service_component: tuple[Cluster, Service, Component],
    ):
        """
        Run the same action (self._action) for cluster, service, component, provider, host
            and expect them to succeed
        """
        cluster, service, component = cluster_service_component
        provider, host = provider_host
        run_cluster_action_and_assert_result(cluster, self._action)
        run_service_action_and_assert_result(service, self._action)
        run_component_action_and_assert_result(component, self._action)
        run_provider_action_and_assert_result(provider, self._action)
        run_host_action_and_assert_result(host, self._action)
