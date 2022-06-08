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

"""Tests for object issues"""
import asyncio
import json
import operator
from typing import Tuple, Optional, Union

import allure
import coreapi
import pytest
import requests
import websockets.client

from adcm_client.base import ActionHasIssues
from adcm_client.objects import ADCMClient, Provider, Host, Service
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.utils import catch_failed
from coreapi.exceptions import ErrorMessage
from websockets.legacy.client import WebSocketClientProtocol

from tests.library.assertions import dicts_are_equal
from tests.library.errorcodes import UPGRADE_ERROR


# pylint: disable=redefined-outer-name


@pytest.fixture()
def provider_bundle(sdk_client_fs):
    """Get provider without concerns bundle"""
    return sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'provider_wo_concern'))


@pytest.fixture()
def provider(provider_bundle):
    """Get provider without concerns"""
    return provider_bundle.provider_create(name='Test Provider')


def test_action_should_not_be_run_while_cluster_has_an_issue(sdk_client_fs: ADCMClient):
    """Test action should not be run while cluster has an issue"""
    bundle_path = utils.get_data_dir(__file__, "cluster")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    cluster = bundle.cluster_create(name=utils.random_string())
    with allure.step(f"Run action with error for cluster {cluster.name}"):
        with pytest.raises(ActionHasIssues):
            cluster.action(name="install").run()


def test_action_should_not_be_run_while_host_has_an_issue(sdk_client_fs: ADCMClient):
    """Test action should not be run while host has an issue"""
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
    """Test action should not be run while hostprovider has an issue"""
    bundle_path = utils.get_data_dir(__file__, "provider")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    provider = bundle.provider_create(name=utils.random_string())
    with allure.step(f"Run action with error for provider {provider.name}"):
        with pytest.raises(ActionHasIssues):
            provider.action(name="install").run()


def test_when_cluster_has_issue_than_upgrade_locked(sdk_client_fs: ADCMClient):
    """Test upgrade should not be run while cluster has an issue"""
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
        UPGRADE_ERROR.equal(e, "cluster ", " has blocking concerns ")


def test_when_hostprovider_has_issue_than_upgrade_locked(sdk_client_fs: ADCMClient):
    """Test upgrade should not be run while hostprovider has an issue"""
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
def test_when_component_has_no_constraint_then_cluster_doesnt_have_issues(sdk_client_fs: ADCMClient):
    """Test no cluster issues if no constraints on components"""
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


@allure.link('https://arenadata.atlassian.net/browse/ADCM-2810')
def test_concerns_are_deleted_with_cluster_deletion(sdk_client_fs: ADCMClient, provider: Provider):
    """Tests concerns are deleted from all related objects when the cluster is deleted"""
    with allure.step('Upload bundles and create cluster'):
        cluster_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'cluster'))
        cluster = cluster_bundle.cluster_create(name='Test Cluster')
    _, host_1, host_2 = _add_services_and_map_hosts_to_it(cluster, provider)
    with allure.step('Check there is a concern on one of the hosts'):
        with catch_failed(ErrorMessage, 'No errors should be raised on concerns check'):
            _check_object_has_concerns(host_1)
            _check_object_has_no_concerns(host_2)
    with allure.step('Delete cluster and expect issues to go away'):
        cluster.delete()
    with allure.step('Check concern is gone'):
        with catch_failed(ErrorMessage, 'No errors should be raised on concerns check'):
            _check_object_has_no_concerns(host_1)
            _check_object_has_no_concerns(host_2)


@pytest.mark.parametrize('bundle_name', ['host', 'provider'])
def test_host_concerns_stays_after_cluster_deletion(bundle_name: str, sdk_client_fs: ADCMClient):
    """Test that host/provider's concerns aren't deleted with cluster deletion"""
    concerns_from_provider_objects = 1
    concerns_from_cluster_objects = 3
    with allure.step('Upload provider bundle'):
        provider_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, bundle_name))
        provider = provider_bundle.provider_create(name='Test Provider')
    with allure.step('Upload bundles and create cluster'):
        cluster_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'cluster'))
        cluster = cluster_bundle.cluster_create(name='Test Cluster')
    _, host_1, host_2 = _add_services_and_map_hosts_to_it(cluster, provider)
    with allure.step('Check there are correct amount of concerns before cluster is deleted'):
        _check_concerns_amount(host_1, concerns_from_provider_objects + concerns_from_cluster_objects)
        _check_concerns_amount(host_2, concerns_from_provider_objects)
    cluster.delete()
    with allure.step('Check there are correct amount of concerns after cluster is deleted'):
        _check_concerns_amount(host_1, concerns_from_provider_objects)
        _check_concerns_amount(host_2, concerns_from_provider_objects)


def test_only_service_concerns_are_deleted_after_it(sdk_client_fs: ADCMClient):
    """Test amount of concerns before/after the service with concerns is deleted from the cluster"""
    with allure.step('Upload bundles and create cluster'):
        cluster_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'cluster'))
        cluster = cluster_bundle.cluster_create(name='Test Cluster')
        service = cluster.service_add(name='service_1')
    with allure.step('Check there are correct amount of concerns before service is deleted'):
        _check_concerns_amount(cluster, 3)
    service.delete()
    with allure.step('Check there are correct amount of concerns after service is deleted'):
        _check_concerns_amount(cluster, 1)


@pytest.fixture()
async def adcm_ws(sdk_client_fs, adcm_fs):
    addr = f'{adcm_fs.ip}:{adcm_fs.port}'
    async with websockets.client.connect(
        uri=f'ws://{addr}/ws/event/', subprotocols=['adcm', sdk_client_fs.api_token()]
    ) as conn:
        yield ADCMWebsocket(conn)


