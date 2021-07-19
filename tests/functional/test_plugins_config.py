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
# pylint: disable=W0611, W0621
import copy
import random
from typing import Tuple, Optional, Dict, Literal, Union

import allure
import pytest
from adcm_client.objects import (
    ADCMClient,
    Bundle,
    Component,
    Service,
    Cluster,
    Host,
    Provider,
)
from adcm_pytest_plugin.utils import get_data_dir

# !===== CONSTANTS =====!

# we use 3 clusters to perform on them different actions
# and check that configuration changes only in action recipients,
# but not on other entities (same with service)
CLUSTER_NAMES = ('first', 'second', 'third')
SERVICE_NAMES = ('First', 'Second')
# you can zip it with SERVICE_NAMES
SERVICE_COMPONENT_NAMES = ('single_component', 'another_component')

CLUSTER_UNITS = ('cluster', 'service', 'component')

ClusterUnit = Union[Cluster, Service, Component]
ClusterUnitLiteral = Literal['cluster', 'service', 'component']
ActionSuffix = Literal[
    'int', 'float', 'text', 'file', 'string', 'json', 'map', 'list', 'multijob', 'host'
]


PROVIDER_UNITS = ('provider', 'host')

# !===== FIXTURES =====!


@pytest.fixture()
def initial_config() -> dict:
    """
    Get dictionary with default initial configuration for each cluster, service, component
    """
    return {
        "int": 1,
        "float": 1.0,
        "text": "xxx\nxxx\n",
        "file": "yyyy\nyyyy\n",
        "string": "zzz",
        "json": [{"x": "y"}, {"y": "z"}],
        "map": {"one": "two", "two": "three"},
        "list": ["one", "two", "three"],
    }


@pytest.fixture()
def expected_config() -> dict:
    """
    Get dictionary with expected config values after run of all adcm_config based actions
    """
    return {
        "int": 2,
        "float": 4.0,
        "text": "new new\nxxx\n",
        "file": "new new new\nyyyy\n",
        "string": "double new",
        "json": [{"x": "new"}, {"y": "z"}],
        "map": {"one": "two", "two": "new"},
        "list": ["one", "new", "three"],
    }


@pytest.fixture()
def initial_clusters_config(initial_config: dict) -> dict:
    """
    Return dict with default configuration info
    Use it to change cluster / service / component configuration to compare it with actual config
    """
    return {
        cluster_name: {
            'config': copy.deepcopy(initial_config),
            'services': {
                service_name: {
                    'config': copy.deepcopy(initial_config),
                    'components': {
                        component_name: {
                            'config': copy.deepcopy(initial_config),
                        }
                    },
                }
                for service_name, component_name in zip(SERVICE_NAMES, SERVICE_COMPONENT_NAMES)
            },
        }
        for cluster_name in CLUSTER_NAMES
    }


@pytest.fixture()
def cluster_bundle(sdk_client_fs: ADCMClient, initial_clusters_config: dict):
    """
    Load bundle, create clusters with services from config
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    for cluster_name, cluster_dict in initial_clusters_config.items():
        cluster = bundle.cluster_create(cluster_name)
        for service_name in cluster_dict['services']:
            cluster.service_add(name=service_name)
    return bundle


@pytest.fixture()
def provider_bundle(sdk_client_fs: ADCMClient, initial_providers_config: dict):
    """
    Load bundle, create providers with hosts from config
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    for name in initial_providers_config:
        provider = bundle.provider_create(name)
        for fqdn in initial_providers_config[name]['hosts']:
            provider.host_create(fqdn=fqdn)
    return bundle


@pytest.fixture()
def providers_names(initial_providers_config: Dict[str, Dict]) -> Tuple[str]:
    """Get providers names"""
    return tuple(initial_providers_config.keys())


