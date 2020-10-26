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
# pylint: disable=W0621,R0914

import allure
import pytest

from contextlib import contextmanager
from docker.errors import NotFound

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import (get_data_dir, random_string, get_initialized_adcm_image)
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.docker import DockerWrapper


def old_adcm_images():
    # TODO Change oldest version after https://arenadata.atlassian.net/browse/ADCM-1430
    # return parametrized_by_adcm_version(adcm_min_version="2019.01.30")[0]
    return parametrized_by_adcm_version(adcm_min_version="2019.03.18")[0]


@contextmanager
def adcm_client(adcm_repo, adcm_credentials, adcm_tag, volumes, init=False):
    """
    Run ADCM container from image {adcm_repo}:{adcm_tag}.
    If init=True new initialised image will be generated.
    If we use 'image' fixture we don't need to initialize it one more time.
    """
    if init:
        with allure.step(f"Create isolated image copy from {adcm_repo}:{adcm_tag}"):
            new_image = get_initialized_adcm_image(adcm_repo=adcm_repo,
                                                   adcm_tag=adcm_tag,
                                                   pull=True)
            repo, tag = new_image["repo"], new_image["tag"]
    else:
        repo, tag = adcm_repo, adcm_tag
    with allure.step(f"Run ADCM from image {repo}:{tag}"):
        dw = DockerWrapper()
        adcm = dw.run_adcm(image=repo, tag=tag, volumes=volumes, pull=False)
        adcm.api.auth(**adcm_credentials)
    yield ADCMClient(api=adcm.api)
    with allure.step(f"Stop ADCM from image {repo}:{tag}"):
        adcm.container.kill()
        try:
            adcm.container.wait(condition="removed", timeout=30)
        except (ConnectionError, NotFound):
            # https://github.com/docker/docker-py/issues/1966 workaround
            pass
    if init:
        with allure.step(f"Remove ADCM image {repo}:{tag}"):
            dw.client.images.remove(f'{repo}:{tag}', force=True)


@pytest.fixture(scope='function')
def volume(request):
    """
    Create Docker volume and remove it after test
    """
    dw = DockerWrapper()
    with allure.step("Create docker volume"):
        vol = dw.client.volumes.create()

    @allure.step("Remove docker volume")
    def fin():
        vol.remove(force=True)

    request.addfinalizer(fin)

    return vol


@pytest.mark.parametrize("old_adcm", old_adcm_images(), ids=repr)
def test_upgrade_adcm(old_adcm, volume, image, adcm_credentials):
    old_repo, old_tag = old_adcm
    with adcm_client(adcm_repo=old_repo,
                     adcm_credentials=adcm_credentials,
                     adcm_tag=old_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}},
                     init=True) as old_adcm_client:
        bundle = old_adcm_client.upload_from_fs(get_data_dir(__file__, 'cluster_bundle'))
        cluster_name = f"test_{random_string()}"
        bundle.cluster_prototype().cluster_create(
            name=cluster_name
        )

    latest_repo, latest_tag = image
    with adcm_client(adcm_repo=latest_repo,
                     adcm_credentials=adcm_credentials,
                     adcm_tag=latest_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}}
                     ) as latest_adcm_client:
        assert len(latest_adcm_client.cluster_list()) == 1, "There is no clusters. Expecting one"
        cluster = latest_adcm_client.cluster_list()[0]
        assert cluster.name == cluster_name, "Unexpected cluster name"


@pytest.mark.parametrize("old_adcm", old_adcm_images(), ids=repr)
def test_pass_in_cluster_config_encryption_after_upgrade(old_adcm, volume, image, adcm_credentials):
    old_repo, old_tag = old_adcm
    with adcm_client(adcm_repo=old_repo,
                     adcm_credentials=adcm_credentials,
                     adcm_tag=old_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}},
                     init=True) as old_adcm_client:
        hostprovider_bundle = old_adcm_client.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
        hostprovider = hostprovider_bundle.provider_create(
            name=f"test_{random_string()}"
        )
        host = hostprovider.host_create(fqdn=f"test_host_{random_string()}")

        cluster_bundle = old_adcm_client.upload_from_fs(
            get_data_dir(__file__, 'cluster_with_cluster_pass_verify'))
        cluster = cluster_bundle.cluster_prototype().cluster_create(
            name=f"test_{random_string()}"
        )

        cluster.host_add(host)

        cluster_config = cluster.config()
        cluster_config["password"] = "q1w2e3r4"
        cluster.config_set(cluster_config)

    latest_repo, latest_tag = image
    with adcm_client(adcm_repo=latest_repo,
                     adcm_credentials=adcm_credentials,
                     adcm_tag=latest_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}}
                     ) as latest_adcm_client:
        assert len(latest_adcm_client.cluster_list()) == 1, "There is no clusters. Expecting one"
        cluster = latest_adcm_client.cluster_list()[0]
        assert cluster.action(name="check-password").run().wait() == "success"


@pytest.mark.parametrize("old_adcm", old_adcm_images(), ids=repr)
def test_pass_in_service_config_encryption_after_upgrade(old_adcm, volume, image, adcm_credentials):
    old_repo, old_tag = old_adcm
    with adcm_client(adcm_repo=old_repo,
                     adcm_credentials=adcm_credentials,
                     adcm_tag=old_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}},
                     init=True) as old_adcm_client:
        hostprovider_bundle = old_adcm_client.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
        hostprovider = hostprovider_bundle.provider_create(
            name=f"test_{random_string()}"
        )
        host = hostprovider.host_create(fqdn=f"test_host_{random_string()}")

        cluster_bundle = old_adcm_client.upload_from_fs(
            get_data_dir(__file__, 'cluster_with_service_pass_verify'))
        cluster = cluster_bundle.cluster_prototype().cluster_create(
            name=f"test_{random_string()}"
        )

        cluster.host_add(host)

        service = cluster.service_add(name="PassChecker")
        service_config = service.config()
        service_config["password"] = "q1w2e3r4"
        service.config_set(service_config)

    latest_repo, latest_tag = image
    with adcm_client(adcm_repo=latest_repo,
                     adcm_credentials=adcm_credentials,
                     adcm_tag=latest_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}}
                     ) as latest_adcm_client:
        assert len(latest_adcm_client.cluster_list()) == 1, "There is no clusters. Expecting one"
        cluster = latest_adcm_client.cluster_list()[0]
        assert len(cluster.service_list()) == 1, "There is no services. Expecting one"
        service = cluster.service_list()[0]
        assert service.action(name="check-password").run().wait() == "success"
