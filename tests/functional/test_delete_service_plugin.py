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

"""Tests for delete_service plugin"""

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils
import allure


def test_delete_service_plugin(sdk_client_fs: ADCMClient):
    """Check that delete service plugin will delete service"""
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create(utils.random_string())
    service = cluster.service_add(name="service")
    task = service.action(name='remove_service').run()
    task.wait()
    with allure.step("Check that service has been deleted"):
        assert task.status == 'success', f"Current job status {task.status}. Expected: success"
        assert not cluster.service_list(), "Service list should be empty"


def test_delete_service_with_import(sdk_client_fs: ADCMClient):
    """Check that possible to delete exported service from cluster"""
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'export_cluster'))
    bundle_import = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'import_cluster'))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster import")
    service = cluster.service_add(name="hadoop")
    cluster_import.bind(service)
    task = service.action(name='remove_service').run()
    task.wait()
    with allure.step("Check that service has been deleted and imports were cleaned"):
        assert task.status == 'success', f"Current job status {task.status}. Expected: success"
        assert not cluster.service_list(), "Service list should be empty"
        assert not cluster_import.service_list(), "Import list should be empty"


def test_delete_service_with_export(sdk_client_fs: ADCMClient):
    """Check that possible to delete imported service"""
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'export_cluster'))
    bundle_import = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'import_cluster'))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster import")
    service = cluster.service_add(name="hadoop")
    import_service = cluster_import.service_add(name='hadoop')
    import_service.bind(service)
    task = service.action(name='remove_service').run()
    task.wait()
    with allure.step("Check that service has been deleted and imports from other service are still present"):
        assert task.status == 'success', f"Current job status {task.status}. Expected: success"
        assert not cluster.service_list(), "Service list should be empty"
        assert cluster_import.service_list(), "Import list should not be empty"
    task = import_service.action(name='remove_service').run()
    task.wait()
    with allure.step("Check that service has been deleted and imports were cleaned"):
        assert task.status == 'success', f"Current job status {task.status}. Expected: success"
        assert not cluster_import.service_list(), "Import list should be empty"


def test_delete_service_with_host(sdk_client_fs: ADCMClient):
    """Check that it is possible to delete service with host component binded to cluster
    And HC map is automatically updated after service deletion"""
    hostprovider_bundle = sdk_client_fs.upload_from_fs(
        utils.get_data_dir(__file__, 'cluster_service_hostcomponent', 'hostprovider')
    )
    provider = hostprovider_bundle.provider_create("test")
    host_1 = provider.host_create("test-host-1")
    host_2 = provider.host_create("test-host-2")
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'cluster_service_hostcomponent', 'cluster'))
    cluster = bundle.cluster_create("test")
    service_1 = cluster.service_add(name="zookeeper")
    service_2 = cluster.service_add(name="second_service")
    cluster.host_add(host_1)
    cluster.host_add(host_2)
    component_1 = service_1.component(name="ZOOKEEPER_SERVER")
    component_2 = service_2.component(name="some_component")
    cluster.hostcomponent_set((host_1, component_1), (host_2, component_1), (host_2, component_2))
    assert len(cluster.service_list()) == 2, "It should be 2 services"
    assert len(cluster.hostcomponent()) == 3, "HC map should contain 3 mappings"
    task = service_1.action(name='remove_service').run()
    task.wait()
    with allure.step("Check that service has been deleted and HC map was cleaned"):
        assert task.status == 'success', f"Current job status {task.status}. Expected: success"
        assert len(cluster.service_list()) == 1, "It should be 1 service"
        assert cluster.service_list()[0].name == "second_service", "It should be only second service left"
        assert len(cluster.hostcomponent()) == 1, "HC map should contain 1 mapping"
    with allure.step("Check that there is no issues on objects"):
        cluster.reread()
        assert not cluster.concerns(), "It should be no concerns on cluster"
        host_1.reread()
        assert not host_1.concerns(), "It should be no concerns on host"
        host_2.reread()
        assert not host_2.concerns(), "It should be no concerns on host"
