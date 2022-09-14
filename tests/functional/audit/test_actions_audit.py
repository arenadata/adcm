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

"""Test audit of actions"""

from typing import Callable, Tuple, Type, Union

import allure
import pytest
import requests
from adcm_client.audit import AuditOperation, ObjectType, OperationResult, OperationType
from adcm_client.objects import ADCM, ADCMClient, Bundle, Cluster, Job, Policy, Provider, Task
from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.functional.audit.conftest import (
    BUNDLES_DIR,
    NEW_USER,
    check_400,
    check_403,
    check_404,
    check_409,
    check_succeed,
    make_auth_header,
    parametrize_audit_scenario_parsing,
)
from tests.functional.rbac.conftest import BusinessRoles as BR
from tests.functional.rbac.conftest import create_policy
from tests.functional.tools import AnyADCMObject, ClusterRelatedObject, ProviderRelatedObject
from tests.library.audit.checkers import AuditLogChecker

# pylint: disable=redefined-outer-name

DummyTask = type("DummyTask", (), {"id": 10000})


@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    """Create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "actions" / "cluster")
    cluster = bundle.cluster_create("Actions Cluster")
    cluster.service_add(name="actions_service")
    return cluster


@pytest.fixture()
def provider(sdk_client_fs) -> Provider:
    """Create provider and host"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "actions" / "provider")
    provider = bundle.provider_create("Actions Provider")
    provider.host_create("host-fqdn")
    return provider


@pytest.fixture()
def build_policy(
    sdk_client_fs, new_user_client
) -> Callable[[BR, Union[ClusterRelatedObject, ProviderRelatedObject, ADCM]], Policy]:
    """Prepare "policy builder" that grants some permission to (already created) new user"""
    user_id = new_user_client.me().id
    return lambda role, obj: create_policy(sdk_client_fs, role, [obj], [sdk_client_fs.user(id=user_id)], [])


@pytest.fixture()
def grant_view_on_cluster(cluster, build_policy):
    """Grant new user a permission to "view cluster" with permission to view config"""
    build_policy(BR.ViewClusterConfigurations, cluster)


@pytest.fixture()
def grant_view_on_component(cluster, build_policy):
    """Grant new user a permission to "view component" with permission to view config"""
    build_policy(BR.ViewComponentConfigurations, cluster.service().component())


@pytest.fixture()
def grant_view_on_provider(provider, build_policy):
    """Grant new user a permission to "view provider" with permission to view config"""
    build_policy(BR.ViewProviderConfigurations, provider)


@pytest.fixture()
def grant_view_on_host(provider, build_policy):
    """Grant new user a permission to "view host" with permission to view config"""
    build_policy(BR.ViewHostConfigurations, provider.host())


class RunActionTestMixin:
    """Helpers for testing actions audit"""

    client: ADCMClient
    admin_creds: dict
    unauth_creds: dict
    correct_config: dict
    incorrect_config: dict

    def run_actions(self, success_action_path, fail_action_path, post):
        """
        Run actions via post:
            1. Unauthorized
            2. Failed to launch
            3. Launched and failed
            4. Launched and succeed
        """
        with allure.step("Unauthorized run action"):
            check_404(post(success_action_path, self.incorrect_config, self.unauth_creds))
        with allure.step("Run action with incorrect config"):
            check_409(post(success_action_path, self.incorrect_config))
        with allure.step("Run actions that will succeed and fail"):
            check_succeed(post(fail_action_path, self.correct_config))
            _wait_all_finished(self.client)
            check_succeed(post(success_action_path, self.correct_config))
            _wait_all_finished(self.client)


def _action_run_test_init(instance: RunActionTestMixin, admin_client: ADCMClient, new_user_client: ADCMClient) -> None:
    instance.client = admin_client
    instance.admin_creds = make_auth_header(admin_client)
    instance.unauth_creds = make_auth_header(new_user_client)
    instance.correct_config = {"config": {"param": 2}}
    instance.incorrect_config = {}


