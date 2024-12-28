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

import sys

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from cm.models import ADCMEntity, Cluster, Host, Provider, Service
from cm.status_api import send_object_update_event

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible_plugin.utils import get_service_by_name
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
    def run(self, terms, variables=None, **kwargs):
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


def set_cluster_state(cluster_id, state):
    obj = Cluster.obj.get(id=cluster_id)
    return _set_object_state(obj, state)


def set_host_state(host_id, state):
    obj = Host.obj.get(id=host_id)
    return _set_object_state(obj, state)


def set_provider_state(provider_id, state):
    obj = Provider.obj.get(id=provider_id)
    return _set_object_state(obj, state)


def set_service_state_by_name(cluster_id, service_name, state):
    obj = get_service_by_name(cluster_id, service_name)
    return _set_object_state(obj, state)


def set_service_state(cluster_id, service_id, state):
    obj = Service.obj.get(id=service_id, cluster__id=cluster_id, prototype__type="service")
    return _set_object_state(obj, state)


def _set_object_state(obj: ADCMEntity, state: str) -> ADCMEntity:
    obj.set_state(state)
    send_object_update_event(object_=obj, changes={"state": state})
    return obj
