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

import allure
import coreapi
import pytest

from adcm_client.base import ActionHasIssues
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils
from tests.library.errorcodes import UPGRADE_ERROR


def test_action_should_not_be_run_while_cluster_has_an_issue(sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "cluster")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step(f"Run action with error for cluster {cluster.name}"):
        with pytest.raises(ActionHasIssues):
            cluster.action(name="install").run()


def test_action_should_not_be_run_while_host_has_an_issue(sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "host")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    provider = bundle.provider_create(name=utils.random_string())
    host = provider.host_create(fqdn=utils.random_string())
    with allure.step(f"Run action with error for host {host.fqdn}"):
        with pytest.raises(ActionHasIssues):
            host.action(name="install").run()


def test_action_should_not_be_run_while_hostprovider_has_an_issue(
    sdk_client_fs: ADCMClient,
):
    bundle_path = utils.get_data_dir(__file__, "provider")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    provider = bundle.provider_create(name=utils.random_string())
    with allure.step(f"Run action with error for provider {provider.name}"):
        with pytest.raises(ActionHasIssues):
            provider.action(name="install").run()


def test_when_cluster_has_issue_than_upgrade_locked(sdk_client_fs: ADCMClient):
    with allure.step("Create cluster and upload new one bundle"):
        old_bundle_path = utils.get_data_dir(__file__, "cluster")
        new_bundle_path = utils.get_data_dir(__file__, "upgrade", "cluster")
        old_bundle = sdk_client_fs.upload_from_fs(old_bundle_path)
        cluster = old_bundle.cluster_create(name=utils.random_string())
        sdk_client_fs.upload_from_fs(new_bundle_path)
    with allure.step("Upgrade cluster"):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            cluster.upgrade().do()
    with allure.step("Check if cluster has issues"):
        UPGRADE_ERROR.equal(e, "cluster ", " has issue: ")


def test_when_hostprovider_has_issue_than_upgrade_locked(sdk_client_fs: ADCMClient):
    with allure.step("Create hostprovider"):
        old_bundle_path = utils.get_data_dir(__file__, "provider")
        new_bundle_path = utils.get_data_dir(__file__, "upgrade", "provider")
        old_bundle = sdk_client_fs.upload_from_fs(old_bundle_path)
        provider = old_bundle.provider_create(name=utils.random_string())
        sdk_client_fs.upload_from_fs(new_bundle_path)
    with allure.step("Upgrade provider"):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            provider.upgrade().do()
    with allure.step("Check if upgrade locked"):
        UPGRADE_ERROR.equal(e)


@allure.link("https://jira.arenadata.io/browse/ADCM-487")
def test_when_component_has_no_constraint_then_cluster_doesnt_have_issues(
    sdk_client_fs: ADCMClient,
):
    with allure.step("Create cluster (component has no constraint)"):
        bundle_path = utils.get_data_dir(__file__, "cluster_component_hasnt_constraint")
        bundle = sdk_client_fs.upload_from_fs(bundle_path)
        cluster = bundle.cluster_create(name=utils.random_string())
    cluster.service_add()
    with allure.step("Run action: lock cluster"):
        cluster.action(name="lock-cluster").run().try_wait()
    with allure.step("Check if state is always-locked"):
        cluster.reread()
        assert cluster.state == "always-locked"
