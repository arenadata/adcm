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
import coreapi
import pytest

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir
from tests.library import errorcodes as err


@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient):
    hostprovider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    provider = hostprovider_bundle.provider_create("test")
    host = provider.host_create("test_host")
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_bundle'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster.host_add(host)
    component = service.component(name="ZOOKEEPER_SERVER")
    cluster.hostcomponent_set((host, component))
    return cluster, host, service


def test_delete_host_with_components(cluster):
    """If host has NO component, than we can simple remove it from cluster.
    """
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        cluster[0].host_delete(cluster[1])
    err.HOST_CONFLICT.equal(e)


def test_delete_service_with_components(cluster):
    """If host has NO component, than we can simple remove it from cluster.
    """
    service = cluster[2]
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        service.delete()
    err.SERVICE_CONFLICT.equal(e)
