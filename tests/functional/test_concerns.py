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
import itertools
from typing import Tuple

import allure
import coreapi
import pytest
from adcm_client.base import ActionHasIssues
from adcm_client.objects import ADCMClient, Cluster, Host, Provider, Service
from adcm_pytest_plugin.utils import catch_failed, get_data_dir, random_string
from coreapi.exceptions import ErrorMessage

from tests.library.adcm_websockets import ADCMWebsocket, EventMessage

# pylint: disable=redefined-outer-name


@pytest.fixture()
def provider_bundle(sdk_client_fs):
    """Get provider without concerns bundle"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider_wo_concern"))


@pytest.fixture()
def provider(provider_bundle):
    """Get provider without concerns"""
    return provider_bundle.provider_create(name="Test Provider")


def test_action_should_not_be_run_while_cluster_has_an_issue(sdk_client_fs: ADCMClient):
    """Test action should not be run while cluster has an issue"""
    bundle_path = get_data_dir(__file__, "cluster")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    cluster = bundle.cluster_create(name=random_string())
    with allure.step(f"Run action with error for cluster {cluster.name}"):
        with pytest.raises(ActionHasIssues):
            cluster.action(name="install").run()


def test_action_should_not_be_run_while_host_has_an_issue(sdk_client_fs: ADCMClient):
    """Test action should not be run while host has an issue"""
    bundle_path = get_data_dir(__file__, "host")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    provider = bundle.provider_create(name=random_string())
    host = provider.host_create(fqdn=random_string())
    with allure.step(f"Run action with error for host {host.fqdn}"):
        with pytest.raises(ActionHasIssues):
            host.action(name="install").run()


def test_action_should_not_be_run_while_hostprovider_has_an_issue(sdk_client_fs: ADCMClient):
    """Test action should not be run while hostprovider has an issue"""
    bundle_path = get_data_dir(__file__, "provider")
    bundle = sdk_client_fs.upload_from_fs(bundle_path)
    provider = bundle.provider_create(name=random_string())
    with allure.step(f"Run action with error for provider {provider.name}"):
        with pytest.raises(ActionHasIssues):
            provider.action(name="install").run()


def test_when_cluster_has_issue_then_upgrade_locked(sdk_client_fs: ADCMClient):
    """Test upgrade should not be run while cluster has an issue"""
    with allure.step("Create cluster and upload new one bundle"):
        old_bundle_path = get_data_dir(__file__, "cluster")
        new_bundle_path = get_data_dir(__file__, "upgrade", "cluster")
        old_bundle = sdk_client_fs.upload_from_fs(old_bundle_path)
        cluster = old_bundle.cluster_create(name=random_string())
        sdk_client_fs.upload_from_fs(new_bundle_path)
    with allure.step("Check upgrade isn't listed when concern is presented"):
        assert len(cluster.upgrade_list()) == 0, "No upgrade should be available with concern"
    with allure.step("Upgrade cluster"):
        cluster.config_set_diff({"required_param": 11})
        assert len(cluster.upgrade_list()) == 1, "Upgrade should be available after concern is removed"
        with catch_failed(coreapi.exceptions.ErrorMessage, "Upgrade should've launched successfuly"):
            cluster.upgrade().do()


def test_when_hostprovider_has_issue_then_upgrade_locked(sdk_client_fs: ADCMClient):
    """Test upgrade should not be run while hostprovider has an issue"""
    with allure.step("Create hostprovider"):
        old_bundle_path = get_data_dir(__file__, "provider")
        new_bundle_path = get_data_dir(__file__, "upgrade", "provider")
        old_bundle = sdk_client_fs.upload_from_fs(old_bundle_path)
        provider = old_bundle.provider_create(name=random_string())
        sdk_client_fs.upload_from_fs(new_bundle_path)
    with allure.step("Check upgrade isn't listed when concern is presented"):
        assert len(provider.upgrade_list()) == 0, "No upgrade should be available with concern"
    with allure.step("Upgrade provider"):
        provider.config_set_diff({"required_param": 11})
        assert len(provider.upgrade_list()) == 1, "Upgrade should be available after concern is removed"
        with catch_failed(coreapi.exceptions.ErrorMessage, "Upgrade should've launched successfully"):
            provider.upgrade().do()


@allure.link("https://jira.arenadata.io/browse/ADCM-487")
def test_when_component_has_no_constraint_then_cluster_doesnt_have_issues(sdk_client_fs: ADCMClient):
    """Test no cluster issues if no constraints on components"""
    with allure.step("Create cluster (component has no constraint)"):
        bundle_path = get_data_dir(__file__, "cluster_component_hasnt_constraint")
        bundle = sdk_client_fs.upload_from_fs(bundle_path)
        cluster = bundle.cluster_create(name=random_string())
    cluster.service_add()
    with allure.step("Run action: lock cluster"):
        cluster.action(name="lock-cluster").run().try_wait()
    with allure.step("Check if state is always-locked"):
        cluster.reread()
        assert cluster.state == "always-locked"


@allure.link("https://arenadata.atlassian.net/browse/ADCM-2810")
def test_concerns_are_deleted_with_cluster_deletion(sdk_client_fs: ADCMClient, provider: Provider):
    """Tests concerns are deleted from all related objects when the cluster is deleted"""
    with allure.step("Upload bundles and create cluster"):
        cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
        cluster = cluster_bundle.cluster_create(name="Test Cluster")
    _, host_1, host_2 = _add_services_and_map_hosts_to_it(cluster, provider)
    with allure.step("Check there is a concern on one of the hosts"):
        with catch_failed(ErrorMessage, "No errors should be raised on concerns check"):
            _check_object_has_concerns(host_1)
            _check_object_has_no_concerns(host_2)
    with allure.step("Delete cluster and expect issues to go away"):
        cluster.delete()
    with allure.step("Check concern is gone"):
        with catch_failed(ErrorMessage, "No errors should be raised on concerns check"):
            _check_object_has_no_concerns(host_1)
            _check_object_has_no_concerns(host_2)


@pytest.mark.parametrize("bundle_name", ["host", "provider"])
def test_host_concerns_stays_after_cluster_deletion(bundle_name: str, sdk_client_fs: ADCMClient):
    """Test that host/provider's concerns aren't deleted with cluster deletion"""
    concerns_from_provider_objects = 1
    concerns_from_cluster_objects = 3
    with allure.step("Upload provider bundle"):
        provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_name))
        provider = provider_bundle.provider_create(name="Test Provider")
    with allure.step("Upload bundles and create cluster"):
        cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
        cluster = cluster_bundle.cluster_create(name="Test Cluster")
    _, host_1, host_2 = _add_services_and_map_hosts_to_it(cluster, provider)
    with allure.step("Check there are correct amount of concerns before cluster is deleted"):
        _check_concerns_amount(host_1, concerns_from_provider_objects + concerns_from_cluster_objects)
        _check_concerns_amount(host_2, concerns_from_provider_objects)
    cluster.delete()
    with allure.step("Check there are correct amount of concerns after cluster is deleted"):
        _check_concerns_amount(host_1, concerns_from_provider_objects)
        _check_concerns_amount(host_2, concerns_from_provider_objects)


def test_only_service_concerns_are_deleted_after_it(sdk_client_fs: ADCMClient):
    """Test amount of concerns before/after the service with concerns is deleted from the cluster"""
    with allure.step("Upload bundles and create cluster"):
        cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
        cluster = cluster_bundle.cluster_create(name="Test Cluster")
        service = cluster.service_add(name="service_1")
    with allure.step("Check there are correct amount of concerns before service is deleted"):
        _check_concerns_amount(cluster, 3)
    service.delete()
    with allure.step("Check there are correct amount of concerns after service is deleted"):
        _check_concerns_amount(cluster, 1)


class TestProviderIndependence:
    """
    Test that provider is independent of concerns coming from hosts and cluster objects.
    Part of tests are using websockets to read events.
    """

    async def test_provider_stays_out_of_concerns(self, sdk_client_fs, adcm_ws: ADCMWebsocket):
        """
        Test that provider doesn't get concerns from host and cluster hierarchy
        even when a component is mapped on host.
        This test also checks some of websocket events.
        """
        provider_bundle = "host_with_concern"
        cluster_bundle = "cluster_with_constraint_concern"
        service_name = "service_with_concerns"

        provider = await self._create_provider_wo_concerns(provider_bundle, sdk_client_fs, adcm_ws)
        host = await self._create_host_and_check_provider(provider, adcm_ws)
        cluster = await self._create_cluster_with_concerns_and_add_service(
            cluster_bundle, service_name, sdk_client_fs, adcm_ws
        )
        await self._add_host_to_cluster_and_check_concerns(cluster, host, adcm_ws)
        await self._set_hc_map_and_check_concerns(cluster, host, adcm_ws)

    async def _create_provider_wo_concerns(
        self, bundle_name: str, client: ADCMClient, adcm_ws: ADCMWebsocket
    ) -> Provider:
        with allure.step(f"Upload provider bundle {bundle_name} and check creation event"):
            provider_bundle = client.upload_from_fs(get_data_dir(__file__, bundle_name))
            await adcm_ws.check_next_message_is(1, event="create", type="bundle", id=provider_bundle.id)
        with allure.step("Create provider and check it has no concerns"):
            provider = provider_bundle.provider_create("Provider without concerns")
            _check_object_has_no_concerns(provider)
            await adcm_ws.check_next_message_is(1, event="create", type="provider", id=provider.id)
            return provider

    @allure.step("Create host and ensure provider has no concerns")
    async def _create_host_and_check_provider(self, provider: Provider, adcm_ws: ADCMWebsocket) -> Host:
        host = provider.host_create("host-with-concern")
        _check_object_has_concerns(host)
        _check_object_has_no_concerns(provider)
        messages = await adcm_ws.get_messages(5, 1.5)
        for msg in messages:
            adcm_ws.check_message_is_not(msg, event="add", type="provider-concerns")
        return host

    async def _create_cluster_with_concerns_and_add_service(
        self, bundle_name: str, service_name: str, client: ADCMClient, adcm_ws: ADCMWebsocket
    ) -> Cluster:
        with allure.step(f"Upload cluster bundle {bundle_name} and check creation event"):
            cluster_bundle = client.upload_from_fs(get_data_dir(__file__, bundle_name))
            await adcm_ws.check_next_message_is(event="create", type="bundle", id=cluster_bundle.id)
        with allure.step(f"Create cluster, add service {service_name} and check creation messages"):
            cluster = cluster_bundle.cluster_create("Cluster without concerns")
            await adcm_ws.check_next_message_is(event="add", type="cluster-concerns")
            await adcm_ws.check_next_message_is(event="create", type="cluster", id=cluster.id)
            service = cluster.service_add(name=service_name)
            messages = await adcm_ws.get_waiting_messages()
            adcm_ws.check_messages_are_presented(
                (
                    EventMessage(
                        "add",
                        {
                            "type": "service",
                            "id": service.id,
                            "details": {"type": "cluster", "value": str(cluster.id)},
                        },
                    ),
                    *[
                        self._concern_add_msg(type_)
                        for type_ in (
                            "service-component-concerns",  # concern on component
                            "cluster-concerns",  # concern on cluster
                            "cluster-object-concerns",  # concern on service
                        )
                    ],
                ),
                messages,
            )
        return cluster

    async def _add_host_to_cluster_and_check_concerns(self, cluster: Cluster, host: Host, adcm_ws: ADCMWebsocket):
        service = cluster.service()
        component = service.component()
        with allure.step(f"Add host {host.fqdn} to a cluster"):
            cluster.host_add(host)
            await adcm_ws.check_next_message_is(event="add", type="host")
        with allure.step("Check that all objects have concerns expect provider"):
            _check_object_has_no_concerns(host.provider())
            _check_concerns_amount(cluster, 3)
            _check_concerns_amount(service, 3)
            _check_concerns_amount(component, 3)
            _check_object_has_concerns(host)

    async def _set_hc_map_and_check_concerns(self, cluster: Cluster, host: Host, adcm_ws: ADCMWebsocket):
        service = cluster.service()
        component = service.component()
        with allure.step(f"Map component {component.name} on host {host.fqdn}"):
            cluster.hostcomponent_set((host, component))
            messages = await adcm_ws.get_waiting_messages()
        with allure.step("Check concerns and events"):
            _check_object_has_no_concerns(host.provider())
            _check_object_has_concerns(host)
            # now they should have concern from host, so amount is the same as before
            _check_concerns_amount(cluster, 3)
            _check_concerns_amount(service, 3)
            _check_concerns_amount(component, 3)
            adcm_ws.check_messages_are_presented(
                (
                    EventMessage("change_hostcomponentmap", {"type": "cluster", "id": cluster.id}),
                    *tuple(
                        itertools.chain.from_iterable(
                            (self._concern_add_msg(type_), self._concern_delete_msg(type_))
                            for type_ in (
                                "cluster-concerns",  # HC concern removed from cluster
                                "cluster-object-concerns",  # and from service
                                "service-component-concerns",  # and from component
                            )
                        )
                    ),
                ),
                messages,
            )

    @staticmethod
    def _concern_add_msg(type_) -> EventMessage:
        return EventMessage("add", {"type": type_})

    @staticmethod
    def _concern_delete_msg(type_) -> EventMessage:
        return EventMessage("delete", {"type": type_})


def _check_object_has_concerns(adcm_object):
    adcm_object.reread()
    assert len(adcm_object.concerns()) > 0, f"Object {adcm_object} should has at least one concern"


def _check_object_has_no_concerns(adcm_object):
    adcm_object.reread()
    assert len(adcm_object.concerns()) == 0, f"Object {adcm_object} should not has any concerns"


def _check_concerns_amount(adcm_object, expected_amount):
    adcm_object.reread()
    assert (
        actual_amount := len(adcm_object.concerns())
    ) == expected_amount, f"Object {adcm_object} should be {expected_amount}, not {actual_amount}"


@allure.step("Add service, map host to it and add another service")
def _add_services_and_map_hosts_to_it(cluster, provider) -> Tuple[Service, Host, Host]:
    service_1 = cluster.service_add(name="service_1")
    host_1, host_2 = [cluster.host_add(provider.host_create(f"test-host-{i}")) for i in range(2)]
    cluster.hostcomponent_set((host_1, service_1.component()))
    cluster.service_add(name="service_2")
    return service_1, host_1, host_2
