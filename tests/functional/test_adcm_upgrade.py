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

"""Tests for ADCM upgrade"""

# pylint:disable=redefined-outer-name

import random
from contextlib import contextmanager
from pathlib import Path
from typing import Collection, Iterable, List, Tuple, Union

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import (
    ADCMClient,
    Bundle,
    Cluster,
    Component,
    GroupConfig,
    Host,
    Job,
    Provider,
    Service,
    Task,
    Upgrade,
)
from adcm_pytest_plugin import params
from adcm_pytest_plugin.docker.adcm import ADCM
from adcm_pytest_plugin.params import ADCMVersionParam
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import catch_failed, get_data_dir, random_string
from tests.functional.plugin_utils import (
    build_objects_checker,
    build_objects_comparator,
)
from tests.functional.tools import AnyADCMObject, get_config, get_objects_via_pagination
from tests.library.assertions import dicts_are_equal, dicts_are_not_equal
from tests.library.utils import previous_adcm_version_tag
from tests.upgrade_utils import upgrade_adcm_version

AVAILABLE_ACTIONS = {
    "single_state-available",
    "state_list-available",
    "state_any-available",
}


@pytest.fixture(scope="session")
def upgrade_target(cmd_opts) -> Tuple[str, str]:
    """Actual ADCM version"""
    if not cmd_opts.adcm_image:
        pytest.fail("CLI parameter adcm_image should be provided")
    return tuple(cmd_opts.adcm_image.split(":", maxsplit=2))  # type: ignore


def old_adcm_images() -> List[ADCMVersionParam]:
    """A list of old ADCM images"""
    return parametrized_by_adcm_version(adcm_min_version="2019.10.08")[0]


def _create_cluster(sdk_client_fs: ADCMClient, bundle_dir: str = "cluster_bundle") -> Cluster:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_dir))
    cluster_name = f"test_{random_string()}"
    return bundle.cluster_prototype().cluster_create(name=cluster_name)


def _create_host(sdk_client_fs: ADCMClient, bundle_dir: str = "hostprovider") -> Host:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_dir))
    provider = bundle.provider_create(name=f"test_{random_string()}")
    return provider.host_create(fqdn=f"test-host-{random_string()}")


@allure.step("Check actions availability")
def _assert_available_actions(obj: AnyADCMObject):
    obj.reread()
    actions = {action.name for action in obj.action_list()}
    assert (
        actions == AVAILABLE_ACTIONS
    ), f"Unexpected list of available actions!\nExpected: {AVAILABLE_ACTIONS}\nActual:{actions}"


@allure.step("Check that previously created cluster exists")
def _check_that_cluster_exists(sdk_client_fs: ADCMClient, cluster: Cluster) -> None:
    assert len(sdk_client_fs.cluster_list()) == 1, "Only one cluster expected to be"
    with catch_failed(ObjectNotFound, "Previously created cluster not found"):
        sdk_client_fs.cluster(name=cluster.name)


@allure.step("Check that previously created service exists")
def _check_that_host_exists(cluster: Cluster, host: Host) -> None:
    assert len(cluster.host_list()) == 1, "Only one host expected to be"
    with catch_failed(ObjectNotFound, "Previously created host not found"):
        cluster.host(fqdn=host.fqdn)


@allure.step("Check encryption")
def _check_encryption(obj: Union[Cluster, Service]) -> None:
    assert obj.action(name="check-password").run().wait() == "success"


@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize("image", old_adcm_images(), ids=repr, indirect=True)
def test_upgrade_adcm(
    launcher,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    adcm_image_tags: Tuple[str, str],
) -> None:
    """Test adcm upgrade"""
    cluster = _create_cluster(sdk_client_fs)
    host = _create_host(sdk_client_fs)
    cluster.host_add(host)

    upgrade_adcm_version(launcher, sdk_client_fs, adcm_api_credentials, adcm_image_tags)

    _check_that_cluster_exists(sdk_client_fs, cluster)
    _check_that_host_exists(cluster, host)


