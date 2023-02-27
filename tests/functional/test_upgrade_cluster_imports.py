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

"""Tests for upgrade cluster with imports"""

import allure
import coreapi
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir, parametrize_by_data_subdirs

from tests.library import errorcodes as err


@allure.step("Bind service and cluster")
def bind_service_and_cluster(cluster_import, service, cluster):
    """Bind service and cluster"""
    cluster_import.bind(service)
    cluster_import.bind(cluster)


def test_upgrade_cluster_with_import(sdk_client_fs: ADCMClient):
    """Scenario:
    1. Create cluster for upgrade with exports
    2. Create upgradable cluster with imports
    3. Bind service and cluster
    4. Upgrade cluster
    5. Check that cluster was upgraded
    """
    with allure.step("Create cluster with exports"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade_cluster_with_export"))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
        cluster_config_before = cluster.config()
        service_config_before = service.config()
    with allure.step("Create cluster for upgrade with imports"):
        bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster_with_import"))
        cluster_import = bundle_import.cluster_create("cluster import")
    bind_service_and_cluster(cluster_import, service, cluster)
    with allure.step("Upgrade cluster"):
        upgr = cluster.upgrade(name="upgrade to 1.6")
        upgr.do()
    with allure.step("Check that cluster was upgraded"):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert cluster.prototype().version == "1.6"
        assert service.prototype().version == "2.2"
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
    with allure.step("Create cluster for upgrade with exports"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_export"))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
    with allure.step("Create cluster for upgrade with imports. Load upgradable bundle with import"):
        bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade_cluster_with_import"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster_with_import"))
        cluster_import = bundle_import.cluster_create("cluster import")
    bind_service_and_cluster(cluster_import, service, cluster)
    with allure.step("Upgrade cluster with import to 1.6"):
        upgr = cluster_import.upgrade(name="upgrade to 1.6")
        id_before = cluster_import.prototype_id
        upgr.do()
    with allure.step("Check that cluster was upgraded"):
        cluster_import.reread()
        assert cluster_import.prototype().version == "1.6"
        assert cluster_import.prototype_id != id_before


@parametrize_by_data_subdirs(__file__, "upgradable_cluster_with_strict_incorrect_version")
def test_incorrect_import_strict_version(sdk_client_fs: ADCMClient, path):
    """Upgrade cluster with service incorrect strict version
    Scenario:
    1. Create cluster for upgrade with exports
    2. Create upgradable cluster with import
    3. Create upgradable cluster with import and incorrect strict version
    4. Create service
    5. Import service from cluster with export to cluster from step 2 (with import)
    6. Upgrade cluster from step 1
    7. Check that cluster was not upgraded because incorrect version for service
    in cluster with import
    """
    with allure.step("Create cluster for upgrade with exports for strict test"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade_cluster_with_export_for_strict_test"))
        sdk_client_fs.upload_from_fs(path)
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
    with allure.step("Create upgradable cluster with import"):
        bundle_import_correct = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_correct_import"))
        cluster_import = bundle_import_correct.cluster_create("cluster import")
    bind_service_and_cluster(cluster_import, service, cluster)
    with allure.step("Upgrade cluster with import with error"):
        upgr = cluster_import.upgrade(name="upgrade to 1.6")
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            upgr.do()
    with allure.step("Check that cluster was not upgraded"):
        err.UPGRADE_ERROR.equal(e)


@parametrize_by_data_subdirs(__file__, "upgradable_cluster_with_incorrect_version")
def test_incorrect_import_version(sdk_client_fs: ADCMClient, path):
    """Upgrade cluster with service incorrect version
    Scenario:
    1. Create cluster for upgrade with exports
    2. Create upgradable cluster with import and incorrect version
    3. Create service
    4. Import service from cluster with export to cluster from step 2 (with import)
    5. Upgrade cluster from step 1
    6. Check that cluster was not upgraded because incorrect version for service
    in cluster with import
    """
    with allure.step("Create cluster for upgrade with exports and cluster with correct import"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade_cluster_with_export"))
        sdk_client_fs.upload_from_fs(path)
        bundle_import_correct = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_correct_import"))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
        cluster_import = bundle_import_correct.cluster_create("cluster import")
    bind_service_and_cluster(cluster_import, service, cluster)
    with allure.step("Upgrade cluster with import to 1.6 with error"):
        upgr = cluster_import.upgrade(name="upgrade to 1.6")
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            upgr.do()
    with allure.step("Check that cluster was not upgraded"):
        err.UPGRADE_ERROR.equal(e)


def test_upgrade_cluster_without_service_config_in_import(sdk_client_fs: ADCMClient):
    """Upgrade cluster with service when in new cluster when
    we haven't some service configuration variables
    Scenario:
    1. Create cluster for upgrade with export
    2. Create upgradable cluster with import and without config in import
    3. Bind service from cluster with export to cluster with import
    4. Upgrade cluster with export
    5. Check upgrade error
    """
    with allure.step("Create cluster for upgrade with exports and cluster without config in import"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade_cluster_with_export"))
        bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster_without_service"))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
        cluster_import = bundle_import.cluster_create("cluster import")
    with allure.step("Bind service from cluster with export to cluster with import"):
        cluster_import.bind(service)
        cluster_import.bind(cluster)
    with allure.step("Upgrade cluster with export"):
        upgr = cluster.upgrade(name="upgrade to 1.6")
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            upgr.do()
    with allure.step("Check upgrade error"):
        err.UPGRADE_ERROR.equal(e)


def test_upgrade_cluster_with_new_configuration_variables(sdk_client_fs: ADCMClient):
    """Upgrade to cluster with new configuration variables"""
    with allure.step("Create cluster for upgrade with exports and cluster with import new config vars"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade_cluster_with_export"))
        bundle_import = sdk_client_fs.upload_from_fs(
            get_data_dir(__file__, "upgradable_cluster_with_import_new_config_vars"),
        )
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="hadoop")
        cluster_config_before = cluster.config()
        service_config_before = service.config()
        cluster_import = bundle_import.cluster_create("cluster import")
    bind_service_and_cluster(cluster_import, service, cluster)
    with allure.step("Upgrade cluster with export"):
        upgr = cluster.upgrade(name="upgrade to 1.6")
        upgr.do()
    with allure.step("Check upgraded cluster"):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert cluster.prototype().version == "1.6"
        assert service.prototype().version == "2.2"
        assert len(cluster_config_after) == 4, cluster_config_after
        assert len(service_config_after) == 3, service_config_after
        for variable in cluster_config_before:
            assert cluster_config_before[variable] == cluster_config_after[variable]
        for variable in service_config_before:
            assert service_config_before[variable] == service_config_after[variable]