class TestClusterObjectsActions(RunActionTestMixin):
    """Test on audit of cluster objects' actions"""

    pytestmark = [pytest.mark.usefixtures("init", "grant_view_on_component")]

    @pytest.fixture()
    def init(self, sdk_client_fs, new_user_client):
        """Fill all required fields"""
        _action_run_test_init(self, sdk_client_fs, new_user_client)

    @parametrize_audit_scenario_parsing("cluster_actions.yaml", NEW_USER)
    def test_run_cluster_actions(self, cluster, audit_log_checker, post):
        """
        Test audit of cluster objects' actions:
        - /api/v1/cluster/{id}/action/{id}/run/

        - /api/v1/service/{id}/action/{id}/run/
        - /api/v1/cluster/{id}/service/{id}/action/{id}/run/

        - /api/v1/component/{id}/action/{id}/run/
        - /api/v1/service/{id}/component/{id}/action/{id}/run/
        - /api/v1/cluster/{id}/service/{id}/component/{id}/action/{id}/run/
        """
        self._run_cluster_actions(cluster, post)
        self._run_service_actions(cluster, post)
        self._run_component_actions(cluster, post)
        audit_log_checker.set_user_map(self.client)
        audit_log_checker.check(self.client.audit_operation_list(operation_type=OperationType.UPDATE))

    @allure.step("Run cluster actions")
    def _run_cluster_actions(self, cluster, post):
        cluster_action_prefix = f"cluster/{cluster.id}/action/"
        success_action_path = f"{cluster_action_prefix}{_succeed_action_id(cluster)}/run"
        fail_action_path = f"{cluster_action_prefix}{_fail_action_id(cluster)}/run"
        self.run_actions(success_action_path, fail_action_path, post)

    @allure.step("Run service actions")
    def _run_service_actions(self, cluster, post):
        service = cluster.service()
        direct_path = f"service/{service.id}/action/"
        from_cluster_path = f"cluster/{cluster.id}/{direct_path}"
        for path in (direct_path, from_cluster_path):
            success_action_path = f"{path}{_succeed_action_id(service)}/run"
            fail_action_path = f"{path}{_fail_action_id(service)}/run"
            self.run_actions(success_action_path, fail_action_path, post)

    @allure.step("Run component actions")
    def _run_component_actions(self, cluster, post):
        service = cluster.service()
        component = service.component()
        direct_path = f"component/{component.id}/action/"
        from_service_path = f"service/{service.id}/{direct_path}"
        from_cluster_path = f"cluster/{cluster.id}/{from_service_path}"
        for path in (direct_path, from_service_path, from_cluster_path):
            success_action_path = f"{path}{_succeed_action_id(component)}/run"
            fail_action_path = f"{path}{_fail_action_id(component)}/run"
            self.run_actions(success_action_path, fail_action_path, post)


class TestProviderObjectActions(RunActionTestMixin):
    """Tests on audit of provider objects' actions"""

    pytestmark = [pytest.mark.usefixtures("init", "grant_view_on_provider", "grant_view_on_host")]

    @pytest.fixture()
    def init(self, sdk_client_fs, new_user_client):
        """Fill all required fields"""
        _action_run_test_init(self, sdk_client_fs, new_user_client)

    @pytest.fixture()
    def _add_host_to_cluster(self, cluster, provider):
        cluster.host_add(provider.host())

    @parametrize_audit_scenario_parsing("provider_actions.yaml", NEW_USER)
    @pytest.mark.usefixtures("grant_view_on_cluster", "_add_host_to_cluster")
    def test_run_provider_actions(self, provider, audit_log_checker, post):
        """
        Test audit of provider objects' actions from host/provider/cluster's perspective:
        - /api/v1/provider/{id}/action/{id}/run/
        - /api/v1/host/{id}/action/{id}/run/
        - /api/v1/provider/{id}/host/{id}/action/{id}/run/
        - /api/v1/cluster/{id}/host/{id}/action/{id}/run/
        """
        self._run_provider_actions(provider, post)
        self._run_host_actions(provider, post)
        audit_log_checker.set_user_map(self.client)
        audit_log_checker.check(self.client.audit_operation_list(operation_type=OperationType.UPDATE))

    def test_simple_run_host_action(self, provider, cluster, sdk_client_fs):
        """Test audit of successful launch of `host_action: true`"""
        host = cluster.host_add(provider.host())
        action = host.action(name="host_action")
        url = f"{sdk_client_fs.url}/api/v1/host/{host.id}/action/{action.id}/run/"
        check_succeed(requests.post(url, json={"config": {"param": 1}}, headers=make_auth_header(sdk_client_fs)))
        audit_log: AuditOperation = sdk_client_fs.audit_operation_list()[0]
        with allure.step(f"Check audit record: {audit_log}"):
            assert audit_log.user_id == sdk_client_fs.me().id, "Incorrect used_id, admin's expected"
            assert audit_log.object_type == ObjectType.HOST, "Incorrect object type"
            assert audit_log.operation_name == f"{action.display_name} action launched", "Incorrect operation name"
            assert audit_log.operation_result == OperationResult.SUCCESS, "Operation should've succeed"

    def _run_provider_actions(self, provider: Provider, post: Callable):
        provider_action_prefix = f"provider/{provider.id}/action/"
        success_action_prefix = f"{provider_action_prefix}{_succeed_action_id(provider)}/run"
        fail_action_path = f"{provider_action_prefix}{_fail_action_id(provider)}/run"
        self.run_actions(success_action_prefix, fail_action_path, post)

    def _run_host_actions(self, provider: Provider, post: Callable):
        host = provider.host()
        direct_path = f"host/{host.id}/action/"
        from_provider_path = f"provider/{provider.id}/{direct_path}"
        from_cluster_path = f"cluster/{host.cluster_id}/{direct_path}"
        for path in (direct_path, from_provider_path, from_cluster_path):
            success_action_path = f"{path}{_succeed_action_id(host)}/run"
            fail_action_path = f"{path}{_fail_action_id(host)}/run"
            self.run_actions(success_action_path, fail_action_path, post)


