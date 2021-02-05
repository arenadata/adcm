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

import coreapi
import pytest

# pylint: disable=W0611, W0621
from adcm_pytest_plugin import utils
from tests.library.errorcodes import CONFIG_VALUE_ERROR


TEST_DATA = [("read-only-when-runned", False, True, "run", False, True),
             ("writable-when-installed", "bluhbluh", "bluhbluh", "install", False, False),
             ("writable", "bluh bluh", "bluh bluh", "", False, False),
             ('read-only-when-installed', False, True, "install", True, True),
             ('read-only-runned-integer', 500, 10, "run", True, True),
             ('read-only-int', 10, 10, "", False, False)
             ]
TEST_IDS = ["ro_when_runned", "wr_when_installed", "wr", "group-ro-installed",
            "group-ro-runned", "same-ro-values"]


@pytest.fixture()
def cluster_sdk(sdk_client_fs):
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__))
    cluster = bundle.cluster_create("test_cluster")
    return cluster


@pytest.fixture()
def cluster_config(cluster_sdk):
    return cluster_sdk.config()


@pytest.mark.parametrize(('key', 'input_value', 'expected', 'action', 'group', 'check_exception'),
                         TEST_DATA, ids=TEST_IDS)
def test_readonly_variable(key, input_value, expected, action, group, check_exception, cluster_sdk):
    current_config = cluster_sdk.config()
    if group:
        current_config['group'][key] = input_value
    else:
        current_config[key] = input_value
    if action:
        cluster_sdk.action(name=action).run().wait()
    if check_exception:
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            cluster_sdk.config_set(current_config)
        CONFIG_VALUE_ERROR.equal(e, 'config key ', 'is read only')
    else:
        cluster_sdk.config_set(current_config)
    config_after_update = cluster_sdk.config()
    if group:
        assert config_after_update['group'][key] == expected
    else:
        assert config_after_update[key] == expected
