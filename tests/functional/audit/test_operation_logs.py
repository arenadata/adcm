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

"""Test audit operation logs"""

from typing import Tuple

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, User
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result
from adcm_pytest_plugin.utils import random_string
from docker.models.containers import Container
from tests.functional.audit.conftest import BUNDLES_DIR, ScenarioArg
from tests.functional.rbac.conftest import BusinessRoles, create_policy

# pylint: disable=redefined-outer-name


CONTEXT = {
    "simple_user": "simpler",
    "cluster": {
        "name": "ADB Cluster",
        "adb_service": {
            "name": "adb",
            "display_name": "ADB",
        },
    },
    "adb_service_component": "one_component",
}


@pytest.fixture()
def adb_bundle(sdk_client_fs) -> Bundle:
    """Upload "adb" bundle"""
    return sdk_client_fs.upload_from_fs(BUNDLES_DIR / "adb")


@pytest.fixture()
def dummy_host(generic_provider) -> Host:
    """Create host from dummy provider"""
    return generic_provider.host_create("dummy-host")


@pytest.fixture()
def new_user_and_client(sdk_client_fs) -> Tuple[User, ADCMClient]:
    """Create new user and login under it"""
    credentials = dict(username=CONTEXT["simple_user"], password="n2ohvzikj(#*Fhxznc")
    user = sdk_client_fs.user_create(**credentials)
    return user, ADCMClient(url=sdk_client_fs.url, user=credentials["username"], password=credentials["password"])


@pytest.mark.parametrize("parsed_audit_log", [ScenarioArg("simple.yaml", CONTEXT)], indirect=True)
def test_simple_flow(sdk_client_fs, audit_log_checker, adb_bundle, dummy_host, new_user_and_client):
    """Test simple from with cluster objects manipulations"""
    config = {"just_string": "hoho"}
    with allure.step("Create cluster and add service"):
        cluster = adb_bundle.cluster_create(name=CONTEXT["cluster"]["name"])
        cluster.host_add(dummy_host)
        service = cluster.service_add(name=CONTEXT["cluster"]["adb_service"]["name"])
    with allure.step("Set configuration of cluster objects"):
        component = service.component(name=CONTEXT["adb_service_component"])
        component.config_set_diff(config)
        service.config_set_diff(config)
        cluster.config_set_diff(config)
    cluster.hostcomponent_set((dummy_host, component))
    run_cluster_action_and_assert_result(cluster, "install", "failed")
    new_user, new_client = new_user_and_client
    create_policy(
        sdk_client_fs,
        BusinessRoles.ViewClusterConfigurations,
        [cluster],
        users=[new_user],
        groups=[],
    )
    new_client.reread()
    with allure.step("Try to change config from unauthorized user"):
        requests.post(
            f"{new_client.url}/api/v1/cluster/{cluster.id}/config/history/",
            json={},
            headers={"Authorization": f"Token {new_client.api_token()}"},
        )
    with allure.step("Delete cluster"):
        cluster.delete()
    # return after https://tracker.yandex.ru/ADCM-3244
    # check_audit_cef_logs(client=sdk_client_fs, adcm_container=adcm_fs.container)
    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(sdk_client_fs.audit_operation_list())


def test_no_audit_objects_duplication(adcm_fs, sdk_client_fs, adb_bundle, generic_provider):
    """Test that audit objects aren't duplicated and is correctly set as 'deleted'"""
    container = adcm_fs.container
    _prepare_objects(adb_bundle, generic_provider)
    cluster: Cluster = sdk_client_fs.cluster()
    cluster.update(name="New Name Of Cluster")
    cluster.service_delete(cluster.service())
    cluster.host_delete(cluster.host())
    # 2 clusters, 4 services, 4 components, 2 hosts, 1 provider, 2 bundles, adcm
    expected_objects = 16
    with allure.step(f"Check that amount of audit objects is {expected_objects}"):
        amount_of_objects = int(_exec_django_shell(container, "AuditObject.objects.count()"))
        assert amount_of_objects == expected_objects, f"Incorrect amount of audit objects: {amount_of_objects}"
    with allure.step("Check that correct amount of audit objects are considered deleted"):
        template = "AuditObject.objects.filter({}).count()"
        total_deleted = int(_exec_django_shell(container, template.format("is_deleted=True")))
        assert total_deleted == 2, "Only 1 service and its component should be considered deleted"
    cluster.delete()
    with allure.step("Check that correct amount of audit objects are considered deleted"):
        total_deleted = int(_exec_django_shell(container, template.format("is_deleted=True")))
        # cluster, 2 services, 2 components
        assert total_deleted == 5, "5 objects should be considered deleted"
        for object_type, expected_amount in (("cluster", 1), ("service", 2), ("component", 2)):
            actual_amount = int(
                _exec_django_shell(container, template.format(f'is_deleted=True, object_type="{object_type}"'))
            )
            assert actual_amount == expected_amount, (
                f"Unexpected amount of deleted audit objects of type {object_type}\n"
                f"Expected: {expected_amount}\nActual: {actual_amount}"
            )


def _exec_django_shell(container: Container, statement: str) -> str:
    script = f"from audit.models import AuditObject; print({statement})"
    with allure.step(f"Execute in django shell: {script}"):
        exit_code, output = container.exec_run(
            [
                "sh",
                "-c",
                ". /adcm/venv/default/bin/activate " f"&& python /adcm/python/manage.py shell -c '{script}'",
            ]
        )
        out = output.decode("utf-8").strip()
        assert exit_code == 0, f"docker exec failed: {out}"
        return out


@allure.step("Prepare objects")
def _prepare_objects(bundle, provider) -> None:
    for i in range(2):
        cluster = bundle.cluster_create(f"Cluster {i}")
        cluster.config_set_diff({"just_string": "clcl"})
        adb_service = cluster.service_add(name="adb")
        dummy_service = cluster.service_add(name="dummy")
        for service in (adb_service, dummy_service):
            service.config_set_diff({"just_string": "serverv"})
            service.component().config_set_diff({"just_string": "compo"})
        cluster.host_add(provider.host_create(random_string(6)))
