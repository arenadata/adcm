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

"""Tests on known ansible bugs"""

import os.path

from os import PathLike
from collections import namedtuple
from typing import Tuple, Iterable, Generator

import allure
import docker
import pytest

from docker.models.volumes import Volume
from docker.models.containers import Container
from docker.models.networks import Network
from adcm_client.objects import ADCMClient, Cluster, Provider, Host
from adcm_pytest_plugin.utils import get_data_dir, random_string, wait_until_step_succeeds
from adcm_pytest_plugin.docker_utils import ADCM
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result

from tests.functional.conftest import only_clean_adcm
from tests.functional.docker_utils import run_container, get_docker_client

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]

CENTOS_IMAGE = "hub.adsw.io/re/tent:test-centos7-x86_64"
# ALTLINUX_IMAGE = "hub.adsw.io/re/tent:test-altlinux-c8.2-x86_64"


SSH_PROVIDER_URL = 'https://downloads.arenadata.io/ADCM/infrastructure/adcm_host_ssh_v2.7-1_community.tgz'

# on child containers
INIT_FILE_NAME = 'start.sh'
INIT_FILEPATH = f'/data/{INIT_FILE_NAME}'
TMPFS_ARGUMENTS = {'/run': '', '/run/lock': ''}
VOLUME_ARGUMENTS = {'/sys/fs/cgroup': {'bind': '/sys/fs/cgroup', 'mode': 'ro'}}
ENV_ARGUMENTS = ["WAIT=yes", f"EXEC={INIT_FILEPATH}"]

INIT_SCRIPT_CENTOS = "init_centos.sh"
# INIT_SCRIPT_ALTLINUX = "init_alt.sh"
INSTALL_FINISHED_MARK = "SSH is ready to be used by test!"

# Run containers parametrization

FQDN_PREFIXES_DELEGATE_TO = ('good-container', 'bad-container')
FQDN_PREFIXES_APT_RPM = ('install-as-list', 'install-as-string')

CENTOS_IMAGE_AND_SCRIPT = (CENTOS_IMAGE, INIT_SCRIPT_CENTOS)
# ALT_IMAGE_AND_SCRIPT = (ALTLINUX_IMAGE, INIT_SCRIPT_ALTLINUX)

RunContainersParam = namedtuple('RunContainersParam', ('image', 'init_script', 'fqdn_prefixes'))
CENTOS_TWO_CLUSTERS = RunContainersParam(*CENTOS_IMAGE_AND_SCRIPT, FQDN_PREFIXES_DELEGATE_TO)
# ALTLINUX_TWO_CLUSTERS = RunContainersParam(*ALT_IMAGE_AND_SCRIPT, FQDN_PREFIXES_DELEGATE_TO)


# !===== General Helpers =====!


def get_path_to_init_file(file: str) -> str:
    """Get full path to init script file by it's name"""
    return os.path.join(get_data_dir(__file__), file)


def get_container_logs(container: Container) -> str:
    """Get logs from docker container as string"""
    return str(container.logs(), encoding='utf-8')


def get_container_hostname(container: Container) -> str:
    """Get hostname from container as string"""
    return str(container.exec_run('hostname').output, encoding='utf-8').strip()


# !===== Fixtures =====!


@pytest.fixture()
def ssh_provider(sdk_client_fs: ADCMClient) -> Provider:
    """Get "prod-like" SSH provider"""
    bundle = sdk_client_fs.upload_from_url(SSH_PROVIDER_URL)
    return bundle.provider_create(name='SSH provider')


@pytest.fixture()
def cluster_delegate_to(sdk_client_fs: ADCMClient) -> Cluster:
    """Cluster to catch the ADCM-683 bug (delegate_to with ansible_host == null)"""
    bundle = sdk_client_fs.upload_from_fs(os.path.join(get_data_dir(__file__), 'cluster_adcm_683'))
    return bundle.cluster_create(name='test_cluster')


@pytest.fixture()
def cluster_apt_rpm(sdk_client_fs: ADCMClient) -> Cluster:
    """Cluster to test apt_rpm bug (argument is list)"""
    bundle = sdk_client_fs.upload_from_fs(os.path.join(get_data_dir(__file__), 'cluster_apt_rpm'))
    return bundle.cluster_create(name='test_cluster')


@pytest.fixture()
def custom_volume() -> Generator[Volume, None, None]:
    """Create custom docker volume"""

    def _volume_mounted_to_container(name: str, container_to_check: Container) -> bool:
        return any(
            (
                name == mount.get('name', None) and mount.get('type', None) == 'volume'
                for mount in container_to_check.attrs['Mounts']
            )
        )

    volume_name = f'init-script-{random_string(6)}'
    docker_client = get_docker_client()
    volume = docker_client.volumes.create(name=volume_name)
    yield volume
    volume.reload()
    for container in (
        cont for cont in docker_client.containers.list() if _volume_mounted_to_container(volume_name, cont)
    ):
        container: Container
        container.remove()
        container.wait(condition='removed')
    volume.remove()


