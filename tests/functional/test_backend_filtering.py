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

"""Tests for backend filtering"""

from typing import List, Type, Union

import allure
import pytest
import pytest_check as check
from adcm_client.base import BaseAPIObject
from adcm_client.objects import (
    Action,
    ADCMClient,
    Bundle,
    BundleList,
    Cluster,
    ClusterList,
    ClusterPrototype,
    ClusterPrototypeList,
    Host,
    HostList,
    HostPrototype,
    HostPrototypeList,
    Job,
    JobList,
    Prototype,
    PrototypeList,
    Provider,
    ProviderList,
    ProviderPrototype,
    ProviderPrototypeList,
    Service,
    Task,
    TaskList,
)
from adcm_pytest_plugin.utils import get_data_dir, get_subdirs_iter
from pytest_lazyfixture import lazy_fixture

# pylint: disable=redefined-outer-name,protected-access


@pytest.fixture()
def cluster_bundles(sdk_client_fs: ADCMClient):
    """Upload cluster bundles"""
    for path in get_subdirs_iter(__file__, "cluster_bundles"):
        sdk_client_fs.upload_from_fs(path)
    return sdk_client_fs


@pytest.fixture()
def one_cluster_prototype(cluster_bundles: ADCMClient):
    """Get cluster prototype"""
    return cluster_bundles.bundle(name="4").cluster_prototype()


@pytest.fixture()
def one_cluster_prototype_name_attr(one_cluster_prototype: ClusterPrototype):
    """Get cluster prototype name attr"""
    return {"name": one_cluster_prototype.name}


@pytest.fixture()
def one_cluster_prototype_bundle_id_attr(one_cluster_prototype: ClusterPrototype):
    """Get cluster prototype bundle_id attr"""
    return {"bundle_id": one_cluster_prototype.bundle_id}


@pytest.fixture()
def clusters(cluster_bundles: ADCMClient):
    """Create clusters"""
    for i in range(51):
        cluster_bundles.bundle(name="14").cluster_create(name=f"cluster {i}")
    return cluster_bundles


@pytest.fixture()
def one_cluster(cluster_bundles: ADCMClient):
    """Create one cluster"""
    return cluster_bundles.bundle(name="42").cluster_create(name="I am a Cluster")


@pytest.fixture()
def one_cluster_name_attr(one_cluster: Cluster):
    """Get cluster name attr"""
    return {"name": one_cluster.name}


@pytest.fixture()
def one_cluster_prototype_id_attr(one_cluster: Cluster):
    """Get cluster prototype_id attr"""
    return {"prototype_id": one_cluster.prototype_id}


@pytest.fixture()
def provider_bundles(sdk_client_fs: ADCMClient):
    """Upload provider bundles"""
    for path in get_subdirs_iter(__file__, "provider_bundles"):
        sdk_client_fs.upload_from_fs(path)
    return sdk_client_fs


@pytest.fixture()
def providers(provider_bundles: ADCMClient):
    """Create providers"""
    bundle = provider_bundles.bundle(name="provider18")
    for i in range(51):
        bundle.provider_create(name=str(i))
    return provider_bundles


@pytest.fixture()
def one_provider(provider_bundles: ADCMClient):
    """Create one provider"""
    return provider_bundles.bundle(name="provider15").provider_create(name="I am a Provider")


@pytest.fixture()
def one_provider_name_attr(one_provider: Provider):
    """Get provider name attr"""
    return {"name": one_provider.name}


@pytest.fixture()
def one_provider_prototype_id_attr(one_provider: Provider):
    """Get provider prototype_id attr"""
    return {"prototype_id": one_provider.prototype_id}


@pytest.fixture()
def provider_bundle_id(one_provider: Provider):
    """Get provider bundle_id attr"""
    return {"bundle_id": one_provider.bundle_id}


@pytest.fixture()
def hosts(provider_bundles: ADCMClient, one_provider):
    """Create hosts return provider bundles"""
    for i in range(51):
        one_provider.host_create(fqdn=f"host{i}")
    return provider_bundles


