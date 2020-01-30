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
import coreapi
import pytest

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir
from tests.library import errorcodes as err


def test_upgrade_cluster_with_import(sdk_client_fs: ADCMClient):
    """Scenario:
    1. Create cluster for upgrade with exports
    2. Create upgradable cluster with imports
    3. Bind service and cluster
    4. Upgrade cluster
    5. Check that cluster was upgraded
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgrade_cluster_with_export'))
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_with_import'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="hadoop")
    cluster_config_before = cluster.config()
    service_config_before = service.config()
    cluster_import = bundle_import.cluster_create("cluster_import")
    cluster_import.bind(service)
    cluster_import.bind(cluster)
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    assert cluster.prototype().version == '1.6'
    assert service.prototype().version == '2.2'
    for variable in cluster_config_before:
        assert cluster_config_before[variable] == cluster_config_after[variable]
    for variable in service_config_before:
        assert service_config_before[variable] == service_config_after[variable]


def test_upgrade_cluster_with_export(sdk_client_fs: ADCMClient):
    """Scenario:
    1. Create cluster for upgrade with export
    2. Create cluster for upgrade with import
    3. Load upgradable bundle with import
    4. Bind service and cluster
    5. Upgrade cluster with import
    6. Check that cluster was upgraded
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_with_export'))
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgrade_cluster_with_import'))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_with_import'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="hadoop")
    cluster_import = bundle_import.cluster_create("cluster_import")
    cluster_import.bind(service)
    cluster_import.bind(cluster)
    upgr = cluster_import.upgrade(name='upgrade to 1.6')
    id_before = cluster_import.prototype_id
    upgr.do()
    cluster_import.reread()
    assert cluster_import.prototype().version == '1.6'
    assert cluster_import.prototype_id != id_before


def test_incorrect_import_version(sdk_client_fs: ADCMClient):
    """Upgrade cluster with service incorrect version

    :param sdk_client_fs:
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgrade_cluster_with_export'))
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_with_incorrect_version'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="hadoop")
    cluster_import = bundle_import.cluster_create("cluster_import")
    cluster_import.bind(service)
    cluster_import.bind(cluster)
    upgr = cluster.upgrade(name='upgrade to 1.6')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    err.UPGRADE_ERROR.equal(e)


@pytest.mark.xfail(reason="ADCM-1113")
def test_upgrade_cluster_without_service_config_in_import(sdk_client_fs: ADCMClient):
    """Upgrade cluster with service when in new cluster
     we haven't some service configuration variables
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgrade_cluster_with_export'))
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_without_service'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="hadoop")
    cluster_import = bundle_import.cluster_create("cluster_import")
    cluster_import.bind(service)
    cluster_import.bind(cluster)
    upgr = cluster.upgrade(name='upgrade to 1.6')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    err.UPGRADE_ERROR.equal(e)


def test_upgrade_cluster_with_new_configuration_variables(sdk_client_fs: ADCMClient):
    """Upgrade to cluster with new configuration variables
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgrade_cluster_with_export'))
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_with_import_new_config_vars'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="hadoop")
    cluster_config_before = cluster.config()
    service_config_before = service.config()
    cluster_import = bundle_import.cluster_create("cluster_import")
    cluster_import.bind(service)
    cluster_import.bind(cluster)
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    assert cluster.prototype().version == '1.6'
    assert service.prototype().version == '2.2'
    assert len(cluster_config_after) == 4, cluster_config_after
    assert len(service_config_after) == 3, service_config_after
    for variable in cluster_config_before:
        assert cluster_config_before[variable] == cluster_config_after[variable]
    for variable in service_config_before:
        assert service_config_before[variable] == service_config_after[variable]
