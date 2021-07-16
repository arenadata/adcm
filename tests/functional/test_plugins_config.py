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
from typing import Tuple, Any, Optional, Dict

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle
from adcm_pytest_plugin.utils import get_data_dir
from delayed_assert import assert_expectations, expect


# we use 3 clusters to perform on them different actions
# and check that configuration changes only in action recipients,
# but not on other entities (same with service)
CLUSTER_NAMES = ('first', 'second', 'third')

SERVICE_NAMES = ('First', 'Second')

SERVICE_COMPONENT_NAMES = ('single_component', 'another_component')


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
def keys_clusters(initial_config: dict) -> Tuple[Tuple[str, str], ...]:
    """
    Get config_key - cluster action distribution to *randomize* and isolate config changes
    """
    return tuple((key, CLUSTER_NAMES[i % 3]) for i, key in enumerate(initial_config.keys()))


@pytest.fixture()
def keys_clusters_services(initial_config: dict) -> Tuple[Tuple[str, str, str], ...]:
    """
    Get config_key - cluster - service action distribution to *randomize* and isolate config changes
    """
    return tuple(
        (key, CLUSTER_NAMES[i % 3], SERVICE_NAMES[i % 2])
        for i, key in enumerate(initial_config.keys())
    )


@pytest.fixture()
def keys_clusters_services_components(
    initial_config: dict,
) -> Tuple[Tuple[str, str, str, str], ...]:
    """
    Get config_key - cluster - service - component action distribution
    """
    return tuple(
        (key, CLUSTER_NAMES[i % 3], SERVICE_NAMES[i % 2], SERVICE_COMPONENT_NAMES[i % 2])
        for i, key in enumerate(initial_config.keys())
    )


# !===== STEPS AND HELPERS =====!


def expect_configuration(actual_config: dict, expected_config: dict, config_owner: str):
    """
    Executes `expect` on each value in expected configuration dict
        against corresponding value in actual configuration
    Use `assert_expectations` to check results and perform assertion itself
    :param actual_config: dict with cluster / service / component actual configuration
    :param expected_config: dict with cluster / service / component expected configuration
    :param config_owner: String to represent configuration owner in error message (e.g. Cluster first)
    """
    for config_key, config_value in expected_config.items():
        expect(
            config_value == actual_config[config_key],
            (
                f'{config_owner.strip()} config "{config_key}" is "{actual_config[config_key]}" '
                f'while expected "{config_value}"'
            ),
        )


@allure.step('Check clusters configuration')
def assert_cluster_config_is_correct(bundle: Bundle, clusters_expected_config: dict):
    """
    Assert that all clusters' and it's children's configuration equal to expected

    Use in test context only
    :param bundle: cluster bundle to load configuration from
    :param clusters_expected_config: dict with expected cluster configuration (check initial_clusters_config)
    """
    # cluster dict has `config` and `services` keys
    for cluster_name, cluster_dict in clusters_expected_config.items():
        actual_cluster_config = (cluster := bundle.cluster(name=cluster_name)).config()
        expected_cluster_config = cluster_dict['config']
        expect_configuration(
            actual_cluster_config, expected_cluster_config, f"Cluster {cluster_name}"
        )
        # service dict has `config` and `components` keys
        for service_name, service_dict in cluster_dict['services'].items():
            actual_service_config = (service := cluster.service(name=service_name)).config()
            expected_service_config = service_dict['config']
            expect_configuration(
                actual_service_config,
                expected_service_config,
                f"Cluster {cluster_name} service {service_name}",
            )
            # component dict has `config` key
            for component_name, component_dict in service_dict['components'].items():
                actual_component_config = service.component(name=component_name).config()
                expected_component_config = component_dict['config']
                expect_configuration(
                    actual_component_config,
                    expected_component_config,
                    f"Cluster {cluster_name} service {service_name} component {component_name}",
                )
    assert_expectations()