class TestUpgrade(RunActionTestMixin):
    """Test audit of upgrade: simple (old) and with actions (new)"""

    SIMPLE = "Simple Upgrade"
    SUCCEED = "Succeed Upgrade"
    FAIL = "Fail Upgrade"

    @pytest.fixture()
    def init(self, sdk_client_fs, new_user_client):
        """Fill all required utilities for audit of actions tests"""
        _action_run_test_init(self, sdk_client_fs, new_user_client)

    @pytest.fixture()
    def upload_new_bundles(self, sdk_client_fs) -> Tuple[Bundle, Bundle]:
        """Upload new versions for cluster and provider bundles"""
        return (
            sdk_client_fs.upload_from_fs(BUNDLES_DIR / "actions" / "new_cluster"),
            sdk_client_fs.upload_from_fs(BUNDLES_DIR / "actions" / "new_provider"),
        )

    @pytest.mark.parametrize("parse_with_context", ["upgrade.yaml"], indirect=True)
    @pytest.mark.parametrize(
        "type_to_pick",
        [Cluster, pytest.param(Provider, marks=pytest.mark.skip(reason="https://tracker.yandex.ru/ADCM-3179"))],
    )
    @pytest.mark.usefixtures(
        "grant_view_on_cluster", "grant_view_on_provider", "upload_new_bundles", "init"
    )  # pylint: disable-next=too-many-locals
    def test_upgrade(self, type_to_pick: Type, cluster, provider, parse_with_context):
        """Test audit of cluster/provider simple upgrade/upgrade with action"""
        if type_to_pick == Cluster:
            obj = cluster
        elif type_to_pick == Provider:
            obj = provider
        else:
            raise ValueError("Either cluster or provider")
        type_name = type_to_pick.__name__.lower()
        upgrade_base = f"{self.client.url}/api/v1/{type_name}/{obj.id}/upgrade/"
        # we can run them in for loop even though it's success, because of how bundle is written
        url = f"{upgrade_base}{obj.upgrade(name=self.SIMPLE).id}/do/"
        for headers, actual_url, check_response in (
            (self.unauth_creds, url, check_403),
            (self.admin_creds, f"{upgrade_base}1000/do/", check_404),
            (self.admin_creds, url, check_succeed),
        ):
            with allure.step(f"Run upgrade '{self.SIMPLE}' on {type_name} {obj.name} via POST to {actual_url}"):
                check_response(requests.post(actual_url, headers=headers))
            _wait_all_finished(self.client)
        for name in (self.FAIL, self.SUCCEED):
            upgrade = obj.upgrade(name=name)
            url = f"{upgrade_base}{upgrade.id}/do/"
            for headers, data, check_response in (
                (self.unauth_creds, {}, check_403),
                (self.admin_creds, {}, check_409),
                (self.admin_creds, {"config": {"param": "asdklj"}}, check_succeed),
            ):
                with allure.step(f"Run upgrade '{name}' on {type_name} {obj.name} via POST to {url} with body: {data}"):
                    check_response(requests.post(url, json=data, headers=headers))
                _wait_all_finished(self.client)
        checker = AuditLogChecker(
            parse_with_context({"username": NEW_USER["username"], "name": obj.name, "object_type": type_name})
        )
        checker.set_user_map(self.client)
        checker.check(self.client.audit_operation_list())


