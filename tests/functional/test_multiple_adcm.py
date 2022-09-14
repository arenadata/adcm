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
Test cases that include two ADCM instances and their interaction
"""

# pylint: disable=redefined-outer-name

from typing import Set, Iterable, Tuple

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient, Provider, Cluster
from adcm_pytest_plugin.utils import get_data_dir, catch_failed
from adcm_pytest_plugin.docker_utils import copy_file_to_container, ADCM
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.steps.commands import dump_cluster, load_cluster

from tests.library.assertions import sets_are_equal, dicts_are_equal
from tests.functional.tools import AnyADCMObject, get_object_represent


CLUSTER_NAME = 'test cluster to export'
PROVIDER_NAME = 'test_provider_to_export'
DEFAULT_CONFIG_SERVICE = 'service_with_defaults'
CHANGED_CONFIG_SERVICE = 'service_with_changed_config'

SECRET_FIELDS = ('password', 'secrettext')
CHANGED_CONFIG = {
    'string': 'customstringval',
    'text': 'custom\ntextval',
    'secrettext': 'secret\ntextval2',
    'boolean': True,
    'integer': 42,
    'float': 5.3,
    'password': 'cleverpass',
    'variant': 'pa',
    'option': 443,
    'list': ['pa', 'ram'],
    'map': {'name': 'noname'},
    'json': {'whole': {'another': 0, 'story': 1}},
    'file': 'new\nfile\ncontent\n',
}


@pytest.fixture()
def second_adcm_sdk(extra_adcm_fs: ADCM, adcm_api_credentials) -> ADCMClient:
    """Returns ADCMClient object from adcm_client"""
    return ADCMClient(url=extra_adcm_fs.url, **adcm_api_credentials)


@pytest.fixture()
def upload_bundle_to_both_adcm(bundle_archives, sdk_client_fs, second_adcm_sdk) -> None:
    """
    * Upload cluster and provider bundles to two ADCMs
    * Create cluster and provider on both
    * On the first only add services to the cluster
    * On the second add services and create some hosts
    """
    cluster_tar, provider_tar = bundle_archives

    cluster = sdk_client_fs.upload_from_fs(cluster_tar).cluster_create(CLUSTER_NAME)
    cluster.service_add(name=DEFAULT_CONFIG_SERVICE)
    cluster.service_add(name=CHANGED_CONFIG_SERVICE)

    sdk_client_fs.upload_from_fs(provider_tar).provider_create(PROVIDER_NAME)

    cluster_from_second_adcm = second_adcm_sdk.upload_from_fs(cluster_tar).cluster_create('Whoops Cluster')
    cluster_from_second_adcm.service_add(name=DEFAULT_CONFIG_SERVICE)
    cluster_from_second_adcm.service_add(name=CHANGED_CONFIG_SERVICE)
    provider_from_second_adcm = second_adcm_sdk.upload_from_fs(provider_tar).provider_create('Whoops Provider')
    for i in range(7):
        provider_from_second_adcm.host_create(f'second-adcm-host-{i}')


@pytest.mark.parametrize(
    'bundle_archives', [(get_data_dir(__file__, 'cluster'), get_data_dir(__file__, 'provider'))], indirect=True
)
@pytest.mark.usefixtures('upload_bundle_to_both_adcm')
def test_export_cluster_from_another_adcm(adcm_fs, extra_adcm_fs, sdk_client_fs, second_adcm_sdk):
    """
    Test basic scenario export of a cluster from one ADCM to another
    """

    provider = sdk_client_fs.provider(name=PROVIDER_NAME)
    cluster_to_export = sdk_client_fs.cluster(name=CLUSTER_NAME)

    hc_map = set_hc_map(cluster_to_export, provider)
    default_config = change_configurations(cluster_to_export)

    imported_cluster, _ = import_cluster_to_second_adcm(cluster_to_export.id, adcm_fs, extra_adcm_fs, second_adcm_sdk)

    check_configurations(imported_cluster, default_config)
    check_hc_map(hc_map, imported_cluster)


@allure.step('Import cluster from one ADCM to another')
def import_cluster_to_second_adcm(
    cluster_id: int, export_from_adcm: ADCM, import_to_adcm: ADCM, second_adcm_sdk: ADCMClient
) -> Tuple[Cluster, Provider]:
    """Import cluster from one ADCM to another and return cluster and provider from "new" ADCM"""
    password = 'unbreakablepassword'
    path_to_dump = '/adcm/data/cluster_dump'
    dump_cluster(export_from_adcm, cluster_id, path_to_dump, password)
    with allure.step('Copy file with cluster dump to "target" ADCM'):
        copy_file_to_container(export_from_adcm.container, import_to_adcm.container, path_to_dump, path_to_dump)
    load_cluster(import_to_adcm, path_to_dump, password)
    with catch_failed(
        ObjectNotFound, f'Either cluster "{CLUSTER_NAME}" or provider "{PROVIDER_NAME}" were not found after the import'
    ):
        return second_adcm_sdk.cluster(name=CLUSTER_NAME), second_adcm_sdk.provider(name=PROVIDER_NAME)


@allure.step('Create hosts and set HC to 1 host to 1 component, left 1 host in cluster unbind')
def set_hc_map(cluster: Cluster, provider: Provider):
    """
    * Create hosts for cluster and one free host
    * Add 3 hosts to a cluster
    * Map one component to one host and another one to another host
    * Return cleared HC map
    """
    hosts = [cluster.host_add(provider.host_create(f'host-{i}')) for i in range(3)]
    host_1, host_2, *_ = hosts
    provider.host_create('free-host')
    component_1, component_2, *_ = [s.component() for s in cluster.service_list()]
    return _clear_hc_map(cluster.hostcomponent_set((host_1, component_1), (host_2, component_2)))


@allure.step('Check HC and hosts bond to the cluster')
def check_hc_map(expected_hc_map: dict, cluster: Cluster):
    """Check hostcomponent map is correct after the import and all hosts that should be in cluster are still there"""
    actual_hc_map = _clear_hc_map(cluster.hostcomponent())
    sets_are_equal(actual_hc_map, expected_hc_map, 'Hostcomponent is incorrect after the import')
    sets_are_equal(
        {h.fqdn for h in cluster.host_list()},
        {f'host-{i}' for i in range(3)},
        'List of hosts in the cluster is incorrect',
    )


@allure.step('Change configurations of the cluster, 1 service and a component on it')
def change_configurations(cluster: Cluster) -> dict:
    """Change config of a cluster, one of its services and this service's component"""
    old_config = dict(cluster.config())
    changed_config = {**CHANGED_CONFIG}
    service = cluster.service(name=CHANGED_CONFIG_SERVICE)
    component = service.component()
    for adcm_object in (cluster, service, component):
        adcm_object.config_set(changed_config)
    _check_secrets(cluster)
    return old_config