@allure.step("Check initial clusters configuration is correct")
def get_correct_initial_cluster_config(cluster_bundle: Bundle, initial_config: dict) -> dict:
    """
    Asserts that initial clusters configuration is correct and returns initial_config
    """
    assert_cluster_config_is_correct(cluster_bundle, initial_config)
    return initial_config


@allure.step("Check initial providers configuration is correct")
def get_correct_initial_provider_config(provider_bundle: Bundle, initial_config: dict) -> dict:
    """
    Asserts that initial providers configuration is correct and returns initial_config
    """
    assert_provider_config_is_correct(provider_bundle, initial_config)
    return initial_config


def _update_component_config(
    cluster_config: dict,
    cluster: str,
    service: str,
    component: str,
    value: Optional[Any] = None,
    key: Optional[str] = None,
):
    """
    Updates value of component in clusters config
    If key is None - sets full component config to value
    """
    if key:
        cluster_config[cluster]['services'][service]['components'][component]['config'][key] = value
    else:
        cluster_config[cluster]['services'][service]['components'][component]['config'] = value


# !===== TESTS =====!


def test_cluster_config(
    cluster_bundle: Bundle, initial_clusters_config: dict, expected_config: dict, keys_clusters
):
    """
    Test cluster level adcm_config actions on cluster
    """
    # expected_state will be changing during actions execution
    # from start it's the same as initial clusters configuration
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    with allure.step('Check cluster keys'):
        for config_key, cluster_name in keys_clusters:
            cluster = cluster_bundle.cluster(name=cluster_name)
            cluster.action(name='cluster_' + config_key).run().try_wait()
            current_expected_state[cluster_name]["config"][config_key] = expected_config[config_key]
            assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_cluster_multijob(
    cluster_bundle: Bundle, initial_clusters_config: dict, expected_config: dict
):
    """
    Multijob task should successfully change cluster configuration
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    cluster_name = random.choice(CLUSTER_NAMES)
    with allure.step(f"Run multijob actions on cluster {cluster_name}"):
        cluster = cluster_bundle.cluster(name=cluster_name)
        cluster.action(name='cluster_multijob').run().try_wait()
        current_expected_state[cluster_name]['config'] = expected_config
    with allure.step("Check multijob action result"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_cluster_config_from_service(
    cluster_bundle: Bundle,
    initial_clusters_config: dict,
    expected_config: dict,
    keys_clusters_services: Tuple[Tuple[str, str, str], ...],
):
    """
    Test cluster config change from service adcm_config action
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    with allure.step('Check service actions result'):
        for config_key, cluster_name, service_name in keys_clusters_services:
            cluster = cluster_bundle.cluster(name=cluster_name)
            service = cluster.service(name=service_name)
            service.action(name='cluster_' + config_key).run().try_wait()
            current_expected_state[cluster_name]["config"][config_key] = expected_config[config_key]
            assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_cluster_config_from_service_multijob(
    cluster_bundle: Bundle, initial_clusters_config: dict, expected_config: dict
):
    """
    Multijob task should successfully change cluster configuration
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    cluster_name = random.choice(CLUSTER_NAMES)
    service_name = random.choice(SERVICE_NAMES)
    with allure.step(
        f"Run multijob action on service {service_name} to alter cluster {cluster_name}"
    ):
        service = cluster_bundle.cluster(name=cluster_name).service(name=service_name)
        service.action(name='cluster_multijob').run().try_wait()
        current_expected_state[cluster_name]['config'] = expected_config
    with allure.step("Check multijob action result"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_service_config_from_cluster_by_name(
    cluster_bundle: Bundle,
    initial_clusters_config: dict,
    expected_config: dict,
    keys_clusters_services: Tuple[Tuple[str, str, str], ...],
):
    """
    Change service configuration from cluster action
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    with allure.step('Check service config from cluster by name'):
        for config_key, cluster_name, service_name in keys_clusters_services:
            cluster = cluster_bundle.cluster(name=cluster_name)
            cluster.action(name='service_name_' + service_name + '_' + config_key).run().try_wait()
            current_expected_state[cluster_name]["services"][service_name]['config'][
                config_key
            ] = expected_config[config_key]
            assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_service_config_from_cluster_by_name_multijob(
    cluster_bundle: Bundle, initial_clusters_config: dict, expected_config: dict
):
    """
    Change service configuration from cluster multijob action
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    cluster_name = random.choice(CLUSTER_NAMES)
    service_name = random.choice(SERVICE_NAMES)
    with allure.step(
        f"Run multijob action on cluster {cluster_name} to alter service {service_name}"
    ):
        cluster = cluster_bundle.cluster(name=cluster_name)
        cluster.action(name=f'service_name_{service_name}_multijob').run().try_wait()
        current_expected_state[cluster_name]['services'][service_name]['config'] = expected_config
    with allure.step("Check multijob action result"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_service_config_from_service_by_name(
    cluster_bundle: Bundle,
    initial_clusters_config: dict,
    expected_config: dict,
    keys_clusters_services: Tuple[Tuple[str, str, str], ...],
):
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    with allure.step('Check service config from service by name'):
        for config_key, cluster_name, service_name in keys_clusters_services:
            service = cluster_bundle.cluster(name=cluster_name).service(name=service_name)
            service.action(name='service_name_' + service_name + '_' + config_key).run().try_wait()
            current_expected_state[cluster_name]["services"][service_name]['config'][
                config_key
            ] = expected_config[config_key]
            assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_service_config_from_service_by_name_multijob(
    cluster_bundle: Bundle, initial_clusters_config: dict, expected_config: dict
):
    """
    Change service configuration by service name multijob action
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    cluster_name = random.choice(CLUSTER_NAMES)
    service_name = random.choice(SERVICE_NAMES)
    with allure.step(f"Run multijob action on service {service_name}"):
        service = cluster_bundle.cluster(name=cluster_name).service(name=service_name)
        service.action(name=f'service_name_{service_name}_multijob').run().try_wait()
        current_expected_state[cluster_name]['services'][service_name]['config'] = expected_config
    with allure.step("Check multijob action result"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_another_service_from_service_by_name(
    cluster_bundle: Bundle,
    initial_clusters_config: dict,
    expected_config: dict,
    keys_clusters_services: Tuple[Tuple[str, str, str], ...],
):
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    with allure.step('Check another service from service by name'):
        for config_key, cluster_name, service_name in filter(
            lambda x: x[-1] != "Second", keys_clusters_services
        ):
            second = cluster_bundle.cluster(name=cluster_name).service(name='Second')
            result = (
                second.action(name='service_name_' + service_name + '_' + config_key).run().wait()
            )
            assert result == "failed", "Job expected to be failed"
            assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_service_config(
    cluster_bundle: Bundle,
    initial_clusters_config: dict,
    expected_config: dict,
    keys_clusters_services: Tuple[Tuple[str, str, str], ...],
):
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    with allure.step('Check service config change actions'):
        for config_key, cluster_name, service_name in keys_clusters_services:
            cluster = cluster_bundle.cluster(name=cluster_name)
            service = cluster.service(name=service_name)
            service.action(name='service_' + config_key).run().try_wait()
            current_expected_state[cluster_name]["services"][service_name]['config'][
                config_key
            ] = expected_config[config_key]
            assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_service_config_multijob(
    cluster_bundle: Bundle, initial_clusters_config: dict, expected_config: dict
):
    """
    Change service configuration by multijob action
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    cluster_name = random.choice(CLUSTER_NAMES)
    service_name = random.choice(SERVICE_NAMES)
    with allure.step(f"Run multijob actions on service {service_name}"):
        service = cluster_bundle.cluster(name=cluster_name).service(name=service_name)
        service.action(name='service_multijob').run().try_wait()
        current_expected_state[cluster_name]['services'][service_name]['config'] = expected_config
    with allure.step("Check multijob action result"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_component_config(
    cluster_bundle: Bundle,
    initial_clusters_config: dict,
    expected_config: dict,
    keys_clusters_services_components: Tuple[Tuple[str, str, str, str], ...],
):
    """
    Component's configuration can be changed with adcm_config plugin action
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    with allure.step("Run component config change actions"):
        for (
            config_key,
            cluster_name,
            service_name,
            component_name,
        ) in keys_clusters_services_components:
            component = (
                cluster_bundle.cluster(name=cluster_name)
                .service(name=service_name)
                .component(name=component_name)
            )
            component.action(name='component_' + config_key).run().try_wait()
            _update_component_config(
                current_expected_state,
                cluster_name,
                service_name,
                component_name,
                expected_config[config_key],
                config_key,
            )
            assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


def test_component_config_multijob(
    cluster_bundle: Bundle, initial_clusters_config: dict, expected_config: dict
):
    """
    Change component configuration by multijob action
    """
    current_expected_state = get_correct_initial_cluster_config(
        cluster_bundle, initial_clusters_config
    )
    cluster_name = random.choice(CLUSTER_NAMES)
    service_name, component_name = random.choice(tuple(zip(SERVICE_NAMES, SERVICE_COMPONENT_NAMES)))

    with allure.step(f"Run multijob actions on service {service_name}"):
        component = (
            cluster_bundle.cluster(name=cluster_name)
            .service(name=service_name)
            .component(name=component_name)
        )
        component.action(name='component_multijob').run().try_wait()
        _update_component_config(
            current_expected_state, cluster_name, service_name, component_name, expected_config
        )
    with allure.step("Check multijob action result"):
        assert_cluster_config_is_correct(cluster_bundle, current_expected_state)


@pytest.fixture()
def initial_providers_config(initial_config) -> dict:
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


def sparse_matrix(*vectors):
    lengs = []
    for a in vectors:
        lengs.append(len(a))

    max_lengs_vector_idx = lengs.index(max(lengs))
    for i, _ in enumerate(vectors[max_lengs_vector_idx]):
        tmp = []
        for j, a in enumerate(vectors):
            tmp.append(a[i % lengs[j]])
        yield tuple(tmp)


@allure.step('Check providers configuration')
def assert_provider_config_is_correct(bundle: Bundle, providers_expected_config: dict):
    """
    Assert that all providers' and hosts' configuration equal to expected

    Use in test context only
    :param bundle: provider bundle to load configuration from
    :param providers_expected_config: dict with expected provider configuration (check initial_providers_config)
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
    assert_expectations()


@pytest.fixture()
def provider_bundle(sdk_client_fs: ADCMClient, initial_providers_config: dict):
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


def test_provider_config(
    provider_bundle: Bundle,
    initial_providers_config: dict,
    expected_config: dict,
    providers_names: Tuple[str],
):
    """
    Test provider config change from provider scope
    """
    current_expected_state = get_correct_initial_provider_config(
        provider_bundle, initial_providers_config
    )
    with allure.step('Check provider config'):
        for config_key, provider_name in sparse_matrix(
            tuple(expected_config.keys()), providers_names
        ):
            provider = provider_bundle.provider(name=provider_name)
            provider.action(name='provider_' + config_key).run().try_wait()
            current_expected_state[provider_name]["config"][config_key] = expected_config[
                config_key
            ]

    assert_provider_config_is_correct(provider_bundle, current_expected_state)


def test_provider_multijob(
    provider_bundle: Bundle, initial_providers_config: dict, expected_config: dict
):
    """
    Test provider multijob action from provider scope
    """
    current_expected_state = get_correct_initial_provider_config(
        provider_bundle, initial_providers_config
    )
    provider_name = random.choice(tuple(initial_providers_config.keys()))
    with allure.step(f'Check provider config change multijob action on provider "{provider_name}"'):
        provider = provider_bundle.provider(name=provider_name)
        provider.action(name='provider_multijob').run().try_wait()
        current_expected_state[provider_name]['config'] = expected_config
        assert_provider_config_is_correct(provider_bundle, current_expected_state)


def test_host_config(
    provider_bundle: Bundle,
    initial_providers_config: dict,
    expected_config: dict,
    providers_names: Tuple[str],
):
    current_expected_state = get_correct_initial_provider_config(
        provider_bundle, initial_providers_config
    )
    with allure.step('Check host config'):
        for config_key, provider_name, host_idx in sparse_matrix(
            tuple(expected_config.keys()), providers_names, [0, 1]
        ):
            provider = provider_bundle.provider(name=provider_name)
            fqdn = list(initial_providers_config[provider_name]['hosts'].keys())[host_idx]
            host = provider.host(fqdn=fqdn)
            host.action(name='host_' + config_key).run().try_wait()
            current_expected_state[provider_name]["hosts"][fqdn]['config'][
                config_key
            ] = expected_config[config_key]
            assert_provider_config_is_correct(provider_bundle, current_expected_state)


def test_host_multijob(
    provider_bundle: Bundle, initial_providers_config: dict, expected_config: dict
):
    """
    Test host multijob action from host scope
    """
    current_expected_state = get_correct_initial_provider_config(
        provider_bundle, initial_providers_config
    )
    provider_name = random.choice(tuple(initial_providers_config.keys()))
    host_fqdn = random.choice(tuple(initial_providers_config[provider_name]['hosts'].keys()))
    with allure.step(
        f'Check host config change multijob action on provider {provider_name} on host "{host_fqdn}"'
    ):
        host = provider_bundle.provider(name=provider_name).host(fqdn=host_fqdn)
        host.action(name='host_multijob').run().try_wait()
        current_expected_state[provider_name]['hosts'][host_fqdn]['config'] = expected_config
        assert_provider_config_is_correct(provider_bundle, current_expected_state)


def test_host_config_from_provider(
    provider_bundle: Bundle,
    initial_providers_config: dict,
    expected_config: dict,
    providers_names: Tuple[str],
):
    current_expected_state = get_correct_initial_provider_config(
        provider_bundle,
        initial_providers_config,
    )
    with allure.step('Check host config from provider'):
        for config_key, provider_name, host_idx in sparse_matrix(
            tuple(expected_config.keys()), providers_names, [0, 1]
        ):
            provider = provider_bundle.provider(name=provider_name)
            fqdn = list(initial_providers_config[provider_name]['hosts'].keys())[host_idx]
            provider.action(name='host_' + config_key).run(config={"fqdn": fqdn}).try_wait()
            current_expected_state[provider_name]["hosts"][fqdn]['config'][
                config_key
            ] = expected_config[config_key]
            assert_provider_config_is_correct(provider_bundle, current_expected_state)


def test_host_config_from_provider_multijob(
    provider_bundle: Bundle, initial_providers_config: dict, expected_config: dict
):
    """
    Test change host config from provider multijob action
    """
    current_expected_state = get_correct_initial_provider_config(
        provider_bundle, initial_providers_config
    )
    provider_name = random.choice(tuple(initial_providers_config.keys()))
    host_fqdn = random.choice(tuple(initial_providers_config[provider_name]['hosts'].keys()))
    with allure.step(f'Check provider config change multijob action on provider "{provider_name}"'):
        provider = provider_bundle.provider(name=provider_name)
        provider.action(name='host_multijob').run(config={"fqdn": host_fqdn}).try_wait()
        current_expected_state[provider_name]['hosts'][host_fqdn]['config'] = expected_config
        assert_provider_config_is_correct(provider_bundle, current_expected_state)