@pytest.fixture()
def one_host(provider_bundles: ADCMClient):
    """Create one host"""
    provider = provider_bundles.bundle(name="provider42").provider_create(name="For one Host")
    return provider.host_create(fqdn="host.host.host")


@pytest.fixture()
def one_host_fqdn_attr(one_host: Host):
    """Get host fqdn attr"""
    return {"fqdn": one_host.fqdn}


@pytest.fixture()
def one_host_prototype_id_attr(one_host: Host):
    """Get host prototype_id attr"""
    return {"prototype_id": one_host.prototype_id}


@pytest.fixture()
def one_host_provider_id_attr(one_host: Host):
    """Get host provider_id attr"""
    return {"provider_id": one_host.provider_id}


@pytest.mark.skip(reason="ADCM-3297")
@pytest.mark.parametrize(
    "tested_class",
    [
        pytest.param(Bundle, id="Bundle"),
        pytest.param(Prototype, id="Prototype"),
        pytest.param(ClusterPrototype, id="ClusterPrototype"),
        pytest.param(ProviderPrototype, id="ProviderPrototype"),
        pytest.param(HostPrototype, id="HostPrototype"),
        pytest.param(Cluster, id="Cluster"),
        pytest.param(Provider, id="Provider"),
        pytest.param(Host, id="Host"),
        pytest.param(Task, id="Task"),
        pytest.param(Job, id="Job"),
    ],
)
def test_coreapi_schema(sdk_client_fs: ADCMClient, tested_class: Type[BaseAPIObject]):
    """Test coreapi schema"""

    def _get_params(link):
        result = {}
        for field in link.fields:
            result[field.name] = True
        return result

    schema_obj = sdk_client_fs._api.schema
    with allure.step(f"Get {tested_class.__name__} schema objects"):
        for path in tested_class.PATH:
            assert path in schema_obj.data
            schema_obj = schema_obj[path]
        params = _get_params(schema_obj.links["list"])
    with allure.step(f"Check if filters are acceptable for coreapi {tested_class.__name__}"):
        for _filter in tested_class.FILTERS:
            check.is_in(
                _filter,
                params,
                f"Filter {_filter} should be acceptable for coreapi in class {tested_class.__name__}",
            )


