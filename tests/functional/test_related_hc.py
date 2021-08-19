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

# pylint: disable=too-many-locals

import os
from contextlib import contextmanager
from typing import List

import allure
import pytest
import yaml
from _pytest.mark import ParameterSet
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import random_string, get_data_dir, get_data_subdirs_as_parameters
from coreapi.exceptions import ErrorMessage

CASES_PATH = "cases"


@contextmanager
def _does_not_raise():
    yield


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
            added_host = created_cluster.host_add(
                provider.host_create(fqdn=f"fqdn_{random_string()}")
            )
            for service_with_component in case_template["hc_map"][host]:
                service_name, component_name = service_with_component.split(".")
                service = _get_or_add_service(created_cluster, service_name)
                hostcomponent_list.append((added_host, service.component(name=component_name)))
        expectation = (
            _does_not_raise() if case_template["positive"] else pytest.raises(ErrorMessage)
        )
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
