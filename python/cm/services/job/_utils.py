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

from typing import Any, Hashable

from cm.errors import AdcmEx
from cm.models import Action, Cluster, Component, Host, HostComponent, Service
from cm.services.job.types import HcAclAction


def get_old_hc(saved_hostcomponent: list[dict]):
    if not saved_hostcomponent:
        return {}

    old_hostcomponent = {}
    for hostcomponent in saved_hostcomponent:
        service = Service.objects.get(id=hostcomponent["service_id"])
        comp = Component.objects.get(id=hostcomponent["component_id"])
        host = Host.objects.get(id=hostcomponent["host_id"])
        key = _cook_comp_key(service.prototype.name, comp.prototype.name)
        _add_to_dict(old_hostcomponent, key, host.fqdn, host)

    return old_hostcomponent


def cook_delta(
    cluster: Cluster,
    new_hc: list[tuple[Service, Host, Component]],
    action_hc: list[dict],
    old: dict = None,
) -> dict:
    def add_delta(_delta, action, _key, fqdn, _host):
        _service, _comp = _key.split(".")
        if not _check_action_hc(action_hc, _service, _comp, action):
            msg = (
                f'no permission to "{action}" component "{_comp}" of ' f'service "{_service}" to/from hostcomponentmap'
            )
            raise AdcmEx(code="WRONG_ACTION_HC", msg=msg)

        _add_to_dict(_delta[action], _key, fqdn, _host)

    new = {}
    for service, host, comp in new_hc:
        key = _cook_comp_key(service.prototype.name, comp.prototype.name)
        _add_to_dict(new, key, host.fqdn, host)

    if old is None:
        old = {}
        for hostcomponent in HostComponent.objects.filter(cluster=cluster):
            key = _cook_comp_key(hostcomponent.service.prototype.name, hostcomponent.component.prototype.name)
            _add_to_dict(old, key, hostcomponent.host.fqdn, hostcomponent.host)

    delta = {HcAclAction.ADD.value: {}, HcAclAction.REMOVE.value: {}}
    for key, value in new.items():
        if key in old:
            for host in value:
                if host not in old[key]:
                    add_delta(_delta=delta, action=HcAclAction.ADD.value, _key=key, fqdn=host, _host=value[host])

            for host in old[key]:
                if host not in value:
                    add_delta(_delta=delta, action=HcAclAction.REMOVE.value, _key=key, fqdn=host, _host=old[key][host])
        else:
            for host in value:
                add_delta(_delta=delta, action=HcAclAction.ADD.value, _key=key, fqdn=host, _host=value[host])

    for key, value in old.items():
        if key not in new:
            for host in value:
                add_delta(_delta=delta, action=HcAclAction.REMOVE.value, _key=key, fqdn=host, _host=value[host])

    return delta


def _add_to_dict(my_dict: dict, key: Hashable, subkey: Hashable, value: Any) -> None:
    if key not in my_dict:
        my_dict[key] = {}

    my_dict[key][subkey] = value


def _cook_comp_key(name, subname):
    return f"{name}.{subname}"


def _check_action_hc(
    action_hc: list[dict],
    service: Service,
    component: Component,
    action: Action,
) -> bool:
    for item in action_hc:
        if item["service"] == service and item["component"] == component and item["action"] == action:
            return True

    return False
