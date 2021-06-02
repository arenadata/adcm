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
# pylint: disable=W0611, W0621
import allure
import coreapi
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import parametrize_by_data_subdirs

from tests.library import errorcodes as err


@parametrize_by_data_subdirs(__file__, "service_import_check_negative")
def test_service_import_negative(sdk_client_fs: ADCMClient, path):
    """Create service with incorrect version in import cluster
    Scenario:
    1. Create cluster with import
    2. Create cluster with export
    3. Bind service from cluster with export to cluster with import
    4. Expect backend error because incorrect version for import
    """
    with allure.step('Create cluster with def export'):
        bundle = sdk_client_fs.upload_from_fs(path + '/export')
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
    with allure.step('Create cluster with def import'):
        bundle_import = sdk_client_fs.upload_from_fs(path + '/import')
        cluster_import = bundle_import.cluster_create("cluster_import")
    with allure.step('Bind service from cluster with export to cluster with import'):
        cluster_import.bind(cluster)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        cluster_import.bind(service)
    with allure.step('Expect backend error because incorrect version for import'):
        err.BIND_ERROR.equal(e)


@parametrize_by_data_subdirs(__file__, "cluster_import_check_negative")
def test_cluster_import_negative(sdk_client_fs: ADCMClient, path):
    """Create cluster with incorrect version in import cluster
    Scenario:
    1. Create cluster with import
    2. Create cluster with export
    3. Bind cluster from cluster with export to cluster with import
    4. Expect backend error because incorrect version for import
    """
    with allure.step('Create cluster with export and add service'):
        bundle = sdk_client_fs.upload_from_fs(path + '/export')
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
    with allure.step('Create default cluster with import'):
        bundle_import = sdk_client_fs.upload_from_fs(path + '/import')
        cluster_import = bundle_import.cluster_create("cluster_import")
    with allure.step('Bind cluster from cluster with export to cluster with import'):
        cluster_import.bind(service)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        cluster_import.bind(cluster)
    with allure.step('Check error because incorrect version for import'):
        err.BIND_ERROR.equal(e)


@parametrize_by_data_subdirs(__file__, "service_import")
def test_service_import(sdk_client_fs: ADCMClient, path):
    """Import service test"""
    with allure.step('Create cluster with export and service test'):
        bundle = sdk_client_fs.upload_from_fs(path + '/export')
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
    with allure.step('Create cluster with import'):
        bundle_import = sdk_client_fs.upload_from_fs(path + '/import')
        cluster_import = bundle_import.cluster_create("cluster_import")
    with allure.step('Bind service from cluster with export to cluster with import'):
        cluster_import.bind(service)


@parametrize_by_data_subdirs(__file__, "cluster_import")
def test_cluster_import(sdk_client_fs: ADCMClient, path):
    """Import cluster test"""
    with allure.step('Create test cluster with export'):
        bundle = sdk_client_fs.upload_from_fs(path + '/export')
        cluster = bundle.cluster_create("test")
    with allure.step('Create cluster with import'):
        bundle_import = sdk_client_fs.upload_from_fs(path + '/import')
        cluster_import = bundle_import.cluster_create("cluster_import")
    with allure.step('Bind cluster from cluster with export to cluster with import'):
        cluster_import.bind(cluster)
