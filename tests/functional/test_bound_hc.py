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
import os

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


class CasesPathsForParametrize:
    def __init__(self, case_paths, ids):
        self.cases_paths = case_paths
        self.ids = ids


def get_cases_paths() -> CasesPathsForParametrize:
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
    return CasesPathsForParametrize(cases_paths, ids)


cases_paths_param = get_cases_paths()


@allure.link(url="https://arenadata.atlassian.net/browse/ADCM-1535", name="Test cases")
@pytest.mark.parametrize("case_path", cases_paths_param.cases_paths, ids=cases_paths_param.ids)
def test_binded_hc(sdk_client_fs: ADCMClient, case_path):
    """
    Tests for binded components on hosts
    https://arenadata.atlassian.net/browse/ADCM-1535
    """
    with allure.step('Upload custom provider bundle and create it in ADCM'):
        provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/provider")
        provider = provider_bundle.provider_prototype().provider_create(random_string())
    with allure.step('Upload custom cluster bundle and create it in ADCM'):
        cluster_bundle = sdk_client_fs.upload_from_fs(case_path.split(CASES_PATH)[0])
        created_cluster = cluster_bundle.cluster_prototype().cluster_create(random_string())
    with allure.step('Parse case description from YAML file and set host-component map'):
        with open(case_path) as file:
            case_template = yaml.safe_load(file)
        allure.dynamic.description(case_template["description"])
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
        if case_template["positive"] is False:
            with pytest.raises(ErrorMessage):
                created_cluster.hostcomponent_set(*hostcomponent_list)
        else:
            created_cluster.hostcomponent_set(*hostcomponent_list)
