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

"""Tests host-components: bound_to, requires, constraints"""

# pylint: disable=too-many-locals, redefined-outer-name

import os
from contextlib import nullcontext
from typing import List, Literal

import allure
import pytest
import yaml
from _pytest.mark import ParameterSet
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient, Bundle, Cluster, Provider
from adcm_pytest_plugin.utils import (
    catch_failed,
    get_data_dir,
    get_data_subdirs_as_parameters,
    random_string,
)
from coreapi.exceptions import ErrorMessage
from tests.functional.conftest import only_clean_adcm

CASES_PATH = "cases"
CONSTRAINTS_DIR = get_data_dir(__file__, 'bundle_configs', 'constraints')


expect_hostcomponent_set_success = catch_failed(ErrorMessage, 'Host component set should not fail')
expect_hostcomponent_set_fail = pytest.raises(ErrorMessage)


def _get_or_add_service(cluster, service_name):
    """
    Add service if it wasn't added before and return it
    """
    try:
        return cluster.service(name=service_name)
    except ObjectNotFound:
        return cluster.service_add(name=service_name)


def _get_cases_paths(path: str) -> List[ParameterSet]:
    """
    Get cases path for parametrize test
    """
    bundles_paths, bundles_ids = get_data_subdirs_as_parameters(__file__, "bundle_configs", path)
    params = []
    for i, bundle_path in enumerate(bundles_paths):
        for sub_path in ["positive", "negative"]:
            case_dir = os.path.join(bundle_path, CASES_PATH, sub_path)
            for bundle_file in os.listdir(case_dir):
                params.append(
                    pytest.param(
                        os.path.join(case_dir, bundle_file),
                        id=f"{bundles_ids[i]}_{sub_path}_{bundle_file.strip('.yaml')}",
                    )
                )
    return params


def _test_related_hc(client: ADCMClient, case_path: str):
    with allure.step("Upload custom provider bundle and create it in ADCM"):
        provider_bundle = client.upload_from_fs(get_data_dir(__file__) + "/provider")
        provider = provider_bundle.provider_prototype().provider_create(random_string())
    with allure.step("Upload custom cluster bundle and create it in ADCM"):
        bundle_path = case_path.split(CASES_PATH)[0]
        cluster_bundle = client.upload_from_fs(bundle_path)
        created_cluster = cluster_bundle.cluster_prototype().cluster_create(random_string())
    with allure.step("Parse case description from YAML file and set host-component map"):
        with open(case_path, encoding='utf_8') as file:
            case_template = yaml.safe_load(file)
        allure.dynamic.description(case_template["description"])
        hostcomponent_list = []
        for host in case_template["hc_map"].keys():
            added_host = created_cluster.host_add(provider.host_create(fqdn=f"fqdn-{random_string()}"))
            for service_with_component in case_template["hc_map"][host]:
                service_name, component_name = service_with_component.split(".")
                service = _get_or_add_service(created_cluster, service_name)
                hostcomponent_list.append((added_host, service.component(name=component_name)))
        expectation = nullcontext() if case_template["positive"] else pytest.raises(ErrorMessage)
        with expectation:
            created_cluster.hostcomponent_set(*hostcomponent_list)


@allure.link(url="https://arenadata.atlassian.net/browse/ADCM-1535", name="Test cases")
@pytest.mark.parametrize("case_path", _get_cases_paths("bound_to"))
def test_bound_hc(sdk_client_fs: ADCMClient, case_path: str):
    """
    Tests for bound components on hosts
    """
    _test_related_hc(sdk_client_fs, case_path)


@allure.link(url="https://arenadata.atlassian.net/browse/ADCM-1633", name="Test cases")
@pytest.mark.parametrize("case_path", _get_cases_paths("requires"))
def test_required_hc(sdk_client_fs: ADCMClient, case_path: str):
    """
    Tests for required components on hosts
    """
    _test_related_hc(sdk_client_fs, case_path)


# Test constraints


