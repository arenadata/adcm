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

# pylint:disable=redefined-outer-name

"""Tests for delete service with active import"""

import allure
import coreapi
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir
from tests.library import errorcodes as err


@pytest.fixture()
def service(sdk_client_fs: ADCMClient):
    """Create service"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_export"))
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_import"))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster import")
    service = cluster.service_add(name="hadoop")
    cluster_import.bind(service)
    return service


@pytest.fixture()
def service_import(sdk_client_fs: ADCMClient):
    """Create service with import"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_export"))
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_service_import"))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster import")
    service = cluster.service_add(name="hadoop")
    import_service = cluster_import.service_add(name="hadoop")
    import_service.bind(service)
    return service


def test_delete_service_with_with_active_export(service):
    """If host has NO component, than we can simple remove it from cluster"""
    with allure.step("Delete service"):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            service.delete()
    with allure.step("Check service conflict"):
        err.SERVICE_CONFLICT.equal(e)


def test_delete_service_with_active_export_for_service(service_import):
    """Add test for bind service"""
    with allure.step("Delete imported to cluster service"):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            service_import.delete()
    with allure.step("Check service conflict"):
        err.SERVICE_CONFLICT.equal(e)
