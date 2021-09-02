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

from typing import Union, Callable, Any, TypeVar, Collection, Type, Optional, List, Tuple

import allure
import pytest

from _pytest.mark.structures import ParameterSet
from adcm_pytest_plugin import utils as plugin_utils
from adcm_client.objects import Cluster, Service, Component, Provider, Host, ADCMClient

ClusterRelatedObject = Union[Cluster, Service, Component]
ProviderRelatedObject = Union[Provider, Host]
AnyADCMObject = Union[ClusterRelatedObject, ProviderRelatedObject]
ADCMObjectField = TypeVar('ADCMObjectField')

DEFAULT_OBJECT_NAMES = ('first', 'second')


def generate_cluster_success_params(action_prefix: str, id_template: str) -> List[ParameterSet]:
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
    cluster = ('first',)

    first_service = (*cluster, 'first')
    first_service_first_component = (*first_service, 'first')
    first_service_second_component = (*first_service, 'second')

    second_service = (*cluster, 'second')
    second_service_first_component = (*second_service, 'first')
    return [
        *[
            pytest.param(
                f'{action_prefix}_cluster',
                cluster,
                from_obj_func,
                id=id_template.format('cluster') + f'_from_{from_obj_id}',
            )
            for from_obj_func, from_obj_id in (
                (cluster, 'self'),
                (first_service, 'service'),
                (first_service_first_component, 'component'),
            )
        ],
        *[
            pytest.param(
                f'{action_prefix}_service',
                first_service,
                from_obj_func,
                id=id_template.format('service') + f'_from_{from_obj_id}',
            )
            for from_obj_func, from_obj_id in ((first_service, 'self'), (first_service_first_component, 'component'))
        ],
        pytest.param(
            f'{action_prefix}_component',
            first_service_first_component,
            first_service_first_component,
            id=id_template.format('component') + '_from_self',
        ),
        *[
            pytest.param(
                f'{action_prefix}_first_service',
                first_service,
                from_obj_func,
                id=id_template.format('service') + f'_from_{from_obj_id}',
            )
            for from_obj_func, from_obj_id in (
                (first_service, 'self_by_name'),
                (cluster, 'cluster'),
                (second_service, 'another_service'),
                (second_service_first_component, 'another_service_component'),
            )
        ],
        *[
            pytest.param(
                f'{action_prefix}_first_component',
                first_service_first_component,
                from_obj_func,
                id=id_template.format('component') + f'_from_{from_obj_id}',
            )
            for from_obj_func, from_obj_id in (
                (first_service_first_component, 'self_by_name'),
                (first_service, 'service'),
                (first_service_second_component, 'another_component'),
            )
        ],
        *[
            pytest.param(
                f'{action_prefix}_first_service_first_component',
                first_service_first_component,
                from_obj_func,
                id=id_template.format('component') + f'_from_{from_obj_id}',
            )
            for from_obj_func, from_obj_id in (
                (first_service_first_component, 'self_by_service_component_name'),
                (cluster, 'cluster'),
                (second_service, 'another_service'),
                (second_service_first_component, 'component_from_another_service'),
            )
        ],
    ]


def generate_provider_success_params(action_prefix: str, id_template: str) -> List[ParameterSet]:
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
    provider = ('first',)
    host = (*provider, 'first-first')

    return [
        pytest.param(f'{action_prefix}_provider', provider, provider, id=id_template.format('provider') + '_from_self'),
        pytest.param(f'{action_prefix}_provider', provider, host, id=id_template.format('provider') + '_from_host'),
        pytest.param(f'{action_prefix}_host', host, host, id=id_template.format('host') + '_from_self'),
    ]