def check_configurations(cluster: Cluster, default_config: dict):
    """Check config of cluster objects and then check secrets"""
    default_config_wo_secrets = _get_config_wo_secret_fields(default_config)
    changed_config_wo_secrets = _get_config_wo_secret_fields(CHANGED_CONFIG)
    objects_with_default_config = (service := cluster.service(name=DEFAULT_CONFIG_SERVICE)), service.component()
    objects_with_changed_config = (
        cluster,
        (service := cluster.service(name=CHANGED_CONFIG_SERVICE)),
        service.component(),
    )

    with allure.step('Check that one of services and its component have default config'):
        _check_configs_in_objects(default_config_wo_secrets, objects_with_default_config)

    with allure.step('Check that cluster, one of services and its component have changed config'):
        _check_configs_in_objects(changed_config_wo_secrets, objects_with_changed_config)

    _check_secrets(cluster)


def _check_configs_in_objects(expected_config: dict, objects: Iterable[AnyADCMObject]):
    for adcm_object in objects:
        actual_config = _get_config_wo_secret_fields(adcm_object.config())
        dicts_are_equal(
            actual_config,
            expected_config,
            f'Config of {get_object_represent(adcm_object)} is incorrect.\nCheck attachments for more details.',
        )


def _get_config_wo_secret_fields(config: dict) -> dict:
    return {key: value for key, value in config.items() if key not in SECRET_FIELDS}


@allure.step('Check secrets in config (password and secrettext) by action')
def _check_secrets(cluster):
    run_cluster_action_and_assert_result(cluster, 'check_secrets')


def _clear_hc_map(raw_hc) -> Set[str]:
    return {(hc['host'], hc['service_name'], hc['component']) for hc in raw_hc}
