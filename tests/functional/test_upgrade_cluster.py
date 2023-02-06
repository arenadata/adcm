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

# pylint: disable=redefined-outer-name

"""Tests for cluster upgrade"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Service
from adcm_pytest_plugin.docker.adcm import ADCM
from adcm_pytest_plugin.utils import catch_failed, get_data_dir
from coreapi.exceptions import ErrorMessage
from tests.functional.tools import BEFORE_UPGRADE_DEFAULT_STATE, get_object_represent


@pytest.fixture()
def old_bundle(sdk_client_fs) -> Bundle:
    """Get cluster bundle of previous version"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))


@pytest.fixture()
def upgradable_bundle(sdk_client_fs) -> Bundle:
    """Get cluster to upgrade to"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster"))


@pytest.mark.usefixtures("upgradable_bundle")
def test_upgrade_with_two_clusters(old_bundle):
    """Upgrade cluster when we have two created clusters from one bundle
    Scenario:
    1. Create two clusters from one bundle
    2. Upload upgradable bundle
    3. Upgrade first cluster
    4. Check that only first cluster was upgraded
    """
    with allure.step("Create two clusters from one bundle"):
        cluster_first = old_bundle.cluster_create("test")
        cluster_second = old_bundle.cluster_create("test2")
        service = cluster_first.service_add(name="zookeeper")
    with allure.step("Upgrade first cluster"):
        upgr_cl = cluster_first.upgrade(name="upgrade to 1.6")
        upgr_cl.do()
    with allure.step("Check that only first cluster was upgraded"):
        cluster_first.reread()
        service.reread()
        cluster_second.reread()
        assert cluster_first.prototype().version == "1.6"
        assert service.prototype().version == "3.4.11"
        assert cluster_second.prototype().version == "1.5"


@pytest.mark.usefixtures("upgradable_bundle")
def test_check_prototype(old_bundle):
    """Check prototype for service and cluster after upgrade"""
    with allure.step("Create test cluster"):
        cluster = old_bundle.cluster_create("test")
        cl_id_before = cluster.id
        service = cluster.service_add(name="zookeeper")
        serv_id_before = service.id
        cluster_proto_before = cluster.prototype()
        service_proto_before = service.prototype()
    with allure.step("Upgrade test cluster to 1.6"):
        upgr = cluster.upgrade(name="upgrade to 1.6")
        upgr.do()
    with allure.step("Check prototype"):
        cluster.reread()
        service.reread()
        cluster_proto_after = cluster.prototype()
        service_proto_after = service.prototype()
        assert cl_id_before == cluster.id
        assert serv_id_before == service.id
        assert cluster_proto_before.id != cluster_proto_after.id
        assert service_proto_before.id != service_proto_after.id


@pytest.mark.usefixtures("upgradable_bundle")
def test_multiple_upgrade_bundles(old_bundle):
    """Upgrade cluster multiple time from version to another"""
    with allure.step("Create upgradable cluster for multiple upgrade"):
        cluster = old_bundle.cluster_create("test")
    with allure.step("Upgrade cluster multiple time from version to another to 1.6"):
        upgr = cluster.upgrade(name="upgrade to 1.6")
        upgr.do()
    with allure.step("Upgrade second time cluster to 2"):
        cluster.reread()
        upgr = cluster.upgrade(name="upgrade 2")
        upgr.do()
    with allure.step("Check upgraded cluster"):
        cluster.reread()
        assert cluster.state == "upgradated"


def test_change_config(sdk_client_fs: ADCMClient, old_bundle):
    """Upgrade cluster with other config"""
    with allure.step("Create upgradable cluster with new change values"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster_new_change_values"))
        cluster = old_bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step("Set cluster and service config"):
        cluster_config_before = cluster.config()
        service_config_before = service.config()
        cluster_config_before["required"] = 25
        cluster_config_before["int_key"] = 245
        cluster_config_before["str-key"] = "new_value"
        service_config_before["required_service"] = 20
        service_config_before["int_key_service"] = 333
        cluster.config_set(cluster_config_before)
        service.config_set(service_config_before)
    with allure.step("Upgrade cluster with new change values to 1.6"):
        upgr = cluster.upgrade(name="upgrade to 1.6")
        upgr.do()
    with allure.step("Check upgraded cluster and service"):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert len(cluster_config_before.keys()) == len(cluster_config_after.keys())
        for key in cluster_config_before:
            assert cluster_config_before[key] == cluster_config_after[key]
        for key in service_config_before:
            assert service_config_before[key] == service_config_after[key]


@allure.issue("https://arenadata.atlassian.net/browse/ADCM-1971")
def test_upgrade_cluster_with_config_groups(sdk_client_fs):
    """Test upgrade cluster config groups"""
    with allure.step("Create cluster with different groups on config"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_groups"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster_with_groups"))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step("Upgrade cluster with new change values to 1.6"):
        upgrade = cluster.upgrade(name="upgrade to 1.6")
        upgrade.do()
    with allure.step("Assert that configs save success after upgrade"):
        cluster.config_set(
            {
                "attr": {
                    "activatable_group_with_ro": {"active": True},
                    "activatable_group": {"active": True},
                },
                "config": {
                    **cluster.config(),
                    "activatable_group_with_ro": {"readonly-key": "value"},
                    "activatable_group": {
                        "required": 10,
                        "writable-key": "value",
                        "readonly-key": "value",
                    },
                },
            }
        )
        service.config_set(
            {
                "attr": {
                    "activatable_group_with_ro": {"active": True},
                    "activatable_group": {"active": True},
                },
                "config": {
                    **service.config(),
                    "activatable_group_with_ro": {"readonly-key": "value"},
                    "activatable_group": {
                        "required": 10,
                        "writable-key": "value",
                        "readonly-key": "value",
                    },
                },
            }
        )


def test_cannot_upgrade_with_state(sdk_client_fs: ADCMClient, old_bundle):
    """Test upgrade should not be available ant stater"""
    with allure.step("Create upgradable cluster with unsupported state"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster_unsupported_state"))
        cluster = old_bundle.cluster_create("test")
    with allure.step("Upgrade cluster to 1.6 and then to 2"):
        upgr = cluster.upgrade(name="upgrade to 1.6")
        upgr.do()
        cluster.reread()
        assert len(cluster.upgrade_list()) == 0, "No upgrade should be available"


@pytest.mark.usefixtures("upgradable_bundle")
def test_before_upgrade_state(old_bundle):
    """Test that field "before_upgrade" field has correct values"""
    with allure.step("Check `before_upgrade` field is correct before upgrade"):
        cluster = old_bundle.cluster_create(name="Test Cluster")
        assert (
            actual_state := cluster.before_upgrade["state"]
        ) == BEFORE_UPGRADE_DEFAULT_STATE, (
            f"Expected before_upgrade state was {BEFORE_UPGRADE_DEFAULT_STATE}, but {actual_state} was found"
        )
    with allure.step("Check `before_upgrade` field is correct after upgrade"):
        state_before_upgrade = cluster.state
        cluster.upgrade().do()
        cluster.reread()
        assert (
            actual_state := cluster.before_upgrade["state"]
        ) == state_before_upgrade, (
            f"Expected before_upgrade state was {state_before_upgrade}, but {actual_state} was found"
        )


class TestUpgradeWithComponent:
    """Test upgrade of cluster with cluster changes"""

    _DIR = "upgrade_with_components"
    _GEN_CONFIG = {"some_param": "pam-pam"}
    _SERVICE_NAME = "test_service"

    @pytest.fixture()
    def old_cluster(self, sdk_client_fs) -> Cluster:
        """Create cluster from old cluster bundle"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, self._DIR, "old"))
        cluster = bundle.cluster_create("Test Cluster of Old")
        cluster.service_add(name=self._SERVICE_NAME)
        return cluster

    @pytest.fixture()
    def new_bundle(self, sdk_client_fs) -> Bundle:
        """Upload new cluster bundle"""
        return sdk_client_fs.upload_from_fs(get_data_dir(__file__, self._DIR, "new"))

    @allure.issue(
        name="Component miss config after upgrade",
        url="https://arenadata.atlassian.net/browse/ADCM-2376",
    )
    @pytest.mark.usefixtures("new_bundle")
    def test_upgrade_with_components(self, adcm_fs, sdk_client_fs, old_cluster):
        """
        Test that upgrade where new version has changes in components are working fine
        """
        old_cluster.upgrade().do()
        new_cluster = sdk_client_fs.cluster(id=old_cluster.id)
        service = new_cluster.service(name=self._SERVICE_NAME)
        self.check_new_component_config_exists(service)
        self.check_config_existence_status_change(service)
        self.check_defaults_changed_correctly(service)
        self.check_new_file_in_config_was_created(adcm_fs, service)

    @allure.step("Check that config of component new in new version is presented")
    def check_new_component_config_exists(self, service: Service):
        """Check that component appeared in new version has config"""
        component = service.component(name="new_component")
        with catch_failed(ErrorMessage, f"Config of {get_object_represent(component)} should be available"):
            config = component.config()
        self._check_config(config, self._GEN_CONFIG)

    def check_config_existence_status_change(self, service: Service):
        """Check configs of components that have their configs added/cleared"""
        no_config_in_old_version = "waiting_for_config"
        no_config_in_new_version = "can_loose_config"

        with allure.step("Check that config was created for component that has no config before"):
            component = service.component(name=no_config_in_old_version)
            with catch_failed(ErrorMessage, f"Config of {get_object_represent(component)} should be available"):
                config = component.config()
            self._check_config(config, self._GEN_CONFIG)

        with allure.step("Check that config was removed from component that has config before"):
            component = service.component(name=no_config_in_new_version)
            self._check_config(component.config(), {})

    @allure.step("Check that new file field in config has corresponding file on FS")
    def check_new_file_in_config_was_created(self, adcm: ADCM, service: Service):
        """Check that new file field in config is created after upgrade"""
        files_dir = "/adcm/data/file"
        component = service.component(name="component_new_file")
        expected_file = f"component.{component.id}.new_file."
        files = adcm.container.exec_run(["ls", "-a", files_dir]).output.decode("utf-8")
        assert (
            expected_file in files
        ), f'File "{expected_file}" should be presented in "{files_dir}", but dir contains:\n{files}'

    @allure.step("Check defaults changed correctly")
    def check_defaults_changed_correctly(self, service: Service):
        """Check defaults changed correctly after upgrade"""
        component = service.component(name="defaults_changed")
        self._check_config(component.config(), {"will_have_default": 54, "have_default": 12})

    def _check_config(self, actual_config: str, expected_config: str):
        """Check configs are equal"""
        assert (
            actual_config == expected_config
        ), f"Config is not equal to the one that was expected.\nActual: {actual_config}\nExpected: {expected_config}"