@pytest.fixture(
    # params=[CENTOS_TWO_CLUSTERS, ALTLINUX_TWO_CLUSTERS], ids=["centos_two_containers", "altlinux_two_containers"]
    params=[CENTOS_TWO_CLUSTERS], ids=["centos_two_containers"]
)
def run_containers(request, custom_volume: Volume) -> Generator[Tuple[Container, ...], None, None]:
    """Run docker containers and stop them afterwards"""
    param: RunContainersParam = request.param
    data_volume = prepare_volume_with_init_script(param.image, get_path_to_init_file(param.init_script), custom_volume)
    arguments = {
        'volumes': {data_volume.name: {'bind': '/data', 'mode': 'rw'}, **VOLUME_ARGUMENTS},
        'tmpfs': TMPFS_ARGUMENTS,
        'environment': ENV_ARGUMENTS,
    }
    with allure.step(f'Run containers from image "{param.image}": {" ".join(param.fqdn_prefixes)}'):
        containers = []
        for name in param.fqdn_prefixes:
            container = run_container(param.image, name=f'{name}-{random_string(3)}', **arguments)
            containers.append(container)
            # The original idea was to wait in test body right before SSH access is required.
            # But on CI this approach failed with some problem with packages install.
            wait_init_script_finished(container)

    yield tuple(containers)

    with allure.step(f'Stop containers from image "{param.image}'):
        if request.node.rep_setup.passed and request.node.rep_call.failed:
            _attach_containers_info(containers)
        for container in containers:
            container.stop()
            container.wait(condition='removed')


@pytest.fixture()
def custom_network(
    adcm_fs: ADCM, run_containers: Tuple[Container, ...]  # pylint: disable=unused-argument
) -> Generator[Network, None, None]:
    """Create docker network"""
    network_name = f'network-{random_string(6)}'
    with allure.step(f'Create custom network {network_name}'):
        docker_client: docker.DockerClient = adcm_fs.container.client
        network = docker_client.networks.create(network_name)
    yield network
    network.reload()
    with allure.step(f'Disconnect containers from network {network}'):
        for container in network.containers:
            network.disconnect(container.name)
    network.remove()


# !===== Steps =====!


@allure.step('Prepare volume with init script')
def prepare_volume_with_init_script(image: str, script: PathLike, volume: Volume) -> Volume:
    """Run container that will add init script to volume"""
    with open(script, mode='r', encoding='utf-8') as script_file:
        file_content = script_file.read()
    container = run_container(
        image,
        volumes={volume.name: {'bind': '/data', 'mode': 'rw'}},
        command=[
            'bash',
            '-c',
            f'echo "{file_content}" > {INIT_FILEPATH} && chmod +x {INIT_FILEPATH}',
        ],
    )
    container.wait()
    return volume


def connect_containers_to_network(network: Network, *other_containers) -> None:
    """Connect containers to given network"""
    with allure.step(f'Connect containers to network {network.name}'):
        for container in other_containers:
            network.connect(container.name)
    network.reload()


@allure.step('Wait until containers are initialized with init script')
def wait_init_script_finished(*containers: Iterable[Container]) -> None:
    """Check logs for message at the end of exec script"""

    def _containers_are_initialized():
        for container in containers:
            assert INSTALL_FINISHED_MARK in get_container_logs(
                container
            ), f'Container failed to initialize: {INSTALL_FINISHED_MARK} not in logs of container {container.name}'

    try:
        wait_until_step_succeeds(_containers_are_initialized, timeout=90, period=10)
    except AssertionError as e:
        _attach_containers_info(containers)
        raise TimeoutError('Containers failed to initialize, see logs for details') from e


@allure.step('Create hosts: {host_fqdns} and add them to cluster {cluster}')
def create_hosts_and_add_to_cluster(
    cluster: Cluster, provider: Provider, host_fqdns: Iterable[str]
) -> Tuple[Host, ...]:
    """Create hosts with given FQDNs and add them to cluster"""
    return tuple((cluster.host_add(provider.host_create(fqdn)) for fqdn in host_fqdns))


# !===== Tests =====!

# pylint: disable=too-many-arguments
@allure.link(url='https://arenadata.atlassian.net/browse/ADCM-683')
def test_delegate_to_directive(
    adcm_fs: ADCM,
    custom_network: Network,
    cluster_delegate_to: Cluster,
    run_containers: Tuple[Container, Container],
    ssh_provider: Provider,
    action_name: str = 'delegate',
):
    """
    Test that ansible version used in ADCM doesn't have known bug
        with delegate_to directive and ansible_host=null
    """
    ansible_credentials = {'ansible_user': 'root', 'ansible_ssh_pass': 'root'}
    good_container, bad_container = run_containers
    good_host_fqdn, bad_host_fqdn = good_container.name, bad_container.name

    connect_containers_to_network(custom_network, adcm_fs.container, good_container, bad_container)
    good_host, bad_host = create_hosts_and_add_to_cluster(
        cluster_delegate_to, ssh_provider, (good_host_fqdn, bad_host_fqdn)
    )

    with allure.step(f'Set "ansible_host" in one host to {good_host_fqdn} and in another to None'):
        good_host.config_set_diff({'ansible_host': good_host_fqdn, **ansible_credentials})
        bad_host.config_set_diff({'ansible_host': None, **ansible_credentials})
    with allure.step(f'Run {action_name} on cluster and check result'):
        task = run_cluster_action_and_assert_result(
            cluster_delegate_to,
            action_name,
            config={'good_fqdn': good_container.name, 'bad_fqdn': bad_container.name},
        )
    _check_hostnames(task, good_container, bad_container)