@pytest.mark.parametrize(
    ("sdk_client", "tested_class", "tested_list_class", "search_args", "expected_args"),
    [
        pytest.param(
            lazy_fixture("cluster_bundles"),
            ClusterPrototype,
            ClusterPrototypeList,
            lazy_fixture("one_cluster_prototype_name_attr"),
            lazy_fixture("one_cluster_prototype_name_attr"),
            id="Cluster Prototype Name Filter",
        ),
        pytest.param(
            lazy_fixture("cluster_bundles"),
            ClusterPrototype,
            ClusterPrototypeList,
            lazy_fixture("one_cluster_prototype_bundle_id_attr"),
            lazy_fixture("one_cluster_prototype_bundle_id_attr"),
            id="Cluster Prototype Bundle ID Filter",
        ),
        pytest.param(
            lazy_fixture("cluster_bundles"),
            Prototype,
            PrototypeList,
            lazy_fixture("one_cluster_prototype_name_attr"),
            lazy_fixture("one_cluster_prototype_name_attr"),
            id="Prototype Name Filter",
        ),
        pytest.param(
            lazy_fixture("cluster_bundles"),
            Prototype,
            PrototypeList,
            lazy_fixture("one_cluster_prototype_bundle_id_attr"),
            lazy_fixture("one_cluster_prototype_bundle_id_attr"),
            id="Prototype Bundle ID Filter",
        ),
        pytest.param(
            lazy_fixture("provider_bundles"),
            ProviderPrototype,
            ProviderPrototypeList,
            {"name": "provider24"},
            {"name": "provider24"},
            id="Provider Prototype Name Filter",
        ),
        pytest.param(
            lazy_fixture("provider_bundles"),
            ProviderPrototype,
            ProviderPrototypeList,
            lazy_fixture("provider_bundle_id"),
            lazy_fixture("provider_bundle_id"),
            id="Provider Prototype Bundle ID Filter",
        ),
        pytest.param(
            lazy_fixture("provider_bundles"),
            HostPrototype,
            HostPrototypeList,
            {"name": "host13"},
            {"name": "host13"},
            id="Host Prototype Name Filter",
        ),
        pytest.param(
            lazy_fixture("provider_bundles"),
            HostPrototype,
            HostPrototypeList,
            lazy_fixture("provider_bundle_id"),
            lazy_fixture("provider_bundle_id"),
            id="Host Prototype Bundle ID Filter",
        ),
        pytest.param(
            lazy_fixture("cluster_bundles"),
            Bundle,
            BundleList,
            {"name": "4"},
            {"version": "ver4"},
            id="Bundle Name Filter",
        ),
        pytest.param(
            lazy_fixture("cluster_bundles"),
            Bundle,
            BundleList,
            {"version": "ver8"},
            {"name": "8"},
            id="Bundle Version Filter",
        ),
        pytest.param(
            lazy_fixture("clusters"),
            Cluster,
            ClusterList,
            lazy_fixture("one_cluster_name_attr"),
            lazy_fixture("one_cluster_prototype_id_attr"),
            id="Cluster Name Filter",
        ),
        pytest.param(
            lazy_fixture("clusters"),
            Cluster,
            ClusterList,
            lazy_fixture("one_cluster_prototype_id_attr"),
            lazy_fixture("one_cluster_name_attr"),
            id="Cluster Prototype Id Filter",
        ),
        pytest.param(
            lazy_fixture("providers"),
            Provider,
            ProviderList,
            lazy_fixture("one_provider_name_attr"),
            lazy_fixture("one_provider_prototype_id_attr"),
            id="Provider Name Filter",
        ),
        pytest.param(
            lazy_fixture("providers"),
            Provider,
            ProviderList,
            lazy_fixture("one_provider_prototype_id_attr"),
            lazy_fixture("one_provider_name_attr"),
            id="Provider Prototype Id Filter",
        ),
        pytest.param(
            lazy_fixture("hosts"),
            Host,
            HostList,
            lazy_fixture("one_host_fqdn_attr"),
            lazy_fixture("one_host_prototype_id_attr"),
            id="Host Fqdn Filter",
        ),
        pytest.param(
            lazy_fixture("hosts"),
            Host,
            HostList,
            lazy_fixture("one_host_prototype_id_attr"),
            lazy_fixture("one_host_fqdn_attr"),
            id="Host Prototype Id Filter",
        ),
        pytest.param(
            lazy_fixture("hosts_with_jobs"),
            Task,
            TaskList,
            lazy_fixture("task_action_id_attr"),
            lazy_fixture("task_action_id_attr"),
            id="Task Action Id Filter",
        ),
        pytest.param(
            lazy_fixture("hosts_with_jobs"),
            Task,
            TaskList,
            lazy_fixture("task_status_attr"),
            lazy_fixture("task_status_attr"),
            id="Task Status Filter",
        ),
        pytest.param(
            lazy_fixture("hosts_with_jobs"),
            Job,
            JobList,
            lazy_fixture("task_status_attr"),
            lazy_fixture("task_status_attr"),
            id="Job Action Id Filter",
        ),
        pytest.param(
            lazy_fixture("hosts_with_jobs"),
            Job,
            JobList,
            lazy_fixture("task_status_attr"),
            lazy_fixture("task_status_attr"),
            id="Job Status Filter",
        ),
        pytest.param(
            lazy_fixture("hosts_with_jobs"),
            Job,
            JobList,
            lazy_fixture("job_task_id_attr"),
            lazy_fixture("job_task_id_attr"),
            id="Job Task Id Filter",
        ),
    ],
)
def test_filter(sdk_client: ADCMClient, tested_class, tested_list_class, search_args, expected_args):
    """Scenario:
    * Create a lot of objects in ADCM (more than allowed to get without paging)
    * Call listing over *List class with tested filter as search args.
    * Inspect first (and only) element of list
    * Check that we found what we need
    * Create single object over class call (like Cluster or Bundle) with tested filter
      as search args
    * Check that we found what we need
    """
    with allure.step("Create a lot of objects in ADCM"):
        objects = tested_list_class(sdk_client._api, **search_args)
    with allure.step("Inspect first (and only) element of list"):
        for k, v in expected_args.items():
            assert getattr(objects[0], k) == v
    with allure.step("Create single object over class call (like Cluster or Bundle) with tested filter as search args"):
        single_object = tested_class(sdk_client._api, **search_args)
    with allure.step("Check created object"):
        for k, v in expected_args.items():
            assert getattr(single_object, k) == v


