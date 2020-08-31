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
# pylint: disable=W0611, W0621, W0404, W0212, C1801
import pytest
from pytest_lazyfixture import lazy_fixture
from adcm_client.base import ResponseTooLong
from adcm_client.objects import (Action, ADCMClient, Bundle,  # ActionList,
                                 BundleList, Cluster, ClusterList,
                                 ClusterPrototype, ClusterPrototypeList, Host,
                                 HostList, HostPrototype, HostPrototypeList,
                                 Job, JobList, Prototype, PrototypeList,
                                 Provider, ProviderList, ProviderPrototype,
                                 ProviderPrototypeList, Task, TaskList)
from adcm_pytest_plugin.utils import get_data_dir, get_subdirs_iter
from delayed_assert import assert_expectations, expect


@pytest.fixture(scope="module")
def cluster_bundles(sdk_client_ms: ADCMClient):
    for path in get_subdirs_iter(__file__, "cluster_bandles"):
        sdk_client_ms.upload_from_fs(path)
    return sdk_client_ms


@pytest.fixture(scope="module")
def one_cluster_prototype(cluster_bundles: ADCMClient):
    return cluster_bundles.bundle(name="4").cluster_prototype()


@pytest.fixture(scope="module")
def one_cluster_prototype_name_attr(one_cluster_prototype: ClusterPrototype):
    return {'name': one_cluster_prototype.name}


@pytest.fixture(scope="module")
def one_cluster_prototype_bundle_id_attr(one_cluster_prototype: ClusterPrototype):
    return {'bundle_id': one_cluster_prototype.bundle_id}


@pytest.fixture(scope="module")
def clusters(cluster_bundles: ADCMClient):
    for i in range(51):
        cluster_bundles.bundle(name='14').cluster_create(name=str(i))
    return cluster_bundles


@pytest.fixture(scope="module")
def one_cluster(cluster_bundles: ADCMClient):
    return cluster_bundles.bundle(name='42').cluster_create(name="I am a Cluster")


@pytest.fixture(scope="module")
def one_cluster_name_attr(one_cluster: Cluster):
    return {'name': one_cluster.name}


@pytest.fixture(scope="module")
def one_cluster_prototype_id_attr(one_cluster: Cluster):
    return {'prototype_id': one_cluster.prototype_id}


@pytest.fixture(scope="module")
def provider_bundles(sdk_client_ms: ADCMClient):
    for path in get_subdirs_iter(__file__, "provider_bundles"):
        sdk_client_ms.upload_from_fs(path)
    return sdk_client_ms


@pytest.fixture(scope="module")
def providers(provider_bundles: ADCMClient):
    bundle = provider_bundles.bundle(name='provider18')
    for i in range(51):
        bundle.provider_create(name=str(i))
    return provider_bundles


@pytest.fixture(scope="module")
def one_provider(provider_bundles: ADCMClient):
    return provider_bundles.bundle(name='provider15').provider_create(name="I am a Provider")


@pytest.fixture(scope="module")
def one_provider_name_attr(one_provider: Provider):
    return {'name': one_provider.name}


@pytest.fixture(scope="module")
def one_provider_prototype_id_attr(one_provider: Provider):
    return {'prototype_id': one_provider.prototype_id}


@pytest.fixture(scope="module")
def provider_bundle_id(one_provider: Provider):
    return {'bundle_id': one_provider.bundle_id}


@pytest.fixture(scope="module")
def hosts(provider_bundles: ADCMClient, one_provider):
    for i in range(51):
        one_provider.host_create(fqdn=str(i))
    return provider_bundles


@pytest.fixture(scope="module")
def one_host(provider_bundles: ADCMClient):
    provider = provider_bundles.bundle(name='provider42').provider_create(name="For one Host")
    return provider.host_create(fqdn='host.host.host')


@pytest.fixture(scope="module")
def one_host_fqdn_attr(one_host: Host):
    return {'fqdn': one_host.fqdn}


@pytest.fixture(scope="module")
def one_host_prototype_id_attr(one_host: Host):
    return {'prototype_id': one_host.prototype_id}


@pytest.fixture(scope="module")
def one_host_provider_id_attr(one_host: Host):
    return {'provider_id': one_host.provider_id}


