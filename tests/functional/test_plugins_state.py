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

# pylint:disable=redefined-outer-name
import copy

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle
from adcm_pytest_plugin.utils import get_data_dir
from delayed_assert import assert_expectations, expect

INITIAL_CLUSTERS_STATE = {
    'first': {'state': 'created', 'services': {'First': 'created', 'Second': 'created'}},
    'second': {'state': 'created', 'services': {'First': 'created', 'Second': 'created'}},
    'third': {'state': 'created', 'services': {'First': 'created', 'Second': 'created'}},
}


@allure.step('Check cluster service states')
def assert_cluster_service_states(bundle: Bundle, statemap: dict):
    for cname, clv in statemap.items():
        cstate = bundle.cluster(name=cname).state
        cstate_expected = clv['state']
        expect(
            cstate == cstate_expected,
            f"Cluster \"{cname}\" is \"{cstate}\" while expected \"{cstate_expected}\"",
        )
        for sname, sstate_expected in clv['services'].items():
            sstate = bundle.cluster(name=cname).service(name=sname).state
            expect(
                sstate == sstate_expected,
                (
                    f"Cluster \"{cname}\" service \"{sname}\" state is "
                    f"\"{sstate}\" while expected \"{sstate_expected}\""
                ),
            )
    assert_expectations()


@pytest.fixture()
def cluster_bundle(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    for name in ('first', 'second', 'third'):
        cluster = bundle.cluster_create(name)
        cluster.service_add(name='First')
        cluster.service_add(name='Second')
    return bundle


def test_change_service_state_by_name(cluster_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_STATE)
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run action: set first service'):
        cluster_bundle.cluster(name='first').action(name='set_first_service').run().try_wait()
    expected_state['first']['services']['First'] = 'bimba!'
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run action: set second service'):
        cluster_bundle.cluster(name='third').action(name='set_second_service').run().try_wait()
    expected_state['third']['services']['Second'] = 'state2'
    assert_cluster_service_states(cluster_bundle, expected_state)


def test_change_service_state_by_name_from_service(cluster_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_STATE)
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run action: set second service'):
        second = cluster_bundle.cluster(name='first').service(name='Second')
        second.action(name='set_second_service').run().try_wait()
    expected_state['first']['services']['Second'] = 'state2'
    assert_cluster_service_states(cluster_bundle, expected_state)


def test_change_service_state_by_name_from_another_service(cluster_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_STATE)
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run action: set first service'):
        second = cluster_bundle.cluster(name='first').service(name='Second')
        result = second.action(name='set_first_service').run().wait()
    with allure.step('Check job state'):
        assert result == "failed", "Job expected to be failed"
    assert_cluster_service_states(cluster_bundle, expected_state)


def test_change_service_state(cluster_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_STATE)
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run first service action: set service'):
        second = cluster_bundle.cluster(name='second')
        third = cluster_bundle.cluster(name='third')
        second.service(name='First').action(name='set_service').run().try_wait()
    expected_state['second']['services']['First'] = 'statex'
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run second service action: set service'):
        second.service(name='Second').action(name='set_service').run().try_wait()
    expected_state['second']['services']['Second'] = 'statex'
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run third service action: set service'):
        third.service(name='Second').action(name='set_service').run().try_wait()
    expected_state['third']['services']['Second'] = 'statex'
    assert_cluster_service_states(cluster_bundle, expected_state)


def test_change_cluster_state(cluster_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_STATE)
    assert_cluster_service_states(cluster_bundle, expected_state)
    first = cluster_bundle.cluster(name='first')
    second = cluster_bundle.cluster(name='second')
    third = cluster_bundle.cluster(name='third')
    with allure.step('Run second cluster action: set cluster'):
        second.action(name='set_cluster').run().try_wait()
    with allure.step('Check cluster state'):
        expected_state['second']['state'] = 'statey'
        assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run first service action: set cluster'):
        first.service(name='First').action(name='set_cluster').run().try_wait()
    expected_state['first']['state'] = 'statey'
    assert_cluster_service_states(cluster_bundle, expected_state)
    with allure.step('Run second service action: set cluster'):
        third.service(name='Second').action(name='set_cluster').run().try_wait()
    expected_state['third']['state'] = 'statey'
    assert_cluster_service_states(cluster_bundle, expected_state)


INITIAL_HOST_STATE = {
    'first': {
        'state': 'created',
        'hosts': {'first_host1': 'created', 'first_host2': 'created', 'first_host3': 'created'},
    },
    'second': {
        'state': 'created',
        'hosts': {'second_host1': 'created', 'second_host2': 'created', 'second_host3': 'created'},
    },
}


@pytest.fixture()
def host_bundle(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
    for name, value in INITIAL_HOST_STATE.items():
        provider = bundle.provider_create(name)
        for hname in value['hosts']:
            provider.host_create(fqdn=hname)
    return bundle


@allure.step('Check host state')
def assert_provider_host_states(bundle: Bundle, statemap: dict):
    for pname, expected_state in statemap.items():
        pstate = bundle.provider(name=pname).state
        pstate_expected = expected_state['state']
        expect(
            pstate == pstate_expected,
            f"Provider \"{pname}\" is \"{pstate}\" while expected \"{pstate_expected}\"",
        )
        for hname, hstate_expected in expected_state['hosts'].items():
            hstate = bundle.provider(name=pname).host(fqdn=hname).state
            expect(
                hstate == hstate_expected,
                f'Host state is {hstate} while expected {hstate_expected}',
            )
    assert_expectations()


def test_change_host_state(host_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_HOST_STATE)
    assert_provider_host_states(host_bundle, expected_state)
    first = host_bundle.provider(name='first')
    second = host_bundle.provider(name='second')
    with allure.step('Run first host action: set host'):
        first.host(fqdn='first_host1').action(name='set_host').run().try_wait()
    expected_state['first']['hosts']['first_host1'] = 'statez'
    assert_provider_host_states(host_bundle, expected_state)
    with allure.step('Run second host action: set host'):
        second.host(fqdn='second_host1').action(name='set_host').run().try_wait()
    expected_state['second']['hosts']['second_host1'] = 'statez'
    assert_provider_host_states(host_bundle, expected_state)
    with allure.step('Change second host'):
        second.host(fqdn='second_host3').action(name='set_host').run().try_wait()
    expected_state['second']['hosts']['second_host3'] = 'statez'
    assert_provider_host_states(host_bundle, expected_state)


def test_change_provider_state(host_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_HOST_STATE)
    assert_provider_host_states(host_bundle, expected_state)
    with allure.step('Run second host action: set state'):
        second = host_bundle.provider(name='second')
        second.action(name='set_state').run().try_wait()
    expected_state['second']['state'] = 'pstatex'
    assert_provider_host_states(host_bundle, expected_state)


def test_change_host_from_provider_state(host_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_HOST_STATE)
    assert_provider_host_states(host_bundle, expected_state)
    with allure.step('Run second host action: set host state'):
        second = host_bundle.provider(name='second')
        second.action(name='set_host_state').run(config={"fqdn": "second_host2"}).try_wait()
    expected_state['second']['hosts']['second_host2'] = 'stateq'
    assert_provider_host_states(host_bundle, expected_state)