@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize("image", old_adcm_images(), ids=repr, indirect=True)
def test_pass_in_config_encryption_after_upgrade(
    launcher,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    adcm_image_tags: Tuple[str, str],
) -> None:
    """Test adcm upgrade with encrypted fields"""
    cluster = _create_cluster(sdk_client_fs, "cluster_with_pass_verify")
    service = cluster.service_add(name="PassCheckerService")

    config_diff = dict(password="q1w2e3r4")
    cluster.config_set_diff(config_diff)
    service.config_set_diff(config_diff)

    upgrade_adcm_version(launcher, sdk_client_fs, adcm_api_credentials, adcm_image_tags)

    _check_encryption(cluster)
    _check_encryption(service)


@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize("image", [["hub.arenadata.io/adcm/adcm", "2021.06.17.06"]], ids=repr, indirect=True)
def test_actions_availability_after_upgrade(
    launcher,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    upgrade_target: Tuple[str, str],
) -> None:
    """Test that actions availability from old DSL remains the same after update"""
    cluster = _create_cluster(sdk_client_fs, "cluster_with_actions")

    _assert_available_actions(cluster)

    upgrade_adcm_version(launcher, sdk_client_fs, adcm_api_credentials, upgrade_target)

    _assert_available_actions(cluster)


class TestConfigGroupAttrFormatUpgrade:
    """Test that "attr" of config groups are updated correctly in new ADCM versions"""

    LAST_OLD_ATTR_ADCM_VERSION = ["hub.arenadata.io/adcm/adcm", "2022.04.18.13"]

    @pytest.fixture()
    def objects(self, sdk_client_fs):
        """Create one of each object: cluster, service, component, provider"""
        cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'with_config_groups', 'cluster'))
        provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'with_config_groups', 'provider'))
        cluster = cluster_bundle.cluster_create('Test Awesome Cluster')
        service = cluster.service_add(name='test_service')
        provider = provider_bundle.provider_create('Test Awesome Provider')
        return cluster, service, service.component(), provider

    @pytest.fixture()
    def config_groups(self, objects):
        """Create config group for each object"""
        return tuple(obj.group_config_create(f'{obj.__class__.__name__} group') for obj in objects)

    @pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
    @pytest.mark.parametrize("image", [LAST_OLD_ATTR_ADCM_VERSION], ids=repr, indirect=True)
    def test_upgrade_to_new_config_groups_attr_format_unchecked_config(
        self,
        launcher,
        sdk_client_fs: ADCMClient,
        adcm_api_credentials: dict,
        upgrade_target: Tuple[str, str],
        objects,
        config_groups,
    ):
        """
        Test that newly created config groups have new "attr" structure after ADCM upgrade
        from version with old "attr" format to a new one
        """
        old_attrs = self._get_attrs(config_groups)
        new_attrs = self._get_expected_new_attr_for_groups(config_groups)

        self._check_config_groups_attr_are_different_before_upgrade(objects, old_attrs, new_attrs)

        upgrade_adcm_version(launcher, sdk_client_fs, adcm_api_credentials, upgrade_target)

        for obj in (*objects, *config_groups):
            obj.reread()

        self._check_config_groups_attr_are_correct_after_upgrade(objects, config_groups, new_attrs)

    @pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
    @pytest.mark.parametrize("image", [LAST_OLD_ATTR_ADCM_VERSION], ids=repr, indirect=True)
    def test_upgrade_to_new_config_groups_attr_format_checked_config(
        self,
        launcher,
        sdk_client_fs: ADCMClient,
        adcm_api_credentials: dict,
        upgrade_target: Tuple[str, str],
        objects,
        config_groups,
    ):
        """
        Test that config groups with all elements added to them have new "attr" structure after ADCM upgrade
        from version with old "attr" format to a new one
        """
        old_attrs = self._get_attrs(config_groups)

        self._add_all_items_in_config_groups(config_groups)
        new_attrs = self._get_expected_new_attr_for_groups(config_groups)

        self._check_config_groups_attr_are_different_before_upgrade(objects, old_attrs, new_attrs)

        upgrade_adcm_version(launcher, sdk_client_fs, adcm_api_credentials, upgrade_target)

        for obj in (*objects, *config_groups):
            obj.reread()

        self._check_config_groups_attr_are_correct_after_upgrade(objects, config_groups, new_attrs)

    def _check_config_groups_attr_are_different_before_upgrade(self, objects, old_attrs, new_attrs):
        for obj, old_attr, new_attr in zip(objects, old_attrs, new_attrs):
            with allure.step(
                'Check that "attr" before upgrade is different from expected in new version '
                f'for group config of {obj.__class__.__name__}'
            ):
                dicts_are_not_equal(old_attr, new_attr)

    def _check_config_groups_attr_are_correct_after_upgrade(self, objects, config_groups, expected_attrs):
        for obj, group, expected_attr in zip(objects, config_groups, expected_attrs):
            with allure.step(
                'Check that "attr" after upgrade became the one that were expected '
                f'for group config of {obj.__class__.__name__}'
            ):
                dicts_are_equal(group.config(full=True)['attr'], expected_attr)

    def _get_attrs(self, groups: Collection[GroupConfig]):
        return tuple(g.config(full=True)['attr'] for g in groups)

    def _get_expected_new_attr_for_groups(self, groups: Collection[GroupConfig]):
        new_configs_attr = []
        for group in groups:
            attr = group.config(full=True)['attr']
            for key in attr['group_keys']:
                if 'group' not in key:
                    continue
                attr['group_keys'][key] = {
                    'value': False if 'activatable' in key else None,
                    'fields': {**attr['group_keys'][key]},
                }
            for key in attr['custom_group_keys']:
                if 'group' not in key:
                    continue
                attr['custom_group_keys'][key] = {
                    'value': True,
                    'fields': {**attr['custom_group_keys'][key]},
                }
            new_configs_attr.append(attr)
        return tuple(new_configs_attr)

    def _add_all_items_in_config_groups(self, groups: Collection[GroupConfig]):
        for group in groups:
            with allure.step(f'Add all config items to config group: {group.name}'):
                group_config = group.config(full=True)
                group.config_set_diff(
                    {
                        'attr': {
                            **group_config['attr'],
                            'group_keys': {
                                'simple_value': True,
                                'simple_group': {
                                    'valingroup': True,
                                    'readonlyval': True,
                                },
                                'activatable_group': {
                                    'valingroup': True,
                                    'readonlyval': True,
                                },
                            },
                        },
                        'config': {**group_config['config']},
                    }
                )