@pytest.mark.parametrize(
    'TestedClass',
    [
        pytest.param(
            Bundle,
            id="Bundle"
        ),
        pytest.param(
            Prototype,
            id="Prototype"
        ),
        pytest.param(
            ClusterPrototype,
            id="ClusterPrototype"
        ),
        pytest.param(
            ProviderPrototype,
            id="ProviderPrototype"
        ),
        pytest.param(
            HostPrototype,
            id="HostPrototype"
        ),
        pytest.param(
            Cluster,
            id="Cluster"
        ),
        pytest.param(
            Provider,
            id="Provider"
        ),
        pytest.param(
            Host,
            id="Host"
        ),
        pytest.param(
            Task,
            id="Task"
        ),
        pytest.param(
            Job,
            id="Job"
        ),
    ]
)
def test_coreapi_schema(sdk_client_ms: ADCMClient, TestedClass):
    def get_params(link):
        result = {}
        for f in link.fields:
            result[f.name] = True
        return result

    schema_obj = sdk_client_ms._api.schema
    for p in TestedClass.PATH:
        assert p in schema_obj.data
        schema_obj = schema_obj[p]

    params = get_params(schema_obj.links['list'])
    # from pprint import pprint
    # pprint(params)
    for f in TestedClass.FILTERS:
        expect(
            f in params,
            "Filter {} should be acceptable for coreapi in class {}".format(
                f, TestedClass.__name__
            )
        )
    assert_expectations()


@pytest.mark.parametrize(
    "sdk_client,TestedClass",
    [
        pytest.param(
            lazy_fixture('cluster_bundles'),
            ClusterPrototypeList,
            id="Cluster Prototype"),
        pytest.param(
            lazy_fixture('cluster_bundles'),
            PrototypeList,
            id="Prototype"),
        pytest.param(
            lazy_fixture('provider_bundles'),
            ProviderPrototypeList,
            id="Provider Prototype"),
        pytest.param(
            lazy_fixture('provider_bundles'),
            HostPrototypeList,
            id="Host Prototype"),
        pytest.param(
            lazy_fixture('provider_bundles'),
            BundleList,
            id="Bundle"),
        pytest.param(
            lazy_fixture('clusters'),
            ClusterList,
            id="Cluster"),
        pytest.param(
            lazy_fixture('hosts'),
            HostList,
            id="Host"),
        pytest.param(
            lazy_fixture('host_with_jobs'),
            TaskList,
            id="Task"),
        pytest.param(
            lazy_fixture('host_with_jobs'),
            JobList,
            id="Job"),
    ],
)
def test_paging_fail(sdk_client, TestedClass):
    """Scenario:
    * Prepare a lot of objects in ADCM
    * Call listing api over objects.*List classes
    * Expecting to have ResponseTooLong error
    """
    with pytest.raises(ResponseTooLong):
        TestedClass(sdk_client._api)


