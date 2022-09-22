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

"""Tests for host deletion"""

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir


def test_delete_host(sdk_client_fs: ADCMClient):
    """If host has NO component, than we can simple remove it from cluster."""
    hostprovider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    provider = hostprovider_bundle.provider_create("test")
    host = provider.host_create("test-host")
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_bundle'))
    cluster = bundle.cluster_create("test")
    cluster.service_add(name="zookeeper")
    cluster.host_add(host)
    cluster.host_delete(host)
