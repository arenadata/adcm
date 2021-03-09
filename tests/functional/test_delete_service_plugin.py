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
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils
import allure


def test_delete_service_plugin(sdk_client_fs: ADCMClient):
    """Check that delete service plugin will delete service
    """
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create(utils.random_string())
    service = cluster.service_add(name="service")
    task = service.action_run(name='remove_service')
    task.wait()
    with allure.step(f'Check that job state is {task.status}'):
        assert task.status == 'success', "Current job status {}. " \
                                         "Expected: success".format(task.status)
        assert not cluster.service_list()


def test_delete_service_with_import(sdk_client_fs: ADCMClient):
    """Check that possible to delete exported service from cluster
    """
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'export_cluster'))
    bundle_import = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'import_cluster'))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster_import")
    service = cluster.service_add(name="hadoop")
    cluster_import.bind(service)
    task = service.action_run(name='remove_service')
    task.wait()
    with allure.step(f'Check that job state is {task.status}'):
        assert task.status == 'success', "Current job status {}. " \
                                         "Expected: success".format(task.status)
        assert not cluster.service_list()
        assert not cluster_import.service_list()


def test_delete_service_with_export(sdk_client_fs: ADCMClient):
    """Check that possible to delete imported service
    """
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'export_cluster'))
    bundle_import = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'import_cluster'))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster_import")
    service = cluster.service_add(name="hadoop")
    import_service = cluster_import.service_add(name='hadoop')
    import_service.bind(service)
    task = service.action_run(name='remove_service')
    task.wait()
    with allure.step(f'Check that job state is {task.status}'):
        assert task.status == 'success', "Current job status {}. " \
                                         "Expected: success".format(task.status)
        assert not cluster.service_list()
        assert cluster_import.service_list()
    task = import_service.action_run(name='remove_service')
    task.wait()
    with allure.step(f'Check that job state is {task.status}'):
        assert task.status == 'success', "Current job status {}. " \
                                         "Expected: success".format(task.status)
        assert not cluster_import.service_list()


def test_delete_service_with_host(sdk_client_fs: ADCMClient):
    """Check that possible to delete service with host component binded to cluster
    """
    hostprovider_bundle = sdk_client_fs.upload_from_fs(
        utils.get_data_dir(__file__, 'cluster_service_hostcomponent', 'hostprovider'))
    provider = hostprovider_bundle.provider_create("test")
    host = provider.host_create("test_host")
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__,
                                                             'cluster_service_hostcomponent',
                                                             'cluster'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster.host_add(host)
    component = service.component(name="ZOOKEEPER_SERVER")
    cluster.hostcomponent_set((host, component))
    assert cluster.service_list()
    task = service.action_run(name='remove_service')
    task.wait()
    with allure.step(f'Check that job state is {task.status}'):
        assert task.status == 'success', "Current job status {}. " \
                                         "Expected: success".format(task.status)
        assert not cluster.service_list()
