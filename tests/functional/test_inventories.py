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

"""Tests for actions inventory"""

import json
from typing import Optional, Tuple
from uuid import uuid4

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import (
    ADCM,
    ADCMClient,
    Cluster,
    Component,
    Host,
    Provider,
    Service,
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker_utils import get_file_from_container
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import get_data_dir
from docker.models.containers import Container
from tests.functional.conftest import only_clean_adcm
from tests.functional.tools import (
    BEFORE_UPGRADE_DEFAULT_STATE,
    create_config_group_and_add_host,
    get_inventory_file,
)

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]


HOST_FQDN = 'awesome-future'
CLUSTER_NAME = 'dumMxpQA'
GROUP_COMPONENT_NAME = 'GROUP_BUDDY'

CONFIG_TO_CHANGE = {
    'config': {
        'json_field': {'there_is': 'no one'},
        'map_field': {'here': 'but me'},
        '__main_info': "I'm a very important string, don't touch me",
        'simple_field': 1,
    },
    'attr': {
        'group_keys': {
            'json_field': True,
            'map_field': True,
            'simple_field': False,
            '__main_info': False,
        },
        'custom_group_keys': {
            'json_field': True,
            'map_field': True,
            'simple_field': True,
            '__main_info': False,
        },
    },
}


@allure.title('Create provider')
@pytest.fixture()
def provider(sdk_client_fs: ADCMClient) -> Provider:
    """Get dummy provider"""
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'provider'))
    return bundle.provider_create(name='test_provider')


@allure.title('Create cluster')
@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient) -> Cluster:
    """Get cluster for inventory check"""
    cluster_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'cluster_inventory_tests'))
    return cluster_bundle.cluster_prototype().cluster_create(CLUSTER_NAME)


def test_check_inventories_file(cluster: Cluster, provider: Provider, adcm_fs: ADCM, request: SubRequest):
    """Assert inventory file contents for the action"""
    host = provider.host_create(fqdn=HOST_FQDN)
    with allure.step('Configure cluster'):
        service = cluster.service_add(name="zookeeper")
        cluster.host_add(host)
        component = service.component(name=GROUP_COMPONENT_NAME)
        cluster.hostcomponent_set((host, component))
    with allure.step(f'Create config group with {GROUP_COMPONENT_NAME} and change it'):
        config_group = create_config_group_and_add_host('group_name', component, host)
        config_group.config_set(CONFIG_TO_CHANGE)
    with allure.step('Run actions on cluster'):
        run_cluster_action_and_assert_result(cluster, "set_multi_states")
        run_cluster_action_and_assert_result(cluster, "install")
    with allure.step('Get inventory file from container'):
        text = get_file_from_container(adcm_fs, '/adcm/data/run/2/', 'inventory.json')
        inventory_content = text.read().decode('utf8')
        inventory = json.loads(inventory_content)
        _attach_inventory_file(request, inventory_content, 'Actual content of inventory.json')
    with allure.step('Get expected inventory file'):
        with open(utils.get_data_dir(__file__, 'cluster-inventory.json'), 'rb') as template:
            expected_content = template.read().decode('utf8')
            expected = json.loads(expected_content)
        _attach_inventory_file(request, expected_content, 'Expected content of inventory.json')
    with allure.step('Compare actual and expected config'):
        assert (
            inventory == expected
        ), "Content of file inventory.json doesn't match expected. See attachments for more info."
    with allure.step('Check that object attributes are available in ansible script'):
        run_cluster_action_and_assert_result(cluster, 'check')