@pytest.fixture()
def cluster_with_actions(sdk_client_fs: ADCMClient):
    """Create cluster with actions"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_actions"))
    return bundle.cluster_create(name="cluster with actions")


@pytest.fixture()
def service_with_actions(cluster_with_actions: Cluster):
    """Create service with actions"""
    return cluster_with_actions.service_add(name="service_with_actions")


@pytest.fixture()
def provider_with_actions(sdk_client_fs: ADCMClient):
    """Create provider with actions"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider_with_actions"))
    return bundle.provider_create(name="provider_with_actions")


@pytest.fixture()
def host_with_actions(provider_with_actions: Provider):
    """Create host with actions"""
    return provider_with_actions.host_create(fqdn="host.with.actions")


@pytest.fixture()
def host_ok_action(host_with_actions: Host):
    """Het host OK action"""
    return host_with_actions.action(name="ok42")


@pytest.fixture()
def hosts_with_actions(host_with_actions: Host, provider_with_actions: Provider):
    """Create hosts with actions"""
    hosts = [host_with_actions]
    for i in range(9):
        hosts.append(provider_with_actions.host_create(fqdn=f"host.with.actions.{i}"))
    return hosts


@pytest.fixture()
def hosts_with_jobs(hosts_with_actions: List, host_ok_action: Action):
    """
    Run multiple actions on hosts. Return first host.
    """
    for _ in range(6):
        actions = []
        for host in hosts_with_actions:
            actions.append(host.action(name="fail50").run())
        for action in actions:
            action.wait()
    host_ok_action.run().try_wait()
    return hosts_with_actions[0]


@pytest.fixture()
def task_action_id_attr(host_ok_action: Action):
    """Get task action_id attr"""
    return {"action_id": host_ok_action.action_id}


@pytest.fixture()
def task_status_attr():
    """Get task status attr"""
    return {"status": "success"}


@pytest.fixture()
def job_task_id_attr(host_ok_action: Action):
    """Get task task_id attr"""
    return {"task_id": host_ok_action.task().id}


@pytest.mark.parametrize(
    ("tested_parent_class", "search_args", "expected_args"),
    [
        pytest.param(
            lazy_fixture("cluster_with_actions"),
            {"name": "ok14"},
            {"name": "ok14"},
            id="on Cluster",
        ),
        pytest.param(
            lazy_fixture("service_with_actions"),
            {"name": "fail15"},
            {"name": "fail15"},
            id="on Service",
        ),
        pytest.param(
            lazy_fixture("provider_with_actions"),
            {"name": "ok14"},
            {"name": "ok14"},
            id="on Provider",
        ),
        pytest.param(lazy_fixture("host_with_actions"), {"name": "fail15"}, {"name": "fail15"}, id="on Host"),
    ],
)
def test_actions_name_filter(
    tested_parent_class: Union[Provider, Service, Cluster], search_args: dict, expected_args: dict
):
    """Scenario:
    * Create object with a lot of actions
    * Call action_list() with tested filter as search args.
    * Inspect first (and only) element of list
    * Check that we found what we need
    * Call action() with tested filter as search args
    * Check that we found what we need
    """
    with allure.step(f"Create {tested_parent_class} with a lot of actions"):
        actions = tested_parent_class.action_list(**search_args)
    with allure.step("Inspect first (and only) element of list"):
        for k, v in expected_args.items():
            assert getattr(actions[0], k) == v
    with allure.step("Call action() with tested filter as search args"):
        action = tested_parent_class.action(**search_args)
    with allure.step("Check action name"):
        for k, v in expected_args.items():
            assert getattr(action, k) == v