class TestADCMActions:
    """Test audit of ADCM actions"""

    @parametrize_audit_scenario_parsing("adcm_actions.yaml", NEW_USER)
    @pytest.mark.usefixtures("prepare_settings")
    def test_adcm_actions(self, sdk_client_fs, audit_log_checker, new_user_client, build_policy):
        """Test audit of ADCM actions"""
        adcm = sdk_client_fs.adcm()
        build_policy(BR.ViewADCMSettings, adcm)
        sync_action = adcm.action(name="test_ldap_connection")
        url = f"{sdk_client_fs.url}/api/v1/adcm/{adcm.id}/action/{sync_action.id}/run/"
        with allure.step("Run action and get denied"):
            check_404(requests.post(url, headers=make_auth_header(new_user_client)))
        with allure.step("Fail to run action"):
            check_400(
                requests.post(url, json={"config": {"i": "doesnotexist"}}, headers=make_auth_header(sdk_client_fs))
            )
        with allure.step("Run action successfuly"):
            check_succeed(requests.post(url, headers=make_auth_header(sdk_client_fs)))
        _wait_all_finished(sdk_client_fs)
        audit_log_checker.set_user_map(sdk_client_fs)
        audit_log_checker.check(sdk_client_fs.audit_operation_list())


class TestTaskCancelRestart(RunActionTestMixin):
    """Test audit of cancelling/restarting tasks with one/multi jobs"""

    pytestmark = [pytest.mark.usefixtures("init", "grant_view_on_cluster")]

    @pytest.fixture()
    def init(self, sdk_client_fs, new_user_client):
        """Fill all utility fields for audit of actions testing"""
        _action_run_test_init(self, sdk_client_fs, new_user_client)

    @parametrize_audit_scenario_parsing("cancel_restart.yaml", {**NEW_USER, "action_display_name": "Terminate Simple"})
    def test_task_with_one_job(self, cluster, audit_log_checker):
        """Test audit of cancel/restart tasks with one job"""
        task = cluster.action(name="terminatable_simple").run(**self.correct_config)
        self._wait_for_status(task.job())
        self._test_task_cancel_restart(task, audit_log_checker)

    @parametrize_audit_scenario_parsing("cancel_restart.yaml", {**NEW_USER, "action_display_name": "Terminate Multi"})
    def test_task_with_multiple_jobs(self, cluster, audit_log_checker):
        """Test audit of cancel/restart tasks with many jobs"""
        task: Task = cluster.action(name="terminatable_multi").run(**self.correct_config)
        second_job = self._get_job("second_step", task)
        with allure.step("Wait for second job to start"):
            self._wait_for_status(second_job)
        self._test_task_cancel_restart(task, audit_log_checker)

    def _test_task_cancel_restart(self, task, audit_checker):
        with allure.step("Cancel task with result: denied, success, fail"):
            check_404(self._cancel(task, self.unauth_creds))
            check_succeed(self._cancel(task, self.admin_creds))
            _wait_all_finished(self.client)
            check_409(self._cancel(task, self.admin_creds))
        with allure.step("Restart task with result: denied, fail, success"):
            check_404(self._restart(task, self.unauth_creds))
            check_404(self._restart(DummyTask(), self.admin_creds))
            check_succeed(self._restart(task, self.admin_creds))
        _wait_all_finished(self.client)
        audit_checker.set_user_map(self.client)
        audit_checker.check(self.client.audit_operation_list())

    def _cancel(self, task: Union[Task, DummyTask], headers: dict):
        url = f"{self.client.url}/api/v1/task/{task.id}/cancel/"
        with allure.step(f"Cancel task via PUT {url}"):
            return requests.put(url, headers=headers)

    def _restart(self, task: Union[Task, DummyTask], headers: dict):
        url = f"{self.client.url}/api/v1/task/{task.id}/restart/"
        with allure.step(f"Restart task via PUT {url}"):
            return requests.put(url, headers=headers)

    def _get_job(self, name: str, task: Task) -> Job:
        return next(filter(lambda j: j.display_name == name, task.job_list()))

    def _wait_for_status(self, job: Job, status: str = "running", **kwargs):
        def _wait():
            job.reread()
            assert job.status == status, f"Job {job.display_name} should be in status {status}"

        wait_until_step_succeeds(_wait, timeout=9, period=1, **kwargs)


@allure.step("Wait all tasks are finished")
def _wait_all_finished(client):
    for j in client.job_list():
        j.task().wait()


def _succeed_action_id(obj: AnyADCMObject) -> int:
    return obj.action(name="will_succeed").id


def _fail_action_id(obj: AnyADCMObject) -> int:
    return obj.action(name="will_fail").id