class TestStateBeforeUpgrade:
    """Test that state before upgrade is correctly presented in inventory.json file"""

    @pytest.fixture()
    def old_cluster(self, sdk_client_fs) -> Cluster:
        """Upload old and new version of cluster, create old one"""
        old_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "upgrade", "old"))
        sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "upgrade", "new"))
        return old_bundle.cluster_create(name="Test Cluster")

    def test_before_upgrade_in_inventory(self, adcm_fs, old_cluster):
        """Test value of before upgrade state in inventory.json before and after upgrade"""
        with allure.step('Check before_upgrade state before upgrade'):
            task = old_cluster.action(name="do_nothing").run()
            task.wait()
            self.check_before_upgrade_state_equal_to(BEFORE_UPGRADE_DEFAULT_STATE, get_inventory_file(adcm_fs, task.id))
        with allure.step('Check before_upgrade state after upgrade'):
            state_before_upgrade = old_cluster.state
            old_cluster.upgrade().do()
            old_cluster.reread()
            task = old_cluster.action(name="do_nothing").run()
            task.wait()
            self.check_before_upgrade_state_equal_to(state_before_upgrade, get_inventory_file(adcm_fs, task.id))

    def check_before_upgrade_state_equal_to(self, expected_state: Optional[str], inventory: dict):
        """Check that `state` key in inventory dictionary is equal to expected"""
        with utils.catch_failed(KeyError, "Structure of inventory.json file is unexpected"):
            actual_state = inventory["all"]["children"]["CLUSTER"]["vars"]["cluster"]["before_upgrade"]["state"]
        assert (
            actual_state == expected_state
        ), f'Before upgrade state should be "{expected_state}", but actual state is "{actual_state}"'


class TestHostInMultipleConfigGroups:
    """Test inventory generation when one host belongs to more than on config group"""

    @pytest.fixture()
    def hosts(self, provider) -> Tuple[Host, Host]:
        """Create 2 hosts"""
        return provider.host_create("host-1"), provider.host_create("host-2")

    @pytest.fixture()
    def cluster_with_components(self, sdk_client_fs: ADCMClient) -> Tuple[Cluster, Service, Component, Component]:
        """Create cluster, add service and return itself, service and components"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_components"))
        cluster = bundle.cluster_create("Test Cluster")
        service = cluster.service_add(name="test_service")
        return (
            cluster,
            service,
            service.component(name="first_component"),
            service.component(name="second_component"),
        )

    @pytest.fixture()
    def second_service_with_components(self, cluster_with_components) -> Tuple[Service, Component, Component]:
        """Add second service to the cluster"""
        cluster, *_ = cluster_with_components
        service = cluster.service_add(name="second_service")
        return (
            service,
            service.component(name="first_component"),
            service.component(name="second_component"),
        )

    @pytest.fixture()
    def _map_hosts_to_components(self, hosts, cluster_with_components, second_service_with_components) -> None:
        cluster, *_, component_1, component_2 = cluster_with_components
        _, component_3, component_4 = second_service_with_components
        for host in hosts:
            cluster.host_add(host)
        cluster.hostcomponent_set(
            *[(host, component) for host in hosts for component in (component_1, component_2, component_3, component_4)]
        )

    @allure.issue(url="https://tracker.yandex.ru/ADCM-3153")
    @pytest.mark.usefixtures("_map_hosts_to_components")
    def test_hostvars_when_one_host_in_multiple_config_groups(self, hosts, cluster_with_components):
        """Test that hostvars are correct, when one host is in more than one config group"""
        host_1, _ = hosts
        cluster, service, component_1, _ = cluster_with_components
        with allure.step("Create config groups"):
            for obj in (cluster, service, component_1):
                group = create_config_group_and_add_host(f"{obj.__class__.__name__} group", obj, host_1)
                group.config_set({"config": {"param": "changed"}, "attr": {"group_keys": {"param": True}}})
        with allure.step("Run action that checks hostvars"):
            run_cluster_action_and_assert_result(cluster, "check")


def _read_job_inventory(container: Container, job_id: int) -> dict:
    exit_code, out = container.exec_run(["cat", f"/adcm/data/run/{job_id}/inventory.json"])
    content = out.decode("utf-8")
    if exit_code != 0:
        raise ValueError(f"Docker command failed: {content}")
    return json.loads(content)


def _attach_inventory_file(request: SubRequest, inventory_content: str, name: str):
    """Attach inventory file on top level of allure report"""
    reporter = utils.allure_reporter(request.config)
    if not reporter:
        return
    test_result = reporter.get_test(uuid=None)
    reporter.attach_data(
        uuid=uuid4(),
        body=inventory_content,
        name=name,
        attachment_type=allure.attachment_type.JSON,
        parent_uuid=test_result.uuid,
    )