@pytest.mark.parametrize(
    "sdk_client,TestedClass,TestedListClass,search_args,expected_args",
    [
        pytest.param(
            lazy_fixture('cluster_bundles'),
            ClusterPrototype,
            ClusterPrototypeList,
            lazy_fixture('one_cluster_prototype_name_attr'),
            lazy_fixture('one_cluster_prototype_name_attr'),
            id="Cluster Prototype Name Filter"),
        pytest.param(
            lazy_fixture('cluster_bundles'),
            ClusterPrototype,
            ClusterPrototypeList,
            lazy_fixture('one_cluster_prototype_bundle_id_attr'),
            lazy_fixture('one_cluster_prototype_bundle_id_attr'),
            id="Cluster Prototype Bundle ID Filter"),
        pytest.param(
            lazy_fixture('cluster_bundles'),
            Prototype,
            PrototypeList,
            lazy_fixture('one_cluster_prototype_name_attr'),
            lazy_fixture('one_cluster_prototype_name_attr'),
            id="Prototype Name Filter"),
        pytest.param(
            lazy_fixture('cluster_bundles'),
            Prototype,
            PrototypeList,
            lazy_fixture('one_cluster_prototype_bundle_id_attr'),
            lazy_fixture('one_cluster_prototype_bundle_id_attr'),
            id="Prototype Bundle ID Filter"),
        pytest.param(
            lazy_fixture('provider_bundles'),
            ProviderPrototype,
            ProviderPrototypeList,
            {'name': 'provider24'},
            {'name': 'provider24'},
            id="Provider Prototype Name Filter"),
        pytest.param(
            lazy_fixture('provider_bundles'),
            ProviderPrototype,
            ProviderPrototypeList,
            lazy_fixture('provider_bundle_id'),
            lazy_fixture('provider_bundle_id'),
            id="Provider Prototype Bundle ID Filter"),
        pytest.param(
            lazy_fixture('provider_bundles'),
            HostPrototype,
            HostPrototypeList,
            {'name': 'host13'},
            {'name': 'host13'},
            id="Host Prototype Name Filter"),
        pytest.param(
            lazy_fixture('provider_bundles'),
            HostPrototype,
            HostPrototypeList,
            lazy_fixture('provider_bundle_id'),
            lazy_fixture('provider_bundle_id'),
            id="Host Prototype Bundle ID Filter"),
        pytest.param(
            lazy_fixture('cluster_bundles'),
            Bundle,
            BundleList,
            {'name': '4'},
            {'version': 'ver4'},
            id="Bundle Name Filter"),
        pytest.param(
            lazy_fixture('cluster_bundles'),
            Bundle,
            BundleList,
            {'version': 'ver8'},
            {'name': '8'},
            id="Bundle Version Filter"),
        pytest.param(
            lazy_fixture('clusters'),
            Cluster,
            ClusterList,
            lazy_fixture('one_cluster_name_attr'),
            lazy_fixture('one_cluster_prototype_id_attr'),
            id="Cluster Name Filter"),
        pytest.param(
            lazy_fixture('clusters'),
            Cluster,
            ClusterList,
            lazy_fixture('one_cluster_prototype_id_attr'),
            lazy_fixture('one_cluster_name_attr'),
            id="Cluster Prototype Id Filter"),
        pytest.param(
            lazy_fixture('providers'),
            Provider,
            ProviderList,
            lazy_fixture('one_provider_name_attr'),
            lazy_fixture('one_provider_prototype_id_attr'),
            id="Provider Name Filter"),
        pytest.param(
            lazy_fixture('providers'),
            Provider,
            ProviderList,
            lazy_fixture('one_provider_prototype_id_attr'),
            lazy_fixture('one_provider_name_attr'),
            id="Provider Prototype Id Filter"),
        pytest.param(
            lazy_fixture('hosts'),
            Host,
            HostList,
            lazy_fixture('one_host_fqdn_attr'),
            lazy_fixture('one_host_prototype_id_attr'),
            id="Host Fqdn Filter"),
        pytest.param(
            lazy_fixture('hosts'),
            Host,
            HostList,
            lazy_fixture('one_host_prototype_id_attr'),
            lazy_fixture('one_host_fqdn_attr'),
            id="Host Prototype Id Filter"),
        pytest.param(
            lazy_fixture('host_with_jobs'),
            Task,
            TaskList,
            lazy_fixture('task_action_id_attr'),
            lazy_fixture('task_action_id_attr'),
            id="Task Action Id Filter"),
        pytest.param(
            lazy_fixture('host_with_jobs'),
            Task,
            TaskList,
            lazy_fixture('task_status_attr'),
            lazy_fixture('task_status_attr'),
            id="Task Status Filter"),
        pytest.param(
            lazy_fixture('host_with_jobs'),
            Job,
            JobList,
            lazy_fixture('task_status_attr'),
            lazy_fixture('task_status_attr'),
            id="Job Action Id Filter"),
        pytest.param(
            lazy_fixture('host_with_jobs'),
            Job,
            JobList,
            lazy_fixture('task_status_attr'),
            lazy_fixture('task_status_attr'),
            id="Job Status Filter"),
        pytest.param(
            lazy_fixture('host_with_jobs'),
            Job,
            JobList,
            lazy_fixture('job_task_id_attr'),
            lazy_fixture('job_task_id_attr'),
            id="Job Task Id Filter"),
    ]
)
def test_filter(sdk_client: ADCMClient, TestedClass, TestedListClass, search_args, expected_args):
    """Scenario:
    * Create a lot of objects in ADCM (more than allowed to get without paging)
    * Call listing over *List class with tested filter as search args.
    * Inspect first (and only) element of list
    * Check that we found what we need
    * Create single object over class call (like Cluster or Bundle) with tested filter
      as search args
    * Check that we found what we need
    """
    lo = TestedListClass(sdk_client._api, **search_args)
    for k, v in expected_args.items():
        assert getattr(lo[0], k) == v
    o = TestedClass(sdk_client._api, **search_args)
    for k, v in expected_args.items():
        assert getattr(o, k) == v