def parametrize_by_constraint(case_type: Literal['positive', 'negative']):
    """Parametrize tests by "cases.yaml" file"""
    test_arg_names = ('constraint', 'hosts_amounts')
    parameters = []
    ids = []

    with open(os.path.join(CONSTRAINTS_DIR, 'cases.yaml'), 'rb') as file:
        constraints_cases = yaml.safe_load(file)['constraints']

    for constraint, cases in constraints_cases.items():
        if not cases[case_type]:
            continue
        hosts = cases[case_type]
        parameters.append((constraint, hosts))
        constraint_id = f'constraint_{constraint}'.replace('+', 'plus')
        hosts_id = f'hosts_{"_".join(map(str, hosts))}'
        ids.append(f'{constraint_id}_{hosts_id}')

    return pytest.mark.parametrize(test_arg_names, parameters, ids=ids)


def _test_constraint(
    constraint: str,
    hosts_amounts: List[int],
    cluster_bundle: Bundle,
    provider: Provider,
    expectation_message: str,
    expectation_context,
):
    service_name = f'service_{constraint}'
    for amount in hosts_amounts:
        with allure.step(f'Try to add component on {amount}'):
            new_cluster_name = random_string(12)
            with allure.step(f'Create cluster {new_cluster_name}'):
                cluster = cluster_bundle.cluster_create(new_cluster_name)
                component = cluster.service_add(name=service_name).component()
            with allure.step(f'Create {amount} hosts and add them to a cluster {new_cluster_name}'):
                hosts = [cluster.host_add(provider.host_create(f'{new_cluster_name}-{i}')) for i in range(amount)]
            with allure.step(f'Map component to {amount} hosts and expect it to {expectation_message}'):
                hc_map = _enrich_hc_map(cluster, provider, hc_map=tuple((host, component) for host in hosts))
                with expectation_context:
                    cluster.hostcomponent_set(*hc_map)


@pytest.fixture()
def cluster_bundle(sdk_client_fs) -> Bundle:
    """Upload cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(CONSTRAINTS_DIR, 'various_hc'))


@pytest.fixture()
def provider(sdk_client_fs) -> Provider:
    """Upload provider bundle and create provider"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'provider'))
    return bundle.provider_create(f'Provider {random_string(6)}')


@only_clean_adcm
@parametrize_by_constraint('positive')
def test_hostcomponent_constraints_positive(constraint: str, hosts_amounts: List[int], cluster_bundle, provider):
    """
    Tests for constraints on components (positive cases)
    """
    _test_constraint(constraint, hosts_amounts, cluster_bundle, provider, 'succeed', expect_hostcomponent_set_success)


@only_clean_adcm
@parametrize_by_constraint('negative')
def test_hostcomponent_constraints_negative(constraint: str, hosts_amounts: List[int], cluster_bundle, provider):
    """
    Tests for constraints on components (negative cases)
    """
    _test_constraint(constraint, hosts_amounts, cluster_bundle, provider, 'fail', expect_hostcomponent_set_fail)


@only_clean_adcm
def test_hostcomponent_plus_constraint(cluster_bundle, provider):
    """
    Test positive and negative cases with [+] constraint
    """
    cluster = cluster_bundle.cluster_create('Test Cluster')
    component = cluster.service_add(name='service_+').component()
    hosts = [cluster.host_add(provider.host_create(f'host-{i}')) for i in range(5)]
    not_all_hosts = hosts[:-1]
    with allure.step(
        f'Try to set HC with component on {len(not_all_hosts)} of {len(hosts)} hosts and expect it to fail'
    ):
        with expect_hostcomponent_set_fail:
            cluster.hostcomponent_set(*[(h, component) for h in not_all_hosts])
    with allure.step('Try to set HC with component on all hosts and expect it to succeed'):
        with expect_hostcomponent_set_success:
            cluster.hostcomponent_set(*[(h, component) for h in hosts])


def _enrich_hc_map(cluster: Cluster, provider: Provider, hc_map: tuple) -> tuple:
    """
    Add component from another service (without constraints)
    if current check required amount == 0 (to provide not empty hc map)
    """
    if hc_map:
        # if it's not empty then no need to add any hc
        return hc_map
    with allure.step('Add component without constraints to hc_map'):
        component = cluster.service_add(name='service_without_constraints').component()
        host = cluster.host_add(provider.host_create(f'host-{cluster.name}-{random_string(6)}'))
        return ((host, component),)