class ADCMWebsocket:
    _ws: WebSocketClientProtocol
    _default_timeout: float

    def __init__(self, conn: WebSocketClientProtocol, timeout=5.0):
        self._ws = conn
        self._default_timeout = timeout

    @allure.step('Get up to {max_messages} messages')
    async def get_messages(
        self, max_messages: int, single_msg_timeout: Union[int, float] = 1, break_on_first_fail: bool = True
    ):
        retrieved_messages = []
        for _ in range(max_messages):
            try:
                msg = await self.get_message(single_msg_timeout)
            except asyncio.TimeoutError:
                if break_on_first_fail:
                    break
            else:
                retrieved_messages.append(msg)
        with allure.step(f'Retrieved {len(retrieved_messages)} messages'):
            return retrieved_messages

    @allure.step('Wait for message from websocket for {timeout} seconds')
    async def get_message(self, timeout=None):
        timeout = timeout or self._default_timeout
        return json.loads(await asyncio.wait_for(self._ws.recv(), timeout))

    async def expect_message(self, timeout=None) -> dict:
        timeout = timeout or self._default_timeout
        with catch_failed(asyncio.TimeoutError, f'Message was failed to be received in {timeout} seconds'):
            return await self.get_message(timeout)

    @allure.step("Ensure there won't come any WS message for a {timeout} seconds")
    async def no_message_for(self, timeout=None):
        timeout = timeout or self._default_timeout
        try:
            message = await self.get_message(timeout)
        except TimeoutError:
            pass
        else:
            raise AssertionError(f'At least one message came: {message}')

    @allure.step('Check next incoming WS message')
    async def check_next_message_is(self, event: str, timeout_=None, **object_field):
        message = await self.expect_message(timeout_ or self._default_timeout)
        return await self.check_message_is(message, event, **object_field)

    @allure.step('Check next incoming WS message')
    async def check_next_message_is_not(self, event: str, timeout_=None, **object_field):
        message = await self.expect_message(timeout_ or self._default_timeout)
        return await self.check_message_is_not(message, event, **object_field)

    @allure.step('Check given WS message')
    async def check_message_is(self, message_object: dict, event: str, **object_field):
        with allure.step(f'Check that event is: {event}'):
            assert (actual_event := message_object['event']) == event, f'Incorrect event in message: {actual_event}'
        if not object_field:
            with allure.step('Skip "object" data check'):
                return message_object
        with allure.step('Check "object" data'):
            if 'object' not in message_object:
                raise KeyError(f"There's no key 'object' in WS message: {message_object}")
            object_data = message_object['object']
            for field, value in object_field.items():
                assert field in object_data, f'Failed to find key {field} in {object_data}'
                assert (actual_value := object_data[field]) == value, (
                    f'Incorrect value of key {field}.\n' f'Expected: {value}\n' f'Found: {actual_value}'
                )
        return message_object

    @allure.step('Check given WS message')
    async def check_message_is_not(self, message_object: dict, event: str, **object_field):
        if not object_field:
            with allure.step(f'Check only that event type is {event}'):
                assert (actual_event := message_object['event']) == event, f'Incorrect event type: {actual_event}'
                return message_object

        if 'object' not in message_object:
            raise KeyError(f"There's no key 'object' in WS message: {message_object}")

        # then "wrong" will be only the exact match of all given fields
        expected_fields = {('event', event), *{(k, v) for k, v in object_field.items()}}
        actual_fields = {
            ('event', message_object['event']),
            *{(k, v) for k, v in message_object['object'].items() if k in object_field.keys()},
        }
        assert actual_fields != expected_fields, f'Message fields are incorrect.\nThey should not be {actual_fields}'


async def test_provider_stays_out_of_concerns(sdk_client_fs, adcm_ws: ADCMWebsocket):
    provider_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'host_with_concern'))
    await adcm_ws.check_next_message_is('create', timeout_=1, type='bundle', id=provider_bundle.id)
    with allure.step('Create provider and check it has no concerns'):
        provider = provider_bundle.provider_create('Provider without concerns')
        _check_object_has_no_concerns(provider)
        await adcm_ws.check_next_message_is('create', timeout_=1, type='provider', id=provider.id)
    with allure.step('Create host and ensure provider has no concerns'):
        host = provider.host_create('host-with-concern')
        messages = await adcm_ws.get_messages(5, 1.5)
        for msg in messages:
            await adcm_ws.check_message_is_not(msg, 'add', type='provider-concerns')
        _check_object_has_concerns(host)
        _check_object_has_no_concerns(provider)


def _check_object_has_concerns(adcm_object):
    adcm_object.reread()
    assert len(adcm_object.concerns()) > 0, f'Object {adcm_object} should has at least one concern'


def _check_object_has_no_concerns(adcm_object):
    adcm_object.reread()
    assert len(adcm_object.concerns()) == 0, f'Object {adcm_object} should not has any concerns'


def _check_concerns_amount(adcm_object, expected_amount):
    adcm_object.reread()
    assert (
        actual_amount := len(adcm_object.concerns()) == expected_amount
    ), f'Object {adcm_object} should be {expected_amount}, not {actual_amount}'


@allure.step('Add service, map host to it and add another service')
def _add_services_and_map_hosts_to_it(cluster, provider) -> Tuple[Service, Host, Host]:
    service_1 = cluster.service_add(name='service_1')
    host_1, host_2 = [cluster.host_add(provider.host_create(f'test-host-{i}')) for i in range(2)]
    cluster.hostcomponent_set((host_1, service_1.component()))
    cluster.service_add(name='service_2')
    return service_1, host_1, host_2