@pytest.fixture(scope='module')
def cluster_with_actions(sdk_client_ms: ADCMClient):
    b = sdk_client_ms.upload_from_fs(get_data_dir(__file__, 'cluster_with_actions'))
    return b.cluster_create(name="cluster_with_actions")


@pytest.fixture(scope='module')
def service_with_actions(cluster_with_actions: Cluster):
    return cluster_with_actions.service_add(name='service_with_actions')


@pytest.fixture(scope='module')
def provider_with_actions(sdk_client_ms: ADCMClient):
    b = sdk_client_ms.upload_from_fs(get_data_dir(__file__, 'provider_with_actions'))
    return b.provider_create(name="provider_with_actions")


@pytest.fixture(scope='module')
def host_with_actions(provider_with_actions: Provider):
    return provider_with_actions.host_create(fqdn='host.with.actions')


@pytest.fixture(scope='module')
def host_ok_action(host_with_actions: Host):
    return host_with_actions.action(name="ok42")


@pytest.fixture(scope='module')
def host_fail_action(host_with_actions: Host):
    return host_with_actions.action(name="fail50")


@pytest.fixture(scope='module')
def host_with_jobs(host_with_actions: Host, host_fail_action, host_ok_action):
    for _ in range(51):
        host_fail_action.run().wait()
    host_ok_action.run().try_wait()
    return host_with_actions


@pytest.fixture(scope='module')
def task_action_id_attr(host_ok_action: Action):
    return {'action_id': host_ok_action.action_id}


@pytest.fixture(scope='module')
def task_status_attr(host_ok_action: Action):
    return {'status': 'success'}


@pytest.fixture(scope='module')
def job_task_id_attr(host_ok_action: Action):
    return {'task_id': host_ok_action.task().task_id}


# There is no paging on Actions right now.
# @pytest.mark.parametrize(
#     "TestedParentClass",
#     [
#         pytest.param(
#             lazy_fixture('cluster_with_actions'),
#             id="Cluster"
#         ),
#         pytest.param(
#             lazy_fixture('service_with_actions'),
#             id="Service"
#         ),
#         pytest.param(
#             lazy_fixture('provider_with_actions'),
#             id="Provider"
#         ),
#         pytest.param(
#             lazy_fixture('host_with_actions'),
#             id="Host"
#         ),
#     ])
# def test_paging_fail_on_actions(TestedParentClass):
#     """Scenario:
#     * Create object  with a lot of actions
#     * Call action_list()
#     * Expecting to have ResponseTooLong error
#     """
#     with pytest.raises(ResponseTooLong):
#         from pprint import pprint
#         pprint(TestedParentClass.action_list())

@pytest.mark.parametrize(
    "TestedParentClass,search_args,expected_args",
    [
        pytest.param(
            lazy_fixture('cluster_with_actions'),
            {'name': 'ok14'},
            {'name': 'ok14'},
            id="on Cluster"),
        pytest.param(
            lazy_fixture('service_with_actions'),
            {'name': 'fail15'},
            {'name': 'fail15'},
            id="on Service"),
        pytest.param(
            lazy_fixture('provider_with_actions'),
            {'name': 'ok14'},
            {'name': 'ok14'},
            id="on Provider"),
        pytest.param(
            lazy_fixture('host_with_actions'),
            {'name': 'fail15'},
            {'name': 'fail15'},
            id="on Host"),
    ]
)
def test_actions_name_filter(TestedParentClass, search_args, expected_args):
    """Scenario:
    * Create object with a lot of actions
    * Call action_list() with tested filter as search args.
    * Inspect first (and only) element of list
    * Check that we found what we need
    * Call action() with tested filter as search args
    * Check that we found what we need
    """
    lo = TestedParentClass.action_list(**search_args)
    for k, v in expected_args.items():
        assert getattr(lo[0], k) == v
    o = TestedParentClass.action(**search_args)
    for k, v in expected_args.items():
        assert getattr(o, k) == v