@pytest.fixture()
def initial_providers_config(initial_config) -> dict:
    """
    Return dict with default configuration info
    Use it to change provider / host configuration to compare it with actual config
    """
    return {
        provider_name: {
            'config': copy.deepcopy(initial_config),
            'hosts': {
                # will be like first_First, first_Second
                f'{provider_name}_{host_suffix}': {'config': copy.deepcopy(initial_config)}
                for host_suffix in ('First', 'Second')
            },
        }
        for provider_name in ('first', 'second', 'third')
    }


@pytest.fixture()
def correct_initial_cluster_config(cluster_bundle: Bundle, initial_clusters_config: dict) -> dict:
    """
    Asserts that initial clusters configuration is correct and returns initial_config
    """
    assert_cluster_config_is_correct(cluster_bundle, initial_clusters_config)
    return initial_clusters_config


@pytest.fixture()
def correct_initial_provider_config(
    provider_bundle: Bundle, initial_providers_config: dict
) -> dict:
    """
    Asserts that initial providers configuration is correct and returns initial_config
    """
    assert_provider_config_is_correct(provider_bundle, initial_providers_config)
    return initial_providers_config


@allure.title('Link cluster component to host')
@pytest.fixture()
def cluster_linked_to_host(
    cluster_bundle: Bundle, provider_bundle: Bundle
) -> Tuple[Cluster, Service, Component, Host]:
    """Get cluster units and host connected with component on host"""
    cluster, service, component = get_random_cluster_service_component(cluster_bundle)
    _, host = get_random_provider_host(provider_bundle)
    cluster.host_add(host)
    cluster.hostcomponent_set((host, component))
    return cluster, service, component, host


# !===== STEPS AND HELPERS =====!


def expect_configuration(actual_config: dict, expected_config: dict, config_owner: str):
    """
    Executes `expect` on each value in expected configuration dict
        against corresponding value in actual configuration
    Use `assert_expectations` to check results and perform assertion itself
    :param actual_config: dict with cluster / service / component actual configuration
    :param expected_config: dict with cluster / service / component expected configuration
    :param config_owner: String to represent configuration owner
                         in error message (e.g. Cluster first)
    """
    for config_key, config_value in expected_config.items():
        assert config_value == actual_config[config_key], (
            f'{config_owner} config "{config_key}" is "{actual_config[config_key]}" '
            f'while expected "{config_value}"'
        )


@allure.step('Check providers configuration')
def assert_provider_config_is_correct(bundle: Bundle, providers_expected_config: dict):
    """
    Assert that all providers' and hosts' configuration equal to expected

    :param bundle: provider bundle to load configuration from
    :param providers_expected_config: dict with expected provider configuration
    """
    # provider dict has `config` and `hosts` keys
    for provider_name, provider_dict in providers_expected_config.items():
        actual_provider_config = (provider := bundle.provider(name=provider_name)).config()
        expected_provider_config = provider_dict['config']
        expect_configuration(
            actual_provider_config, expected_provider_config, f'Provider "{provider_name}"'
        )
        # host dict has `config` in keys
        for host_fqdn, host_dict in provider_dict['hosts'].items():
            actual_host_config = provider.host(fqdn=host_fqdn).config()
            expected_host_config = host_dict['config']
            expect_configuration(
                actual_host_config,
                expected_host_config,
                f'Provider "{provider_name}" host with FQDN "{host_fqdn}"',
            )


