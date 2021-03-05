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

import allure
import pytest
import yaml
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import random_string, get_data_dir, get_data_subdirs_as_parameters
from coreapi.exceptions import ErrorMessage

CASES_PATH = "/cases"


def _get_or_add_service(cluster, service_name):
    """
    Add service if it wasn't added before and return it
    """
    try:
        return cluster.service(name=service_name)
    except ObjectNotFound:
        return cluster.service_add(name=service_name)


def get_cases_paths() -> dict:
    """
    Get cases path for parametrize test
    """
    bundles_paths, bundles_ids = get_data_subdirs_as_parameters(__file__, "bundle_configs")
    cases_paths = []
    ids = []
    for i, bundle_path in enumerate(bundles_paths):
        for b in os.listdir(bundle_path + CASES_PATH):
            cases_paths.append("{}/{}".format(bundle_path + CASES_PATH, b))
            ids.append(f"{bundles_ids[i]}_{b.strip('.yaml')}")
    return {"argvalues": cases_paths, "ids": ids}


@pytest.mark.parametrize("relation_type", ["bound_to", "requires"])
@pytest.mark.parametrize("case_path", **get_cases_paths())
def test_related_sc(sdk_client_fs: ADCMClient, relation_type, case_path):
    """
    Tests for related components on hosts
    https://arenadata.atlassian.net/browse/ADCM-1535
    https://arenadata.atlassian.net/browse/ADCM-1633
    """
    with allure.step('Upload custom provider bundle and create it in ADCM'):
        provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/provider")
        provider = provider_bundle.provider_prototype().provider_create(random_string())
    with allure.step('Upload custom cluster bundle and create it in ADCM'):
        bundle_path = os.path.join(case_path.split(CASES_PATH)[0], relation_type)
        if not os.path.exists(os.path.join(bundle_path, "config.yaml")):
            pytest.skip(f"bundle for relation type '{relation_type}' does not exist")
        cluster_bundle = sdk_client_fs.upload_from_fs(bundle_path)
        created_cluster = cluster_bundle.cluster_prototype().cluster_create(random_string())
    with allure.step('Parse case description from YAML file and set host-component map'):
        with open(case_path) as file:
            case_template = yaml.safe_load(file)
        allure.dynamic.description(case_template["description"])
        if f"skip_if_{relation_type}" in case_template:
            pytest.skip(f"test skipped by config for relation type {relation_type}")
        hostcomponent_list = []
        for host in case_template["hc_map"].keys():
            added_host = created_cluster.host_add(
                provider.host_create(fqdn=f"fqdn_{random_string()}"))
            for service_with_component in case_template["hc_map"][host]:
                service_name, component_name = service_with_component.split(".")
                service = _get_or_add_service(created_cluster, service_name)
                hostcomponent_list.append(
                    (added_host, service.component(name=component_name))
                )

        @contextmanager
        def _does_not_raise():
            yield

        expectation = (
            pytest.raises(ErrorMessage)
            if f"{relation_type}_raise_exception" in case_template else
            _does_not_raise()
        )
        with expectation:
            created_cluster.hostcomponent_set(*hostcomponent_list)
