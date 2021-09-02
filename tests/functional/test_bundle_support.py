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
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

from tests.library import errorcodes as err


@pytest.mark.parametrize(
    "bundle_archive",
    [
        pytest.param(
            utils.get_data_dir(__file__, "bundle_wo_cluster_definition"),
            id="bundle_wo_cluster_definition",
        )
    ],
    indirect=True,
)
def test_bundle_should_have_any_cluster_definition(sdk_client_fs: ADCMClient, bundle_archive):
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(bundle_archive)
    with allure.step("Check error message"):
        err.BUNDLE_ERROR.equal(e, "There isn't any cluster or host provider definition in bundle")


def test_bundle_cant_removed_when_some_object_associated_with(
    sdk_client_fs: ADCMClient,
):
    bundle_path = utils.get_data_dir(__file__, "cluster_inventory_tests")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    bundle.cluster_prototype().cluster_create(name=__file__)
    with allure.step("Removing bundle"):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            bundle.delete()
    with allure.step("Check error message"):
        err.BUNDLE_CONFLICT.equal(e, "There is cluster", "of bundle ")


def test_bundle_can_be_removed_when_no_object_associated_with(
    sdk_client_fs: ADCMClient,
):
    bundle_path = utils.get_data_dir(__file__, "cluster_inventory_tests")
    init_bundle_count = len(sdk_client_fs.bundle_list())
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    with allure.step("Remove bundle"):
        bundle.delete()
    with allure.step("Check cluster bundle is removed"):
        assert len(sdk_client_fs.bundle_list()) == init_bundle_count


def test_default_values_should_according_to_their_datatypes(sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "cluster_with_config_default_values")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    cluster = bundle.cluster_prototype().cluster_create(name="Cluster")
    config = cluster.config()
    assert isinstance(config.get("str_key"), str)
    assert isinstance(config.get("text_key"), str)
    assert isinstance(config.get("int_key"), int)
    assert isinstance(config.get("float_key"), float)
    assert isinstance(config.get("bool"), bool)
    assert isinstance(config.get("password"), str)
    assert isinstance(config.get("json"), dict)
    assert isinstance(config.get("list"), list)
    assert isinstance(config.get("map"), dict)


empty_bundles_fields = [
    "empty_success_cluster",
    "empty_fail_cluster",
    "empty_success_host",
    "empty_fail_host",
]


@pytest.mark.parametrize("empty_fields", empty_bundles_fields)
def test_that_check_empty_field_is(empty_fields, sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "empty_states", empty_fields)
    sdk_client_fs.upload_from_fs(bundle_path)
    with allure.step("Check cluster bundle"):
        assert sdk_client_fs.bundle_list() is not None


cluster_fields = [
    ("empty_success_cluster", "failed"),
    ("empty_fail_cluster", "installed"),
]


@pytest.mark.parametrize(("cluster_bundle", "state"), cluster_fields)
def test_check_cluster_state_after_run_action_when_empty(cluster_bundle, state, sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "empty_states", cluster_bundle)
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    cluster = bundle.cluster_prototype().cluster_create(name=utils.random_string())
    cluster.action(name="install").run().wait()
    with allure.step(f"Check if cluster is in state {state}"):
        cluster.reread()
        assert cluster.state == state


host_fields = [
    ("empty_success_host", "failed"),
    ("empty_fail_host", "initiated"),
]


@pytest.mark.parametrize(("host_bundle", "state"), host_fields)
def test_check_host_state_after_run_action_when_empty(host_bundle, state, sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "empty_states", host_bundle)
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    provider = bundle.provider_prototype().provider_create(name=utils.random_string())
    host = provider.host_create(fqdn=utils.random_string())
    host.action(name="init").run().wait()
    with allure.step(f"Check if host is in state {state}"):
        host.reread()
        assert host.state == state


def test_loading_provider_bundle_must_be_pass(sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "hostprovider_loading_pass")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    with allure.step("Check that hostprovider loading pass"):
        assert bundle.provider_prototype() is not None


def test_run_parametrized_action_must_be_runned(sdk_client_fs: ADCMClient):
    bundle_path = utils.get_data_dir(__file__, "run_parametrized_action")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    cluster = bundle.cluster_prototype().cluster_create(name=utils.random_string())
    task = cluster.action(name="install").run(config={"param": "test test test test test"})
    task.try_wait()
    with allure.step("Check if state is success"):
        assert task.job().status == "success"


state_cases = [
    ("cluster", "on_success", "was_dict"),
    ("cluster", "on_success", "was_list"),
    ("cluster", "on_success", "was_sequence"),
    ("cluster", "on_fail", "was_dict"),
    ("cluster", "on_fail", "was_list"),
    ("cluster", "on_fail", "was_sequence"),
    ("provider", "on_success", "was_dict"),
    ("provider", "on_success", "was_list"),
    ("provider", "on_success", "was_sequence"),
    ("provider", "on_fail", "was_dict"),
    ("provider", "on_fail", "was_list"),
    ("provider", "on_fail", "was_sequence"),
    ("host", "on_success", "was_dict"),
    ("host", "on_success", "was_list"),
    ("host", "on_success", "was_sequence"),
    ("host", "on_fail", "was_dict"),
    ("host", "on_fail", "was_list"),
    ("host", "on_fail", "was_sequence"),
]


@pytest.mark.parametrize(("entity", "state", "case"), state_cases)
def test_load_should_fail_when(sdk_client_fs: ADCMClient, entity, state, case):
    with allure.step(f"Upload {entity} bundle with {case}"):
        bundle_path = utils.get_data_dir(__file__, "states", entity, state, case)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            sdk_client_fs.upload_from_fs(bundle_path)
    with allure.step(f"Check if state is {state}"):
        err.INVALID_OBJECT_DEFINITION.equal(e, state, "should be a <class 'str'>")


@allure.link("https://jira.arenadata.io/browse/ADCM-580")
def test_provider_bundle_shouldnt_load_when_has_export_section(
    sdk_client_fs: ADCMClient,
):
    bundle_path = utils.get_data_dir(__file__, "hostprovider_with_export")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(bundle_path)
    with allure.step("Check error"):
        err.INVALID_OBJECT_DEFINITION.equal(e, 'Map key "export" is not allowed here')
