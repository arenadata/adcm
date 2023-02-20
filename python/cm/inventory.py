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

import json
from itertools import chain

from cm.adcm_config import get_prototype_config, process_config
from cm.logger import logger
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostComponent,
    HostProvider,
    MaintenanceMode,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
    get_object_cluster,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

MAINTENANCE_MODE = "maintenance_mode"


def process_config_and_attr(obj: ADCMEntity, conf: dict, attr: dict | None = None, spec: dict | None = None):
    if not spec:
        if isinstance(obj, GroupConfig):
            prototype = obj.object.prototype
        else:
            prototype = obj.prototype

        spec, _, _, _ = get_prototype_config(proto=prototype)

    new_config = process_config(obj=obj, spec=spec, old_conf=conf)

    if attr:
        for key, value in attr.items():
            if "active" in value and not value["active"]:
                new_config[key] = None

    return new_config


def get_prototype_imports(obj: Cluster | ClusterObject, imports: dict) -> dict:
    for imp in PrototypeImport.objects.filter(prototype=obj.prototype):
        if not imp.default:
            continue

        if imp.multibind:
            imports[imp.name] = []
        else:
            imports[imp.name] = {}

        for group in imp.default:
            config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
            conf = process_config_and_attr(obj=obj, conf=config_log.config, attr=config_log.attr)
            if imp.multibind:
                imports[imp.name].append({group: conf[group]})
            else:
                imports[imp.name][group] = conf[group]

    return imports


def get_import(cluster: Cluster) -> dict:  # pylint: disable=too-many-branches
    imports = {}
    for obj in chain([cluster], ClusterObject.objects.filter(cluster=cluster)):
        imports = get_prototype_imports(obj=obj, imports=imports)

    first = True
    for bind in ClusterBind.objects.filter(cluster=cluster):
        if bind.source_service:
            obj = bind.source_service
        else:
            obj = bind.source_cluster

        conf_ref = obj.config
        export_proto = obj.prototype
        config_log = ConfigLog.objects.get(obj_ref=conf_ref, id=conf_ref.current)
        conf = process_config_and_attr(obj=obj, conf=config_log.config, attr=config_log.attr)

        if bind.service:
            proto = bind.service.prototype
        else:
            proto = bind.cluster.prototype

        actual_import = PrototypeImport.objects.get(prototype=proto, name=obj.prototype.name)

        if actual_import.multibind:
            if export_proto.name not in imports:
                imports[export_proto.name] = []
            elif actual_import.default and first:
                imports[export_proto.name] = []
                first = False
        else:
            imports[export_proto.name] = {}

        for export in PrototypeExport.objects.filter(prototype=export_proto):
            if actual_import.multibind:
                imports[export_proto.name].append({export.name: conf[export.name]})
            else:
                imports[export_proto.name][export.name] = conf[export.name]

    return imports


def get_obj_config(obj) -> dict:
    if obj.config is None:
        return {}

    config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)

    return process_config_and_attr(obj=obj, conf=config_log.config, attr=config_log.attr)


def get_cluster_variables(cluster: Cluster, cluster_config: dict = None) -> dict:
    result = {
        "config": cluster_config or get_obj_config(cluster),
        "name": cluster.name,
        "id": cluster.id,
        "version": cluster.prototype.version,
        "edition": cluster.prototype.bundle.edition,
        "state": cluster.state,
        "multi_state": cluster.multi_state,
        "before_upgrade": cluster.before_upgrade,
    }

    imports = get_import(cluster=cluster)
    if imports:
        result["imports"] = imports

    return result


def get_service_variables(service: ClusterObject, service_config: dict = None) -> dict:
    return {
        "id": service.id,
        "version": service.prototype.version,
        "state": service.state,
        "multi_state": service.multi_state,
        "config": service_config or get_obj_config(service),
        MAINTENANCE_MODE: service.maintenance_mode == MaintenanceMode.ON,
        "display_name": service.display_name,
    }