# !===== Dirty ADCM upgrade =====!


class TestUpgradeFilledADCM:
    """
    Check that ADCM filled with different objects can upgrade correctly:
        - objects didn't loose their configs and "stable" properties
        - objects can be manipulated (you can run actions on them)
    """

    LONG_TEXT = f'{"Many" * 200}Words\nTo \"Say\"\n To (me)\n"' * 20

    # Services

    CHEESE_SERVICE = 'cheese_service'
    SAUCE_SERVICE = 'sauce_service'
    BREAD_SERVICE = 'bread_service'

    # Components

    # on cheese
    MILK_COMPONENT = 'milk'
    # on sauce
    SPICE_COMPONENT = 'spice'
    TOMATO_COMPONENT = 'tomato'
    LEMON_COMPONENT = 'lemon'

    # fixtures

    @pytest.fixture()
    def dirty_adcm(self, sdk_client_fs: ADCMClient) -> dict:
        """
        Fill ADCM with many different objects: bundles, clusters, providers, hosts, jobs.
        All jobs are waited to be finished before returning result dictionary.

        :returns: Dictionary with providers, clusters and sometimes bundles.
        """
        dirty_dir = Path(get_data_dir(__file__)) / "dirty_upgrade"
        (
            simple_provider_bundle,
            simple_providers,
            simple_hosts,
            all_tasks,
        ) = self.create_simple_providers(sdk_client_fs, dirty_dir)
        simple_cluster_bundle, simple_clusters, tasks = self.create_simple_clusters(sdk_client_fs, dirty_dir)
        complex_objects = self.create_complex_providers_and_clusters(sdk_client_fs, dirty_dir)
        upgraded_cluster, not_upgraded_cluster = self.create_upgradable_clusters(sdk_client_fs, dirty_dir)
        all_tasks.extend(tasks)
        _wait_for_tasks(all_tasks)
        with allure.step('Delete one of simple clusters with jobs'):
            self._delete_simple_cluster_with_job(simple_clusters)
        return {
            'simple': {
                'providers': tuple(simple_providers),
                'hosts': tuple(simple_hosts),
                'clusters': tuple(simple_clusters),
                'provider_bundle': simple_provider_bundle,
                'cluster_bundle': simple_cluster_bundle,
            },
            'complex': {
                'providers': {
                    'host_supplier': complex_objects[0],
                    'free_hosts': complex_objects[1],
                },
                'clusters': {
                    'all_services': complex_objects[2],
                    'config_history': complex_objects[3],
                    'not_configured': complex_objects[4],
                },
            },
            'upgrade': {'upgraded': upgraded_cluster, 'not_upgraded': not_upgraded_cluster},
        }

    # Test itself

    @params.including_https
    @pytest.mark.full()
    @pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
    @pytest.mark.parametrize("image", [previous_adcm_version_tag()], indirect=True)
    def test_upgrade_dirty_adcm(
        self,
        adcm_fs: ADCM,
        launcher,
        sdk_client_fs: ADCMClient,
        adcm_api_credentials: dict,
        upgrade_target: Tuple[str, str],
        dirty_adcm: dict,
    ):
        """
        Create previous version ADCM with a lot of different objects.
        Upgrade ADCM.
        Run actions on ADCM.
        """
        objects_are_not_changed = build_objects_checker(changed=None, extractor=_get_object_fields)
        with allure.step('Upgrade ADCM and expect all objects to be same'), objects_are_not_changed(
            sdk_client_fs
        ), self.check_job_related_objects_are_not_changed(sdk_client_fs):
            upgrade_adcm_version(launcher, sdk_client_fs, adcm_api_credentials, upgrade_target)
        self.run_actions_after_upgrade(
            dirty_adcm['complex']['clusters']['all_services'],
            dirty_adcm['complex']['clusters']['config_history'],
            dirty_adcm['simple']['providers'][0],
        )

    # Steps and helpers

    @contextmanager
    def check_job_related_objects_are_not_changed(self, adcm_client: ADCMClient):
        """Freeze jobs and check that they aren't changed after upgrade"""

        def extract_job_info(job: Job) -> dict:
            return {
                'task_id': job.task_id,
                'status': job.status,
                'start_date': job.start_date,
                'finish_date': job.finish_date,
                'log_ids': {log.id for log in job.log_list()},
            }

        comparator = build_objects_comparator(
            get_compare_value=extract_job_info,
            field_name='Job info',
            name_composer=lambda obj: f"Job with id {obj.id}",
        )
        jobs: List[Job] = get_objects_via_pagination(adcm_client.job_list)
        frozen_objects = {job.id: extract_job_info(job) for job in jobs}

        yield

        with allure.step('Assert that Jobs have correct info'):
            for job_id, job_info in frozen_objects.items():
                comparator(adcm_client.job(id=job_id), job_info)

    @allure.step('Create simple providers')
    def create_simple_providers(
        self, adcm_client: ADCMClient, bundle_dir: Path
    ) -> Tuple[Bundle, List[Provider], List[Host], List[Task]]:
        """
        Upload simple_provider bundle
        Create 10 providers and 20 hosts on each provider
        Change config of one of providers and one of hosts
        Run failed actions on 3 of providers
        Run install action on hosts of 2 providers
        """
        provider_bundle = adcm_client.upload_from_fs(bundle_dir / "simple_provider")
        providers = [provider_bundle.provider_create(f'Provider {random_string(6)}') for _ in range(10)]
        one_of_providers = providers[-2]
        one_of_providers.config_set_diff({'ssh_key': self.LONG_TEXT})
        hosts = [
            provider.host_create(f'{random_string(6)}-{random_string(6)}') for _ in range(20) for provider in providers
        ]
        one_of_providers.host_list()[-1].config_set_diff({'hosts_file': self.LONG_TEXT})
        tasks = [provider.action(name='validate').run() for provider in providers[:3]] + [
            host.action(name='install').run() for provider in providers[-2:] for host in provider.host_list()
        ]
        return provider_bundle, providers, hosts, tasks

    @allure.step('Create a lot of simple clusters')
    def create_simple_clusters(
        self, adcm_client: ADCMClient, bundle_dir: Path
    ) -> Tuple[Bundle, List[Cluster], List[Task]]:
        """
        Upload simple_cluster bundle
        Create many clusters:
        - With one service and launched action on component
        - With one service and altered config of cluster, service and component
        - With two services and launched cluster install action

        :returns: Bundle, created clusters and tasks
        """
        amount_of_clusters = 34
        params = {
            'cluster_altered_config': {
                'number_of_segments': 2,
                'auto_reboot': False,
                'textarea': self.LONG_TEXT,
            },
            'service_altered_config': {'simple-is-best': False, 'mode': 'fast'},
            'component_altered_config': {'simpler-is-better': True},
            'cluster_action': 'install',
            'service_with_component': 'Tchaikovsky',
            'lonely_service': 'Shostakovich',
            'component_with_action': 'mazepa',
            'component_with_config': 'symphony',
            'component_action': 'no_sense_to_run_me',
        }
        cluster_bundle = adcm_client.upload_from_fs(bundle_dir / "simple_cluster")
        tasks = []
        with allure.step(f'Create {amount_of_clusters} clusters'):
            clusters = [cluster_bundle.cluster_create(f'Cluster {random_string(8)}') for _ in range(amount_of_clusters)]
        with allure.step('Add one service to clusters and run action on component'):
            for one_service_cluster in clusters[:4]:
                service = one_service_cluster.service_add(name=params['service_with_component'])
                component: Component = service.component(name=params['component_with_action'])
                tasks.append(component.action(name=params['component_action']).run())
        with allure.step('Change config of clusters'):
            for cluster_to_change_config in clusters[6:10]:
                cluster_to_change_config.config_set_diff(params['cluster_altered_config'])
                service = cluster_to_change_config.service_add(name=params['service_with_component'])
                service.config_set_diff(params['service_altered_config'])
                service.component(name=params['component_with_config']).config_set_diff(
                    params['component_altered_config']
                )
        with allure.step('Add two services to clusters and run action on them'):
            for install_cluster_with_two_services in clusters[12:30]:
                install_cluster_with_two_services.service_add(name=params['service_with_component'])
                install_cluster_with_two_services.service_add(name=params['lonely_service'])
                tasks.append(install_cluster_with_two_services.action(name=params['cluster_action']).run())
        return cluster_bundle, clusters, tasks

    @allure.step('Create complex provider and {amount_of_hosts} hosts with prefix "{template}" by action')
    def create_complex_provider(
        self, provider_bundle: Bundle, template: str = 'complex-host', amount_of_hosts: int = 18
    ) -> Tuple[Provider, Task]:
        """
        Create provider, bunch of hosts via action (provide template if you want to use it more than 1 time).

        :returns: Create provider and hosts create tasks
        """
        provider = provider_bundle.provider_create(name=f'Complex Provider {random_string(6)}')
        provider.config_set_diff({'very_important_flag': 54.4})
        task = provider.action(name='create_hosts').run(config={'count': amount_of_hosts, 'template': template})
        return provider, task

    @allure.step('Create two complex providers and three complex clusters')
    def create_complex_providers_and_clusters(
        self, adcm_client: ADCMClient, bundles_directory: Path
    ) -> Tuple[Provider, Provider, Cluster, Cluster, Cluster]:
        """
        Upload complex_provider and complex_cluster

        Create two complex providers:
            1.  Provider that supply hosts for complex clusters
                (all hosts created by provider action and taken by clusters)
            2.  Provider that create multiple hosts via action, run actions on some of hosts
                and then delete multiple of them by host delete action

        And three complex clusters:
            1.  Cluster with all services and finished jobs
            2.  Cluster with config history (on cluster, one service and its components)
            3.  Not configured cluster just with hosts and one service added

        :returns: Tuple with provider and cluster objects in order that is declared above
        """
        provider_bundle = adcm_client.upload_from_fs(bundles_directory / "complex_provider")
        provider_bundle.license_accept()
        provider, host_create_task = self.create_complex_provider(provider_bundle)
        provider_with_free_hosts, _ = self.create_complex_provider(provider_bundle, template='doomed-host')
        self._run_actions_on_host_and_delete_with_action(provider)
        cluster_bundle = adcm_client.upload_from_fs(bundles_directory / "complex_cluster")
        cluster_bundle.license_accept()
        cluster_with_history = self._create_cluster_with_config_history(cluster_bundle)
        # we want to wait for tasks on provider to be finished (for hosts to be created)
        host_create_task.wait()
        cluster_with_all_services = self._create_cluster_with_all_services(
            cluster_bundle, tuple(provider.host_list())[:3]
        )
        cluster_with_hosts = self._create_cluster_with_hosts(cluster_bundle, tuple(provider.host_list())[3:])
        return (
            provider,
            provider_with_free_hosts,
            cluster_with_all_services,
            cluster_with_history,
            cluster_with_hosts,
        )

    @allure.step('Create two upgradable clusters, upgrade one of them')
    def create_upgradable_clusters(self, adcm_client: ADCMClient, bundles_directory: Path) -> Tuple[Cluster, Cluster]:
        """
        1. Upload two bundles with old and new version with possibility of upgrade
        2. Create two clusters of previous version
        3. Run dummy actions on both of them
        4. Upgrade one of clusters

        :returns: Tuple with upgraded cluster and old-version cluster
        """
        old_version_bundle = adcm_client.upload_from_fs(bundles_directory / "cluster_to_upgrade")
        adcm_client.upload_from_fs(bundles_directory / "cluster_greater_version")
        cluster_to_upgrade = old_version_bundle.cluster_create('I will be upgraded')
        good_old_cluster = old_version_bundle.cluster_create('I am good the way I am')
        _wait_for_tasks(
            (
                cluster_to_upgrade.action(name='dummy').run(),
                good_old_cluster.action(name='dummy').run(),
            )
        )
        upgrade: Upgrade = cluster_to_upgrade.upgrade()
        upgrade.do()
        return cluster_to_upgrade, good_old_cluster

    @allure.step('Run some actions in upgraded ADCM')
    def run_actions_after_upgrade(
        self,
        cluster_all_services: Cluster,
        cluster_config_history: Cluster,
        simple_provider: Provider,
    ) -> None:
        """
        Run successful actions on: cluster, service, component.
        Run failed action on provider.
        """
        sauce_service = cluster_config_history.service(name=self.SAUCE_SERVICE)
        run_cluster_action_and_assert_result(cluster_all_services, 'eat_sandwich')
        run_service_action_and_assert_result(sauce_service, 'put_on_bread')
        run_component_action_and_assert_result(sauce_service.component(name=self.SPICE_COMPONENT), 'add_more')
        run_provider_action_and_assert_result(simple_provider, 'validate', status='failed')

    @allure.step('Create complex cluster with all services')
    def _create_cluster_with_all_services(self, cluster_bundle: Bundle, hosts: Tuple[Host, Host, Host]) -> Cluster:
        """
        Create cluster with three services
        Add three hosts on it
        Set components on hosts
        Run some actions
        """
        with allure.step('Create cluster and add services'):
            cluster = cluster_bundle.cluster_create(name='With all services')
            cluster.config_set_diff({'very_important_flag': 1.6})
            cheese_service = cluster.service_add(name=self.CHEESE_SERVICE)
            sauce_service = cluster.service_add(name=self.SAUCE_SERVICE)
            bread_service = cluster.service_add(name=self.BREAD_SERVICE)
            components = {
                self.MILK_COMPONENT: cheese_service.component(name=self.MILK_COMPONENT),
                self.TOMATO_COMPONENT: sauce_service.component(name=self.TOMATO_COMPONENT),
                self.LEMON_COMPONENT: sauce_service.component(name=self.LEMON_COMPONENT),
                self.SPICE_COMPONENT: sauce_service.component(name=self.SPICE_COMPONENT),
            }
        with allure.step('Add hosts'):
            for host in hosts:
                cluster.host_add(host)
        with allure.step('Run actions on the cluster, all components and services'):
            self._run_actions_on_components(cluster, sauce_service, components, hosts)
            _wait_for_tasks(service.action().run() for service in (cheese_service, sauce_service, bread_service))
            cluster.action(name='make_sandwich').run().wait()
        return cluster

    @allure.step('Create cluster with config history')
    def _create_cluster_with_config_history(self, bundle: Bundle) -> Cluster:
        """Create cluster with one service and config history"""

        def get_random_config_map() -> dict:
            return {
                'a_lot_of_text': {
                    'simple_string': random_string(25),
                    'file_pass': random_string(16),
                },
                'from_doc': {
                    'memory_size': random.randint(2, 64),
                    'person': {
                        'name': random_string(13),
                        'age': str(random.randint(14, 80)),
                        'custom_field': random_string(12),
                    },
                },
                'country_codes': [
                    {'country': random_string(12), 'code': int(random.randint(1, 200))} for _ in range(4)
                ],
            }

        def get_component_random_config_map() -> dict:
            return {'illicium': random.random()}

        config_change_iterations = 100
        cluster = bundle.cluster_create(name='Config history')
        cluster.config_set_diff({'very_important_flag': 1.6})
        with allure.step(f"Change cluster's config {config_change_iterations} times"):
            for _ in range(config_change_iterations):
                cluster.config_set_diff(get_random_config_map())
        with allure.step(f"Add service and change its config {config_change_iterations} times"):
            service = cluster.service_add(name=self.SAUCE_SERVICE)
            for _ in range(config_change_iterations):
                service.config_set_diff(get_random_config_map())
        with allure.step(f"Change component's config {config_change_iterations} times"):
            component = service.component()
            for _ in range(config_change_iterations):
                component.config_set_diff(get_component_random_config_map())
        return cluster

    @allure.step('Create cluster, add service {service_name} and add hosts to cluster')
    def _create_cluster_with_hosts(
        self, cluster_bundle: Bundle, hosts: Tuple[Host, ...], service_name: str = SAUCE_SERVICE
    ) -> Cluster:
        """
        Create cluster with given amount of hosts.
        Cluster is not configured (can't run actions on it).
        Cluster has 1 service added.
        """
        cluster = cluster_bundle.cluster_create(name='Cluster with hosts')
        cluster.service_add(name=service_name)
        for host in hosts:
            cluster.host_add(host)
        return cluster

    @allure.step("Run actions on provider's hosts and remove every 4th host by action on host")
    def _run_actions_on_host_and_delete_with_action(self, provider: Provider) -> None:
        """Run dummy actions on each second host and delete each fourth host after tasks are finished"""
        hosts = tuple(provider.host_list())
        _wait_for_tasks(tuple((host.action(name='dummy_action').run() for host in hosts[::2])))
        _wait_for_tasks(tuple((host.action(name='remove_host').run() for host in hosts[::4])))

    def _run_actions_on_components(self, cluster: Cluster, service: Service, components: dict, hosts: tuple):
        """Utility function to run actions on components (host actions too)"""
        cluster.action(name='make_sauce').run(
            hc=tuple(
                (
                    {'host_id': host_id, 'service_id': service.id, 'component_id': component_id}
                    for host_id, component_id in (
                        (hosts[1].id, components[self.SPICE_COMPONENT].id),
                        (hosts[1].id, components[self.LEMON_COMPONENT].id),
                        (hosts[2].id, components[self.TOMATO_COMPONENT].id),
                    )
                )
            )
        ).wait()
        cluster.hostcomponent_set(
            (hosts[0], components[self.MILK_COMPONENT]),
            *[
                (cluster.host(id=hc['host_id']), service.component(id=hc['component_id']))
                for hc in cluster.hostcomponent()
            ],
        )
        _wait_for_tasks(
            (
                components[self.TOMATO_COMPONENT].action(name='add_more').run(),
                components[self.SPICE_COMPONENT].action(name='add_more').run(),
            )
        )

    def _delete_simple_cluster_with_job(self, simple_clusters: List[Cluster]) -> None:
        """Delete one of simple clusters where at least one job was ran"""
        cluster_with_job = next(
            filter(
                lambda cluster: any(len(action.task_list()) for action in cluster.action_list()),
                simple_clusters,
            ),
            None,
        )
        if cluster_with_job is None:
            raise ValueError('At least on of simple clusters should have a job')
        cluster_with_job.delete()


def _get_object_fields(adcm_object: AnyADCMObject) -> dict:
    """
    Save all common fields of an object to one big dict
    Useful for dirty upgrade
    """
    return {
        'name_or_fqdn': adcm_object.name if hasattr(adcm_object, 'name') else adcm_object.fqdn,
        'display_name': getattr(adcm_object, 'display_name', None),
        'edition': getattr(adcm_object, 'edition', None),
        'state': adcm_object.state,
        'config': get_config(adcm_object),
        # if visibility is changed, it may break
        'actions': set(action.id for action in adcm_object.action_list()),
    }


@allure.step('Wait for tasks')
def _wait_for_tasks(tasks_to_wait: Iterable[Task]):
    """Iterate over `tasks_to_wait` and wait for each to be finished (results aren't checked)"""
    for task in tasks_to_wait:
        task.wait()