@allure.step('Check clusters configuration')
def assert_cluster_config_is_correct(bundle: Bundle, clusters_expected_config: dict):
    """
    Assert that all clusters' and its children's configuration is equal to expected

    :param bundle: cluster bundle to load configuration from
    :param clusters_expected_config: dict with expected cluster configuration
                                     (check initial_clusters_config)
    """
    # cluster dict has `config` and `services` keys
    for cluster_name, cluster_dict in clusters_expected_config.items():
        actual_config = (cluster := bundle.cluster(name=cluster_name)).config()
        expected_config = cluster_dict['config']
        expect_configuration(actual_config, expected_config, f"Cluster {cluster_name}")
        # service dict has `config` and `components` keys
        for service_name, service_dict in cluster_dict['services'].items():
            actual_config = (service := cluster.service(name=service_name)).config()
            expected_config = service_dict['config']
            expect_configuration(
                actual_config,
                expected_config,
                f"Cluster {cluster_name} service {service_name}",
            )
            # component dict has `config` key
            for component_name, component_dict in service_dict['components'].items():
                actual_config = service.component(name=component_name).config()
                expected_config = component_dict['config']
                expect_configuration(
                    actual_config,
                    expected_config,
                    f"Cluster {cluster_name} service {service_name} component {component_name}",
                )


# !===== TESTS =====!


cluster_action_subject = [
    (action_owner, change_subject)
    for action_owner in CLUSTER_UNITS
    for change_subject in CLUSTER_UNITS
]


@pytest.mark.parametrize(
    'action_owner, change_subject',
    cluster_action_subject,
    ids=[
        f"Change {change_subject} configuration with multijob action on {action_owner}"
        for action_owner, change_subject in cluster_action_subject
    ],
)
def test_multijob(
    cluster_bundle: Bundle,
    correct_initial_cluster_config: dict,
    expected_config: dict,
    action_owner: ClusterUnitLiteral,
    change_subject: ClusterUnitLiteral,
):
    """Check multijob tasks change configuration correctly"""
    current_expected_state = correct_initial_cluster_config
    changer = ClusterBundleConfigChanger(cluster_bundle, current_expected_state, expected_config)
    change_func = getattr(changer, f'change_{change_subject}_config_from_{action_owner}')
    change_func('multijob')
    with allure.step("Check multijob action result"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


@pytest.mark.parametrize(
    'action_owner, change_subject',
    cluster_action_subject,
    ids=[
        f"Change {change_subject} configuration with simple action on {action_owner}"
        for action_owner, change_subject in cluster_action_subject
    ],
)
def test_simple_actions(
    cluster_bundle: Bundle,
    correct_initial_cluster_config: dict,
    expected_config: dict,
    action_owner: ClusterUnitLiteral,
    change_subject: ClusterUnitLiteral,
):
    """Test one-by-one config parameter change"""
    current_expected_state = correct_initial_cluster_config
    changer = ClusterBundleConfigChanger(cluster_bundle, current_expected_state, expected_config)
    change_func = getattr(changer, f'change_{change_subject}_config_from_{action_owner}')
    # other keys are already checked in multijob
    change_func('int')
    with allure.step("Check simple actions changed configuration"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


# Sync it with specification
def test_another_service_from_service_by_name(
    cluster_bundle: Bundle,
    correct_initial_cluster_config: dict,
):
    current_expected_state = correct_initial_cluster_config
    with allure.step('Check another service from service by name'):
        cluster = get_random_cluster(cluster_bundle)
        one, another, *_ = cluster.service_list()
        result = one.action(name=f'service_name_{another.name}_int').run().wait()
        assert (
            result == "failed"
        ), f"Service {one.name} shouldn't be able to change {another.name} config"
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


provider_action_subject = [
    (action_owner, change_subject)
    for action_owner in PROVIDER_UNITS
    for change_subject in PROVIDER_UNITS
]


@pytest.mark.parametrize(
    'action_owner, change_subject',
    provider_action_subject,
    ids=[
        f"Change {change_subject} configuration with multijob action on {action_owner}"
        for action_owner, change_subject in provider_action_subject
    ],
)
def test_provider_bundle_multijob(
    provider_bundle: Bundle,
    correct_initial_provider_config: dict,
    expected_config: dict,
    action_owner: str,
    change_subject: str,
):
    """Test multijob action changes config of provider bundle parts"""
    current_expected_state = correct_initial_provider_config
    changer = ProviderBundleConfigChanger(provider_bundle, current_expected_state, expected_config)
    change_func = getattr(changer, f'change_{change_subject}_config_from_{action_owner}')
    change_func('multijob')
    with allure.step("Check multijob actions changed configuration"):
        assert_provider_config_is_correct(provider_bundle, current_expected_state)


@pytest.mark.parametrize(
    'action_owner, change_subject',
    provider_action_subject,
    ids=[
        f"Change {change_subject} configuration with simple action on {action_owner}"
        for action_owner, change_subject in provider_action_subject
    ],
)
def test_provider_bundle_simple_action(
    provider_bundle: Bundle,
    correct_initial_provider_config: dict,
    expected_config: dict,
    action_owner: str,
    change_subject: str,
):
    """Test simple action changes config of provider bundle parts"""
    current_expected_state = correct_initial_provider_config
    changer = ProviderBundleConfigChanger(provider_bundle, current_expected_state, expected_config)
    change_func = getattr(changer, f'change_{change_subject}_config_from_{action_owner}')
    change_func('int')
    with allure.step("Check multijob actions changed configuration"):
        assert_provider_config_is_correct(provider_bundle, current_expected_state)


def test_host_actions(
    cluster_bundle: Bundle,
    cluster_linked_to_host: Tuple[Cluster, Service, Component, Host],
    correct_initial_cluster_config: dict,
    expected_config: dict,
):
    """Test cluster, service and component "on host" actions"""
    current_expected_state = correct_initial_cluster_config
    cluster, service, component, host = cluster_linked_to_host
    changer = ClusterBundleConfigChanger(cluster_bundle, current_expected_state, expected_config)
    with allure.step('Check cluster host action'):
        run_action(host, 'cluster_host', by_display_name=True)
        changer.change_cluster_config(cluster.name, 'int')
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)
    with allure.step('Check service host action'):
        run_action(host, 'service_host', by_display_name=True)
        changer.change_service_config(cluster.name, service.name, 'int')
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)
    with allure.step('Check component host action'):
        run_action(host, 'component_host', by_display_name=True)
        changer.change_component_config(cluster.name, service.name, component.name, 'int')
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