def get_component_variables(component: ServiceComponent, component_config: dict = None) -> dict:
    return {
        "component_id": component.id,
        "config": component_config or get_obj_config(component),
        "state": component.state,
        "multi_state": component.multi_state,
        MAINTENANCE_MODE: component.maintenance_mode == MaintenanceMode.ON,
        "display_name": component.display_name,
    }


def get_provider_variables(provider: HostProvider, provider_config: dict = None) -> dict:
    host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type="host")
    return {
        "config": provider_config or get_obj_config(provider),
        "name": provider.name,
        "id": provider.id,
        "host_prototype_id": host_proto.id,
        "state": provider.state,
        "multi_state": provider.multi_state,
        "before_upgrade": provider.before_upgrade,
    }


def get_group_config(obj: ADCMEntity, host: Host) -> dict | None:
    group = host.group_config.filter(object_id=obj.id, object_type=ContentType.objects.get_for_model(obj)).last()
    group_config = None
    if group:
        conf, attr = group.get_config_and_attr()
        group_config = process_config_and_attr(group, conf, attr)
    return group_config


def get_host_vars(host: Host, obj: ADCMEntity) -> dict:
    variables = {}
    if not host.group_config.all().exists():
        return variables

    if isinstance(obj, Cluster):
        variables.update({"cluster": get_cluster_variables(obj, cluster_config=get_group_config(obj, host))})
        variables.update({"services": {}})
        for service in ClusterObject.objects.filter(cluster=obj):
            variables["services"][service.prototype.name] = get_service_variables(
                service=service, service_config=get_group_config(obj=service, host=host)
            )
            for component in ServiceComponent.objects.filter(cluster=obj, service=service):
                variables["services"][service.prototype.name][component.prototype.name] = get_component_variables(
                    component=component, component_config=get_group_config(obj=component, host=host)
                )

    elif isinstance(obj, (ClusterObject, ServiceComponent)):
        variables.update({"services": {}})

        for service in ClusterObject.objects.filter(cluster=obj.cluster):
            variables["services"][service.prototype.name] = get_service_variables(
                service=service, service_config=get_group_config(obj=service, host=host)
            )
            for component in ServiceComponent.objects.filter(cluster=obj.cluster, service=service):
                variables["services"][service.prototype.name][component.prototype.name] = get_component_variables(
                    component=component, component_config=get_group_config(obj=component, host=host)
                )

    else:  # HostProvider
        variables.update(
            {"provider": get_provider_variables(provider=obj, provider_config=get_group_config(obj=obj, host=host))}
        )

    return variables


def get_cluster_config(cluster) -> dict:
    result = {
        "cluster": get_cluster_variables(cluster),
        "services": {},
    }

    for service in ClusterObject.objects.filter(cluster=cluster):
        result["services"][service.prototype.name] = get_service_variables(service)
        for component in ServiceComponent.objects.filter(cluster=cluster, service=service):
            result["services"][service.prototype.name][component.prototype.name] = get_component_variables(component)

    return result


def get_provider_config(provider_id) -> dict:
    provider = HostProvider.objects.get(id=provider_id)
    return {"provider": get_provider_variables(provider)}