@pytest.mark.parametrize(
    'run_containers',
    [
        RunContainersParam(*CENTOS_IMAGE_AND_SCRIPT, FQDN_PREFIXES_APT_RPM),
        # RunContainersParam(*ALT_IMAGE_AND_SCRIPT, FQDN_PREFIXES_APT_RPM),
    ],
    indirect=True,
    ids=['centos_two_containers'],
    # ids=['centos_two_containers', 'altlinux_two_containers'],
)
@allure.link(url='https://arenadata.atlassian.net/browse/ADCM-1229')
def test_apt_rpm_list_argument(
    adcm_fs: ADCM,
    custom_network: Network,
    run_containers: Tuple[Container, Container],
    ssh_provider: Provider,
    cluster_apt_rpm: Cluster,
    packages_to_install=('libaio', 'neovim'),
):
    """
    Test that ansible version used in ADCM doesn't have known bug
        with passing "list" type argument to apt_rpm
    """
    ansible_credentials = {'ansible_user': 'root', 'ansible_ssh_pass': 'root'}
    container_list_argument, container_string_argument = run_containers
    cluster = cluster_apt_rpm

    connect_containers_to_network(custom_network, adcm_fs.container, container_list_argument, container_string_argument)
    _check_packages_are_not_installed(packages_to_install, container_list_argument, container_string_argument)
    list_install_host, string_install_host = create_hosts_and_add_to_cluster(
        cluster, ssh_provider, (container_list_argument.name, container_string_argument.name)
    )
    with allure.step('Configure ansible access on hosts'):
        list_install_host.config_set_diff(ansible_credentials)
        string_install_host.config_set_diff(ansible_credentials)

    with allure.step('Install packages with list argument'):
        run_cluster_action_and_assert_result(cluster, 'install_as_list', config={'host': list_install_host.fqdn})
        _check_packages_are_installed(packages_to_install, container_list_argument)
    with allure.step('Install packages with string argument'):
        run_cluster_action_and_assert_result(cluster, 'install_as_string', config={'host': string_install_host.fqdn})
        _check_packages_are_installed(packages_to_install, container_string_argument)


# !===== Specific Steps and Helpers =====!


@allure.step('Check hostnames in log to assure delegate_to worked correctly')
def _check_hostnames(task, good_container, bad_container):
    """Check that hostnames are wrote to log correctly"""
    expected_hostnames = {
        container.name: get_container_hostname(container) for container in (good_container, bad_container)
    }
    log_content = task.job().log(type='stdout').content
    allure.attach(log_content, name='Log of "delegate" action', attachment_type=allure.attachment_type.TEXT)
    for fqdn, hostname in expected_hostnames.items():
        expected_line = f'{fqdn}-hostname: {hostname}'
        with allure.step(f'Expect {expected_line} to be in log'):
            assert expected_line in log_content, f'Hostname of host {fqdn} should be {hostname}'


def _attach_containers_info(containers: Iterable[Container]) -> None:
    """Attach logs, hostnames from containers"""
    for container in containers:
        allure.attach(
            get_container_logs(container),
            name=f'Logs from container with id {container.short_id} and name {container.name}',
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            get_container_hostname(container),
            name=f'Hostname of {container.name}',
            attachment_type=allure.attachment_type.TEXT,
        )


def _check_packages_are_installed(packages: Iterable[str], *containers: Iterable[Container]) -> None:
    """Check that packages are installed in containers"""
    for package in packages:
        for container in containers:
            with allure.step(f"Check that package {package} is installed in container {container.name}"):
                assert _package_is_installed(
                    package, container
                ), f"Package {package} should be installed in container {container.name}"


@allure.step("Check that packages aren't installed in containers")
def _check_packages_are_not_installed(packages: Iterable[str], *containers: Iterable[Container]) -> None:
    """Check that packages aren't installed in containers"""
    for package in packages:
        for container in containers:
            with allure.step(f"Check that package {package} is not installed in container {container.name}"):
                assert not _package_is_installed(
                    package, container
                ), f"Package {package} shouldn't be installed in container {container.name}"


def _package_is_installed(package: str, container: Container) -> bool:
    """Check if package is installed on container"""
    message = container.exec_run(f'rpm -q {package}').output.decode('utf-8').strip()
    return message != f'package {package} is not installed'
