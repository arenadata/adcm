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
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir, parametrize_by_data_subdirs,\
    fixture_parametrized_by_data_subdirs


@fixture_parametrized_by_data_subdirs(__file__, 'cluster_and_service', scope='module')
def cluster(sdk_client_ms: ADCMClient, request):
    bundle = sdk_client_ms.upload_from_fs(request.param)
    cluster = bundle.cluster_create(name=bundle.name)
    cluster.service_add(name='multi')
    return cluster


def test_cluster_state_after_multijob(sdk_client_ms: ADCMClient, cluster):
    cluster.action_run(name="multi").wait()
    assert sdk_client_ms.cluster(name=cluster.name).state == cluster.name


def test_service_state_after_multijob(sdk_client_ms: ADCMClient, cluster):
    cluster.service(name='multi').action_run(name="multi").wait()
    assert cluster.service(name='multi').state == cluster.name


def test_cluster_service_state_locked(sdk_client_ms: ADCMClient):
    bundle = sdk_client_ms.upload_from_fs(get_data_dir(__file__, 'cluster_and_service_lock'))
    cluster = bundle.cluster_create(name=bundle.name)
    cluster.service_add(name='multi')
    cluster.service_add(name='stab')
    assert bundle.cluster(name=bundle.name).state == 'created'
    assert bundle.cluster(name=bundle.name).service(name='multi').state == 'created'
    assert bundle.cluster(name=bundle.name).service(name='stab').state == 'created'
    task = cluster.action_run(name='multi')
    assert bundle.cluster(name=bundle.name).state == 'locked'
    assert bundle.cluster(name=bundle.name).service(name='multi').state == 'locked'
    assert bundle.cluster(name=bundle.name).service(name='stab').state == 'locked'
    task.wait()
    assert bundle.cluster(name=bundle.name).state == 'multi_ok'
    assert bundle.cluster(name=bundle.name).service(name='multi').state == 'created'
    assert bundle.cluster(name=bundle.name).service(name='stab').state == 'created'
    task = cluster.service(name='multi').action_run(name='multi')
    assert bundle.cluster(name=bundle.name).state == 'locked'
    assert bundle.cluster(name=bundle.name).service(name='multi').state == 'locked'
    assert bundle.cluster(name=bundle.name).service(name='stab').state == 'created'
    task.wait()
    assert bundle.cluster(name=bundle.name).state == 'multi_ok'
    assert bundle.cluster(name=bundle.name).service(name='multi').state == 'multi_ok'
    assert bundle.cluster(name=bundle.name).service(name='stab').state == 'created'


@fixture_parametrized_by_data_subdirs(__file__, 'provider_and_host', scope='module')
def provider(sdk_client_ms: ADCMClient, request):
    bundle = sdk_client_ms.upload_from_fs(request.param)
    provider = bundle.provider_create(name=bundle.name)
    provider.host_create(fqdn=bundle.name)
    return provider


def test_provider_state_after_multijob(sdk_client_ms: ADCMClient, provider):
    provider.action_run(name="multi").wait()
    assert sdk_client_ms.provider(name=provider.name).state == provider.name


def test_host_state_after_multijob(sdk_client_ms: ADCMClient, provider):
    provider.host(fqdn=provider.name).action_run(name="multi").wait()
    assert provider.host(fqdn=provider.name).state == provider.name