def get_cluster_related_object(
    client: ADCMClient, cluster: str = 'first', service: Optional[str] = None, component: Optional[str] = None
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
    client: ADCMClient, provider: str = 'first', host: Optional[str] = None
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
    if description := getattr(adcm_object, 'description', ''):
        return description
    return f'{adcm_object.__class__.__name__} "{adcm_object.name}"'


def build_objects_comparator(
    get_compare_field: Callable[[AnyADCMObject], ADCMObjectField],
    field_name: str,
    field_converter: Callable[[Any], ADCMObjectField] = str,
) -> Callable[[AnyADCMObject, ADCMObjectField], None]:
    """Get function to compare value of ADCM object's field with expected one"""

    def compare(adcm_object: AnyADCMObject, expected_value: Union[ADCMObjectField, Collection[ADCMObjectField]]):
        adcm_object_name = compose_name(adcm_object)
        adcm_object.reread()
        assert (
            actual_value := field_converter(get_compare_field(adcm_object))
        ) == expected_value, f'{field_name} of {adcm_object_name} should be {expected_value}, not {actual_value}'

    return compare


def build_objects_checker(
    parent_type: Union[Type[Cluster], Type[Provider]],
    comparator: Callable[[AnyADCMObject, ADCMObjectField], None],
    changed: ADCMObjectField,
    unchanged: ADCMObjectField,
    allure_message: str,
) -> Callable[..., None]:
    """
    Get function to check that particular objects were changed (has value of some field equals to changed).
    """
    if parent_type == Cluster:
        return _check_cluster_related_objects(comparator, changed, unchanged, allure_message)
    if parent_type == Provider:
        return _check_provider_related_objects(comparator, changed, unchanged, allure_message)
    raise ValueError('parent_type should be either Cluster or Provider class')


def _check_cluster_related_objects(
    comparator: Callable[[AnyADCMObject, ADCMObjectField], None],
    changed: ADCMObjectField,
    unchanged: ADCMObjectField,
    allure_message: str,
) -> Callable[[ADCMClient, Collection[ClusterRelatedObject], Optional[ADCMObjectField]], None]:
    """Returns function to check state of cluster related objects"""

    @allure.step(allure_message)
    def wrapped(
        adcm_client: ADCMClient,
        changed_adcm_objects: Collection[ClusterRelatedObject] = (),
        alternative_changed: Optional[ADCMObjectField] = None,
    ):
        actual_changed = alternative_changed if alternative_changed else changed
        for adcm_object in changed_adcm_objects:
            comparator(adcm_object, actual_changed)

        cluster_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Cluster)}
        service_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Service)}
        component_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Component)}
        for cluster in adcm_client.cluster_list():
            if cluster.id not in cluster_ids:
                comparator(cluster, unchanged)
            for service in cluster.service_list():
                if service.id not in service_ids:
                    comparator(service, unchanged)
                for component in service.component_list():
                    if component.id not in component_ids:
                        comparator(component, unchanged)

    return wrapped


def _check_provider_related_objects(
    comparator: Callable[[AnyADCMObject, ADCMObjectField], None],
    changed: ADCMObjectField,
    unchanged: ADCMObjectField,
    allure_message: str,
) -> Callable[[ADCMClient, Collection[ProviderRelatedObject], Optional[ADCMObjectField]], None]:
    """Returns function to check state of provider related objects"""

    @allure.step(allure_message)
    def wrapped(
        adcm_client: ADCMClient,
        changed_adcm_objects: Collection[ProviderRelatedObject] = (),
        alternative_changed: Optional[ADCMObjectField] = None,
    ):
        actual_changed = alternative_changed if alternative_changed else changed
        for adcm_object in changed_adcm_objects:
            comparator(adcm_object, actual_changed)
        provider_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Provider)}
        host_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Host)}
        for provider in adcm_client.provider_list():
            if provider.id not in provider_ids:
                comparator(provider, unchanged)
            for host in provider.host_list():
                if host.id not in host_ids:
                    comparator(host, unchanged)

    return wrapped


def create_two_clusters(adcm_client: ADCMClient, caller_file: str, bundle_dir: str) -> Tuple[Cluster, Cluster]:
    """
    Create two clusters with two services on each with "default object names"
    :param adcm_client: ADCM client
    :param caller_file: Pass __file__ here
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


def create_two_providers(adcm_client: ADCMClient, caller_file: str, bundle_dir: str) -> Tuple[Provider, Provider]:
    """
    Create two providers with two hosts
    :param adcm_client: ADCM client
    :param caller_file: Pass __file__ here
    :param bundle_dir: Bundle directory name (e.g. "cluster", "provider")
    """
    uploaded_bundle = adcm_client.upload_from_fs(plugin_utils.get_data_dir(caller_file, bundle_dir))
    first_provider, second_provider, *_ = [uploaded_bundle.provider_create(name=name) for name in DEFAULT_OBJECT_NAMES]
    providers = (first_provider, second_provider)
    for provider in providers:
        for suffix in DEFAULT_OBJECT_NAMES:
            provider.host_create(fqdn=f'{provider.name}-{suffix}')
    return providers
