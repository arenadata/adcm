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

from typing import Callable

import allure
import pytest
from adcm_client.audit import OperationType
from adcm_client.objects import ADCMClient, Cluster, Policy, Provider

from tests.functional.audit.conftest import (
    BUNDLES_DIR,
    NEW_USER,
    check_404,
    check_409,
    check_succeed,
    make_auth_header,
    parametrize_audit_scenario_parsing,
)
from tests.functional.rbac.conftest import BusinessRoles as BR
from tests.functional.rbac.conftest import create_policy
from tests.functional.tools import AnyADCMObject

# pylint: disable=redefined-outer-name


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
def build_policy(sdk_client_fs, new_user_client) -> Callable[[BR, AnyADCMObject], Policy]:
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
    def _add_cluster_to_host(self, cluster, provider):
        cluster.host_add(provider.host())

    @parametrize_audit_scenario_parsing("provider_actions.yaml", NEW_USER)
    @pytest.mark.usefixtures('grant_view_on_cluster', '_add_cluster_to_host')
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


def _wait_all_finished(client):
    for j in client.job_list():
        j.task().wait()


def _succeed_action_id(obj: AnyADCMObject) -> int:
    return obj.action(name="will_succeed").id


def _fail_action_id(obj: AnyADCMObject) -> int:
    return obj.action(name="will_fail").id
