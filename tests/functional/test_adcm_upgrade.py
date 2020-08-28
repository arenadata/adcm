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
# pylint: disable=W0621

import allure
import pytest

from contextlib import contextmanager

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import (get_data_dir, random_string)
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.docker import DockerWrapper


@contextmanager
def adcm_client(repo, tag, volumes, pull=False):
    """
    Run ADCM container from image {repo}:{tag}. If image was pulled remove it after
    """
    with allure.step(f"Run ADCM from image {repo}:{tag}"):
        dw = DockerWrapper()
        adcm = dw.run_adcm(image=repo, tag=tag, volumes=volumes, pull=pull)
        adcm.api.auth(username='admin', password='admin')
    yield ADCMClient(api=adcm.api)
    with allure.step(f"Stop ADCM from image {repo}:{tag}"):
        adcm.container.stop()
    if pull:
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


@pytest.mark.parametrize("old_adcm",
                         parametrized_by_adcm_version(adcm_min_version="2019.01.30")[0],
                         ids=repr)
def test_upgrade_adcm(old_adcm, volume, image):
    old_repo, old_tag = old_adcm
    with adcm_client(repo=old_repo,
                     tag=old_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}},
                     pull=True) as old_adcm_client:
        bundle = old_adcm_client.upload_from_fs(get_data_dir(__file__, 'cluster_bundle'))
        cluster_name = f"test_{random_string()}"
        bundle.cluster_prototype().cluster_create(
            name=cluster_name
        )

    latest_repo, latest_tag = image
    with adcm_client(repo=latest_repo,
                     tag=latest_tag,
                     volumes={volume.name: {'bind': '/adcm/data', 'mode': 'rw'}}
                     ) as latest_adcm_client:
        assert len(latest_adcm_client.cluster_list()) == 1, "There is no clusters. Expecting one"
        cluster = latest_adcm_client.cluster_list()[0]
        assert cluster.name == cluster_name, "Unexpected cluster name"