def get_host_groups(cluster: Cluster, delta: dict | None = None, action_host: Host | None = None) -> dict:
    if delta is None:
        delta = {}

    groups = {}
    host_components = HostComponent.objects.filter(cluster=cluster)
    for hostcomponent in host_components:
        if action_host and hostcomponent.host.id not in action_host:
            continue

        key_object_pairs = (
            (
                f"{hostcomponent.service.prototype.name}.{hostcomponent.component.prototype.name}",
                hostcomponent.component,
            ),
            (f"{hostcomponent.service.prototype.name}", hostcomponent.service),
        )

        for key, adcm_object in key_object_pairs:
            if hostcomponent.host.maintenance_mode == MaintenanceMode.ON:
                key = f"{key}.{MAINTENANCE_MODE}"

            if key not in groups:
                groups[key] = {"hosts": {}}

            groups[key]["hosts"][hostcomponent.host.fqdn] = get_obj_config(hostcomponent.host)
            groups[key]["hosts"][hostcomponent.host.fqdn].update(get_host_vars(hostcomponent.host, adcm_object))

    for htype in delta:
        for key in delta[htype]:
            lkey = f"{key}.{htype}"
            if lkey not in groups:
                groups[lkey] = {"hosts": {}}

            for fqdn in delta[htype][key]:
                host = delta[htype][key][fqdn]
                if host.maintenance_mode != MaintenanceMode.ON:
                    groups[lkey]["hosts"][host.fqdn] = get_obj_config(host)

    return groups


def get_hosts(host_list, obj, action_host=None):
    group = {}
    for host in host_list:
        if host.maintenance_mode == MaintenanceMode.ON or (action_host and host.id not in action_host):
            continue
        group[host.fqdn] = get_obj_config(host)
        group[host.fqdn]["adcm_hostid"] = host.id
        group[host.fqdn]["state"] = host.state
        group[host.fqdn]["multi_state"] = host.multi_state
        if not isinstance(obj, Host):
            group[host.fqdn].update(get_host_vars(host, obj))
    return group


def get_cluster_hosts(cluster, action_host=None):
    return {
        "CLUSTER": {
            "hosts": get_hosts(Host.objects.filter(cluster=cluster), cluster, action_host),
            "vars": get_cluster_config(cluster),
        }
    }


def get_provider_hosts(provider, action_host=None):
    return {
        "PROVIDER": {
            "hosts": get_hosts(Host.objects.filter(provider=provider), provider, action_host),
        }
    }


def get_host(host_id):
    host = Host.objects.get(id=host_id)
    groups = {"HOST": {"hosts": get_hosts([host], host), "vars": get_provider_config(host.provider.id)}}
    return groups


def get_target_host(host_id):
    host = Host.objects.get(id=host_id)
    groups = {"target": {"hosts": get_hosts([host], host), "vars": get_cluster_config(host.cluster)}}
    return groups


def get_inventory_data(
    obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    action: Action,
    action_host: list[Host] | None = None,
    delta: dict | None = None,
) -> dict:
    if delta is None:
        delta = {}

    inventory_data = {"all": {"children": {}}}
    cluster = get_object_cluster(obj)

    if cluster:
        inventory_data["all"]["children"].update(get_cluster_hosts(cluster=cluster, action_host=action_host))
        inventory_data["all"]["children"].update(get_host_groups(cluster=cluster, delta=delta, action_host=action_host))

    if obj.prototype.type == "host":
        inventory_data["all"]["children"].update(get_host(host_id=obj.id))

        if action.host_action:
            inventory_data["all"]["children"].update(get_target_host(host_id=obj.id))

    if obj.prototype.type == "provider":
        inventory_data["all"]["children"].update(get_provider_hosts(provider=obj, action_host=action_host))
        inventory_data["all"]["vars"] = get_provider_config(provider_id=obj.id)

    return inventory_data


def prepare_job_inventory(
    obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    job_id: int,
    action: Action,
    delta: dict | None = None,
    action_host: list[Host] | None = None,
) -> None:
    if delta is None:
        delta = {}

    logger.info("prepare inventory for job #%s, object: %s", job_id, obj)
    # pylint: disable=consider-using-with
    file_descriptor = open(
        file=settings.RUN_DIR / f"{job_id}/inventory.json", mode="w", encoding=settings.ENCODING_UTF_8
    )

    inventory_data = get_inventory_data(obj=obj, action=action, action_host=action_host, delta=delta)

    json.dump(obj=inventory_data, fp=file_descriptor, indent=3)
    file_descriptor.close()