# !===== UTILITIES =====!


def get_config_key_from_action_name(action_name: str) -> Optional[str]:
    """Get config_key value to pass to _change_x_config in Changers"""
    return action_name.rsplit('_', maxsplit=1)[-1] if 'multijob' not in action_name else None


def run_action(
    unit: Union[ClusterUnit, Provider, Host],
    action_name: str,
    config: Optional[dict] = None,
    by_display_name: bool = False,
):
    action = (
        unit.action(name=action_name)
        if not by_display_name
        else unit.action(display_name=action_name)
    )
    action.run(config=config or {}).try_wait()


def get_random_cluster(cluster_bundle: Bundle) -> Cluster:
    return random.choice(cluster_bundle.cluster_list())


def get_random_cluster_service(cluster_bundle: Bundle) -> Tuple[Cluster, Service]:
    return (
        (cluster := random.choice(cluster_bundle.cluster_list())),
        random.choice(cluster.service_list()),
    )


def get_random_cluster_service_component(
    cluster_bundle: Bundle,
) -> Tuple[Cluster, Service, Component]:
    return (
        (cluster := random.choice(cluster_bundle.cluster_list())),
        (service := random.choice(cluster.service_list())),
        random.choice(service.component_list()),
    )


class ClusterBundleConfigChanger:
    """
    Implements actions *on* cluster units *from* cluster units from same or another level
    """

    def __init__(self, cluster_bundle: Bundle, current_state: dict, expected_state: dict):
        self.bundle = cluster_bundle
        self.clusters_state = current_state
        self.expected_state = expected_state

    def change_cluster_config_from_cluster(self, action_suffix: ActionSuffix):
        cluster = get_random_cluster(self.bundle)
        action_name = f'cluster_{action_suffix}'
        with allure.step(f"Run {action_name} action on cluster {cluster.name} to configure itself"):
            run_action(cluster, action_name)
            self.change_cluster_config(cluster.name, get_config_key_from_action_name(action_name))

    def change_cluster_config_from_service(self, action_suffix: ActionSuffix):
        cluster, service = get_random_cluster_service(self.bundle)
        action_name = f'cluster_{action_suffix}'
        with allure.step(
            f'Run "{action_name}" on service {service.name} to configure cluster {cluster.service}'
        ):
            run_action(service, action_name)
            self.change_cluster_config(cluster.name, get_config_key_from_action_name(action_name))

    def change_cluster_config_from_component(self, action_suffix: ActionSuffix):
        cluster, service, component = get_random_cluster_service_component(self.bundle)
        action_name = f'cluster_{action_suffix}'
        with allure.step(
            'Run "{}" on component {} from {} service to configure {} cluster'.format(
                action_name, component.name, service.name, cluster.name
            )
        ):
            run_action(component, action_name)
            self.change_cluster_config(cluster.name, get_config_key_from_action_name(action_name))

    def change_service_config_from_cluster(self, action_suffix: ActionSuffix):
        cluster, service = get_random_cluster_service(self.bundle)
        action_name = f'service_name_{service.name}_{action_suffix}'
        with allure.step(
            f'Run "{action_name} on {cluster.name} cluster to configure {service.name} service'
        ):
            run_action(cluster, action_name)
            self.change_service_config(
                cluster.name, service.name, get_config_key_from_action_name(action_name)
            )

    def change_service_config_from_service(self, action_suffix: ActionSuffix):
        cluster, service = get_random_cluster_service(self.bundle)
        action_name = f'service_{action_suffix}'
        with allure.step(f'Run "{action_name}" on {service.name} service to configure itself'):
            run_action(service, action_name)
            self.change_service_config(
                cluster.name, service.name, get_config_key_from_action_name(action_name)
            )

    def change_service_config_from_component(self, action_suffix: ActionSuffix):
        cluster, service, component = get_random_cluster_service_component(self.bundle)
        action_name = f'service_{action_suffix}'
        with allure.step(
            f'Run "{action_name}" on {component.name} component to configure {service.name} service'
        ):
            run_action(component, action_name)
            self.change_service_config(
                cluster.name, service.name, get_config_key_from_action_name(action_name)
            )

    def change_component_config_from_cluster(self, action_suffix: ActionSuffix):
        cluster, service, component = get_random_cluster_service_component(self.bundle)
        action_name = f'component_{component.name}_{service.name}_{action_suffix}'
        with allure.step(
            'Run "{}" on {} cluster to configure {} on {} service'.format(
                action_name, cluster.name, component.name, service.name
            )
        ):
            run_action(cluster, action_name)
            self.change_component_config(
                cluster.name,
                service.name,
                component.name,
                get_config_key_from_action_name(action_name),
            )

    def change_component_config_from_service(self, action_suffix: ActionSuffix):
        cluster, service, component = get_random_cluster_service_component(self.bundle)
        action_name = f'component_name_{component.name}_{action_suffix}'
        with allure.step(
            f'Run "{action_name}" on {service.name} service to configure {component.name} component'
        ):
            run_action(service, action_name)
            self.change_component_config(
                cluster.name,
                service.name,
                component.name,
                get_config_key_from_action_name(action_name),
            )

    def change_component_config_from_component(self, action_suffix: ActionSuffix):
        cluster, service, component = get_random_cluster_service_component(self.bundle)
        action_name = f'component_{action_suffix}'
        with allure.step(f'Run "{action_name}" on {component.name} component to configure itself'):
            run_action(component, action_name)
            self.change_component_config(
                cluster.name,
                service.name,
                component.name,
                get_config_key_from_action_name(action_name),
            )

    def change_cluster_config(self, cluster_name: str, config_key: Optional[str] = None):
        if config_key:
            self.clusters_state[cluster_name]['config'][config_key] = self.expected_state[
                config_key
            ]
        else:
            self.clusters_state[cluster_name]['config'] = self.expected_state

    def change_service_config(
        self, cluster_name: str, service_name: str, config_key: Optional[str] = None
    ):
        service_dict = self.clusters_state[cluster_name]['services'][service_name]
        if config_key:
            service_dict['config'][config_key] = self.expected_state[config_key]
        else:
            service_dict['config'] = self.expected_state

    def change_component_config(
        self,
        cluster_name: str,
        service_name: str,
        component_name: str,
        config_key: Optional[str] = None,
    ):
        component_dict = self.clusters_state[cluster_name]['services'][service_name]['components'][
            component_name
        ]
        if config_key:
            component_dict['config'][config_key] = self.expected_state[config_key]
        else:
            component_dict['config'] = self.expected_state


