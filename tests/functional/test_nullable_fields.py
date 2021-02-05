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

# Created by a1wen at 30.01.19

import shutil
from tempfile import mkdtemp

import allure
import coreapi
import pytest
import yaml
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils
from jinja2 import Template

# pylint: disable=W0611, W0621
from tests.library import errorcodes as err

DATADIR = utils.get_data_dir(__file__)
TEMPLATE = DATADIR + '/template.yaml'


def read_conf(template_file_name):
    try:
        with open(template_file_name) as file:
            data = file.read()
    except FileNotFoundError:
        print("Can't open template file: '{}'".format(template_file_name))
    return data


def render(template, context):
    tmpl = Template(template)
    return yaml.load(tmpl.render(config_type=context))


def save_conf(rendered_template, out_dir, out_file_name='/config.yaml'):
    with open(out_dir + out_file_name, 'w') as out:
        out.write(yaml.dump(rendered_template, default_flow_style=False))


types_list = ['integer', 'float', 'string', 'boolean', 'password', 'text', 'json', 'file']
# , 'float', 'string', 'boolean', 'password', 'text', 'json', 'file', option need refactor


@pytest.fixture(params=types_list)
def data(sdk_client_ms: ADCMClient, request):
    out_dir = mkdtemp()
    conf = read_conf(TEMPLATE)
    save_conf(render(conf, request.param), out_dir)
    bundle = sdk_client_ms.upload_from_fs(out_dir)
    cluster = bundle.cluster_create(name=request.param)
    yield cluster, request.param
    shutil.rmtree(out_dir)


def test_null_value_shouldnt_be_for_required(data, val=None):
    cluster, case = data
    conf = {"required": val, "following": val}
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        cluster.config_set(conf)
    with allure.step('Check error in case ' + case):
        err.CONFIG_VALUE_ERROR.equal(e, 'Value of config key "required/" is required')
