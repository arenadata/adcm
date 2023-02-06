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

# pylint: disable=wrong-import-position, import-error

import sys

from ansible.errors import AnsibleError

from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display  # pylint: disable=unused-import
except ImportError:
    from ansible.utils.display import Display  # pylint: disable=ungrouped-imports

    display = Display()

sys.path.append("/adcm/python")
import adcm.init_django  # pylint: disable=unused-import
from cm.ansible_plugin import (
    set_cluster_config,
    set_host_config,
    set_provider_config,
    set_service_config,
    set_service_config_by_name,
)
from cm.logger import logger

DOCUMENTATION = """
    lookup: file
    author: Konstantin Voschanov <vka@arenadata.io>
    version_added: "0.1"
    short_description: set config key for host, cluster or service
    description:
        - This lookup set value of specified config key/subkey for host, cluster or service
    options:
      _terms:
        description: cluster|service|host, 'key/subkey', value
        required: True
    notes:
      - if you run service action, you don't need specify service name
"""

EXAMPLES = """
- debug: msg="set host config {{lookup('adcm_config', 'host', 'ssh-key', 'F25') }}"

- debug: msg="set cluster config {{lookup('adcm_config', 'cluster', 'adh.cfg/port', 80) }}"

- debug: msg="set service config {{lookup('adcm_config', 'service', 'adh.cfg/port', 80) }}"

- debug: msg="set service config {{lookup('adcm_config', 'service', 'adh.cfg/port', 80, service_name='ZOOKEEPER') }}"

"""

RETURN = """
  _raw:
    description:
      - new value of config
"""


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):  # pylint: disable=too-many-branches
        logger.debug("run %s %s", terms, kwargs)
        ret = []

        if len(terms) < 3:
            msg = "not enough arguments to set config ({} of 3)"
            raise AnsibleError(msg.format(len(terms)))

        conf = {terms[1]: terms[2]}

        if terms[0] == "service":
            if "cluster" not in variables:
                raise AnsibleError("there is no cluster in hostvars")
            cluster = variables["cluster"]
            if "service_name" in kwargs:
                res = set_service_config_by_name(cluster["id"], kwargs["service_name"], conf)
            elif "job" in variables and "service_id" in variables["job"]:
                res = set_service_config(cluster["id"], variables["job"]["service_id"], conf)
            else:
                msg = "no service_id in job or service_name and service_version in params"
                raise AnsibleError(msg)
        elif terms[0] == "cluster":
            if "cluster" not in variables:
                raise AnsibleError("there is no cluster in hostvars")
            cluster = variables["cluster"]
            res = set_cluster_config(cluster["id"], conf)
        elif terms[0] == "provider":
            if "provider" not in variables:
                raise AnsibleError("there is no host provider in hostvars")
            provider = variables["provider"]
            res = set_provider_config(provider["id"], conf)
        elif terms[0] == "host":
            if "adcm_hostid" not in variables:
                raise AnsibleError("there is no adcm_hostid in hostvars")
            res = set_host_config(variables["adcm_hostid"], conf)
        else:
            raise AnsibleError(f"unknown object type: {terms[0]}")

        ret.append(res)
        return ret
