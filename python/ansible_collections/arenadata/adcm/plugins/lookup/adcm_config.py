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

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, NamedTuple
import sys

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible_plugin.utils import cast_to_type, get_service_by_name
from cm.converters import CoreObject
from cm.legacy.api import set_object_config_with_plugin
from cm.logger import logger
from cm.models import (
    ADCM,
    Cluster,
    ConfigLog,
    Host,
    PrototypeConfig,
    Provider,
    Service,
)

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
    def run(self, terms, variables=None, **kwargs):
        logger.debug("run %s %s", terms, kwargs)

        return [call_adcm_config_lookup(terms=terms, variables=variables, kwargs=kwargs).value]


class PluginResult(NamedTuple):
    value: dict | int | str
    changed: bool


def call_adcm_config_lookup(
    terms: Sequence[Any], variables: Mapping[str, Any], kwargs: Mapping[str, Any]
) -> PluginResult:
    """
    Ansible-independent part of `adcm_config` lookup call
    """
    job_id = variables["job"]["id"]

    if len(terms) < 3:
        msg = "not enough arguments to set config ({} of 3)"
        raise AnsibleError(msg.format(len(terms)))

    conf = {terms[1]: terms[2]}

    obj = detect_target(terms=terms, variables=variables, kwargs=kwargs)

    return update_config(obj=obj, conf=conf, job_id=job_id)


def detect_target(terms: Sequence[Any], variables: Mapping[str, Any], kwargs: Mapping[str, Any]) -> ADCM | CoreObject:
    """
    Detect object which config should be changed based on lookup arguments and ansible variables
    """
    if terms[0] == "service":
        if "cluster" not in variables:
            raise AnsibleError("there is no cluster in hostvars")
        cluster = variables["cluster"]
        if "service_name" in kwargs:
            return get_service_by_name(cluster["id"], kwargs["service_name"])
        if "job" in variables and "service_id" in variables["job"]:
            return Service.obj.get(
                id=variables["job"]["service_id"], cluster__id=cluster["id"], prototype__type="service"
            )

        msg = "no service_id in job or service_name and service_version in params"
        raise AnsibleError(msg)

    if terms[0] == "cluster":
        if "cluster" not in variables:
            raise AnsibleError("there is no cluster in hostvars")
        cluster = variables["cluster"]
        return Cluster.obj.get(id=cluster["id"])

    if terms[0] == "provider":
        if "provider" not in variables:
            raise AnsibleError("there is no host provider in hostvars")
        provider = variables["provider"]
        return Provider.obj.get(id=provider["id"])

    if terms[0] == "host":
        if "adcm_hostid" not in variables:
            raise AnsibleError("there is no adcm_hostid in hostvars")
        return Host.obj.get(id=variables["adcm_hostid"])

    raise AnsibleError(f"unknown object type: {terms[0]}")


def update_config(obj: ADCM | CoreObject, conf: dict, job_id: int) -> PluginResult:
    config_log = ConfigLog.objects.get(id=obj.config.current)

    new_config = deepcopy(config_log.config)
    new_attr = deepcopy(config_log.attr) if config_log.attr is not None else {}

    changed = False

    for keys, value in conf.items():
        keys_list = keys.split("/")
        key = keys_list[0]
        subkey = None
        if len(keys_list) > 1:
            subkey = keys_list[1]

        if subkey:
            try:
                prototype_conf = PrototypeConfig.objects.get(
                    name=key, subname=subkey, prototype=obj.prototype, action=None
                )
            except PrototypeConfig.DoesNotExist as error:
                raise AnsibleError(f"Config parameter '{key}/{subkey}' does not exist") from error

            cast_value = cast_to_type(field_type=prototype_conf.type, value=value, limits=prototype_conf.limits)
            if new_config[key][subkey] != cast_value:
                new_config[key][subkey] = cast_value
                changed = True
        else:
            try:
                prototype_conf = PrototypeConfig.objects.get(name=key, subname="", prototype=obj.prototype, action=None)
            except PrototypeConfig.DoesNotExist as error:
                raise AnsibleError(f"Config parameter '{key}' does not exist") from error

            cast_value = cast_to_type(field_type=prototype_conf.type, value=value, limits=prototype_conf.limits)
            if new_config[key] != cast_value:
                new_config[key] = cast_value
                changed = True

    if not changed:
        return PluginResult(conf, False)

    # adcm_config lookup need refactor. For this use `apply_config_changes` function

    set_object_config_with_plugin(
        job_id=job_id, obj=obj, config=new_config, attr=new_attr, description="ansible update"
    )

    if len(conf) == 1:
        return PluginResult(next(iter(conf.values())), True)

    return PluginResult(conf, True)
