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
# pylint: disable=wrong-import-order,wrong-import-position

from ansible.errors import AnsibleError

from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display  # pylint: disable=unused-import
except ImportError:
    from ansible.utils.display import Display  # pylint: disable=ungrouped-imports

    display = Display()

import sys

sys.path.append("/adcm/python")
import adcm.init_django  # pylint: disable=unused-import
from cm.ansible_plugin import (
    set_cluster_state,
    set_host_state,
    set_provider_state,
    set_service_state,
    set_service_state_by_name,
)
from cm.logger import logger

DOCUMENTATION = """
    lookup: file
    author: Konstantin Voschanov <vka@arenadata.io>
    version_added: "0.1"
    short_description: update state for host, cluster or service
    description:
        - This lookup set state of specified host, cluster or service
    options:
      _terms:
        description: cluster|service|host, state
        required: True
    notes:
      - if you run service action, you don't need specify service name
"""

EXAMPLES = """
- debug: msg="set host state {{lookup('adcm_state', 'host', 'configured') }}"

- debug: msg="set cluster state {{lookup('adcm_state', 'cluster', 'done') }}"

- debug: msg="set service state {{lookup('adcm_state', 'service', 'installed') }}"

- debug: msg="set service state {{lookup('adcm_state', 'service', 'installed', service_name='ZOOKEEPER') }}"

"""

RETURN = """
  _raw:
    description:
      - new value of state
"""


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):  # pylint: disable=too-many-branches
        logger.debug("run %s %s", terms, kwargs)
        ret = []
        if len(terms) < 2:
            msg = "not enough arguments to set state ({} of 2)"
            raise AnsibleError(msg.format(len(terms)))

        if terms[0] == "service":
            if "cluster" not in variables:
                raise AnsibleError("there is no cluster in hostvars")
            cluster = variables["cluster"]
            if "service_name" in kwargs:
                res = set_service_state_by_name(cluster["id"], kwargs["service_name"], terms[1])
            elif "job" in variables and "service_id" in variables["job"]:
                res = set_service_state(cluster["id"], variables["job"]["service_id"], terms[1])
            else:
                msg = "no service_id in job or service_name in params"
                raise AnsibleError(msg)
        elif terms[0] == "cluster":
            if "cluster" not in variables:
                raise AnsibleError("there is no cluster in hostvars")
            cluster = variables["cluster"]
            res = set_cluster_state(cluster["id"], terms[1])
        elif terms[0] == "provider":
            if "provider" not in variables:
                raise AnsibleError("there is no provider in hostvars")
            provider = variables["provider"]
            res = set_provider_state(provider["id"], terms[1])
        elif terms[0] == "host":
            if "adcm_hostid" not in variables:
                raise AnsibleError("there is no adcm_hostid in hostvars")
            res = set_host_state(variables["adcm_hostid"], terms[1])
        else:
            raise AnsibleError(f"unknown object type: {terms[0]}")
        ret.append(res)
        return ret