def get_random_provider(provider_bundle: Bundle) -> Provider:
    return random.choice(provider_bundle.provider_list())


def get_random_provider_host(provider_bundle: Bundle) -> Tuple[Provider, Host]:
    return (provider := get_random_provider(provider_bundle)), random.choice(provider.host_list())


class ProviderBundleConfigChanger:
    """
    Implements actions *on* provider units *from* provider units from same or another level
    """

    def __init__(self, provider_bundle: Bundle, current_state: dict, expected_state: dict):
        self.bundle = provider_bundle
        self.providers_state = current_state
        self.expected_state = expected_state

    def change_provider_config_from_provider(self, action_suffix: ActionSuffix):
        provider = get_random_provider(self.bundle)
        action_name = f'provider_{action_suffix}'
        with allure.step(f'Run "{action_name}" on {provider.name} provider to configure itself'):
            run_action(provider, action_name)
            self._change_provider_config(
                provider.name, get_config_key_from_action_name(action_name)
            )

    def change_provider_config_from_host(self, action_suffix: ActionSuffix):
        provider, host = get_random_provider_host(self.bundle)
        action_name = f'provider_{action_suffix}'
        with allure.step(f'Run "{action_name}" on {host.fqdn} host to configure {provider.name}'):
            run_action(provider, action_name)
            self._change_provider_config(
                provider.name, get_config_key_from_action_name(action_name)
            )

    def change_host_config_from_provider(self, action_suffix: ActionSuffix):
        provider, host = get_random_provider_host(self.bundle)
        action_name = f'host_{action_suffix}'
        with allure.step(
            f'Run "{action_name}" on {provider.name} provider to configure {host.fqdn} host'
        ):
            run_action(provider, action_name, config={'fqdn': host.fqdn})
            self._change_host_config(
                provider.name, host.fqdn, get_config_key_from_action_name(action_name)
            )

    def change_host_config_from_host(self, action_suffix: ActionSuffix):
        provider, host = get_random_provider_host(self.bundle)
        action_name = f'host_{action_suffix}'
        with allure.step(f'Run "{action_name}" on {host.fqdn} host to configure itself'):
            run_action(provider, action_name, config={'fqdn': host.fqdn})
            self._change_host_config(
                provider.name, host.fqdn, get_config_key_from_action_name(action_name)
            )

    def _change_provider_config(self, provider_name: str, config_key: Optional[str] = None):
        if config_key:
            self.providers_state[provider_name]['config'][config_key] = self.expected_state[
                config_key
            ]
        else:
            self.providers_state[provider_name]['config'] = self.expected_state

    def _change_host_config(
        self, provider_name: str, host_fqdn: str, config_key: Optional[str] = None
    ):
        host_dict = self.providers_state[provider_name]['hosts'][host_fqdn]
        if config_key:
            host_dict['config'][config_key] = self.expected_state[config_key]
        else:
            host_dict['config'] = self.expected_state
