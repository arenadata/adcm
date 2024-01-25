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

from itertools import chain
from typing import Iterable
import json

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from cm.adcm_config.config import get_prototype_config, process_config
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
    ObjectType,
    Prototype,
    PrototypeConfig,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
    get_default_before_upgrade,
    get_object_cluster,
)


class HcAclAction:
    ADD = "add"
    REMOVE = "remove"


MAINTENANCE_MODE = "maintenance_mode"


def fix_fields_for_inventory(prototype_configs: Iterable[PrototypeConfig], config: dict) -> None:
    """
    This function is designed to convert fields of map and list types for inventory
    """
    for prototype_config in prototype_configs:
        if prototype_config.type not in {"map", "list"}:
            continue

        name = prototype_config.name
        sub_name = prototype_config.subname

        fix_value = {} if prototype_config.type == "map" else []

        if sub_name and name in config and sub_name in config[name]:
            if config[name][sub_name] is None:
                config[name][sub_name] = fix_value
        else:
            if name in config and config[name] is None:
                config[name] = fix_value


def process_config_and_attr(
    obj: Cluster | ClusterObject | ServiceComponent | HostProvider | Host | GroupConfig,
    conf: dict,
    attr: dict | None = None,
    spec: dict | None = None,
    flat_spec: dict | None = None,
) -> dict:
    if not spec:
        prototype = obj.object.prototype if isinstance(obj, GroupConfig) else obj.prototype

        spec, flat_spec, _, _ = get_prototype_config(prototype=prototype)

    new_config = process_config(obj=obj, spec=spec, old_conf=conf)
    fix_fields_for_inventory(prototype_configs=flat_spec.values(), config=new_config)

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


def get_import(cluster: Cluster) -> dict:
    imports = {}
    for obj in chain([cluster], ClusterObject.objects.filter(cluster=cluster)):
        imports = get_prototype_imports(obj=obj, imports=imports)

    first = True
    for bind in ClusterBind.objects.filter(cluster=cluster):
        obj = bind.source_service if bind.source_service else bind.source_cluster

        conf_ref = obj.config
        export_proto = obj.prototype
        config_log = ConfigLog.objects.get(obj_ref=conf_ref, id=conf_ref.current)
        conf = process_config_and_attr(obj=obj, conf=config_log.config, attr=config_log.attr)

        proto = bind.service.prototype if bind.service else bind.cluster.prototype

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


def get_obj_config(obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host) -> dict:
    if obj.config is None:
        return {}

    config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)

    return process_config_and_attr(obj=obj, conf=config_log.config, attr=config_log.attr)


def get_before_upgrade(obj: ADCMEntity, host: Host | None) -> dict:
    if obj.before_upgrade == get_default_before_upgrade():
        return obj.before_upgrade

    config, group_object = None, None
    config_log = ConfigLog.objects.filter(id=obj.before_upgrade.get("config_id")).first()
    if host is not None:
        group = host.group_config.filter(
            object_id=obj.id, object_type=ContentType.objects.get_for_model(model=obj)
        ).first()

        if group and obj.before_upgrade.get("groups") and group.name in obj.before_upgrade["groups"]:
            config_log = ConfigLog.objects.filter(
                id=obj.before_upgrade["groups"][group.name]["group_config_id"]
            ).first()
            group_object = group

    if config_log:
        if not obj.before_upgrade.get("bundle_id"):
            bundle_id = obj.cluster.before_upgrade["bundle_id"]
        else:
            bundle_id = obj.before_upgrade["bundle_id"]

        obj_prototype = obj.prototype
        try:
            if obj_prototype.type == ObjectType.COMPONENT:
                old_proto = Prototype.objects.get(
                    name=obj_prototype.name, parent__name=obj_prototype.parent.name, bundle_id=bundle_id
                )
            else:
                old_proto = Prototype.objects.get(name=obj_prototype.name, bundle_id=bundle_id, parent=None)

        except Prototype.DoesNotExist:
            logger.info("Can't get old proto for %s. Old bundle id: %s", obj, bundle_id)

        else:
            old_spec, old_flat_spec, _, _ = get_prototype_config(prototype=old_proto)
            config = process_config_and_attr(
                obj=group_object or obj,
                conf=config_log.config,
                attr=config_log.attr,
                spec=old_spec,
                flat_spec=old_flat_spec,
            )

    return {"state": obj.before_upgrade.get("state"), "config": config}


def get_cluster_variables(cluster: Cluster, cluster_config: dict | None = None, host: Host | None = None) -> dict:
    result = {
        "config": cluster_config or get_obj_config(obj=cluster),
        "name": cluster.name,
        "id": cluster.id,
        "version": cluster.prototype.version,
        "edition": cluster.prototype.bundle.edition,
        "state": cluster.state,
        "multi_state": cluster.multi_state,
        "before_upgrade": get_before_upgrade(obj=cluster, host=host),
    }

    imports = get_import(cluster=cluster)
    if imports:
        result["imports"] = imports

    return result


def get_service_variables(service: ClusterObject, service_config: dict | None = None, host: Host | None = None) -> dict:
    return {
        "id": service.id,
        "version": service.prototype.version,
        "state": service.state,
        "multi_state": service.multi_state,
        "config": service_config or get_obj_config(obj=service),
        MAINTENANCE_MODE: service.maintenance_mode == MaintenanceMode.ON,
        "display_name": service.display_name,
        "before_upgrade": get_before_upgrade(obj=service, host=host),
    }


def get_component_variables(
    component: ServiceComponent, component_config: dict | None = None, host: Host | None = None
) -> dict:
    return {
        "component_id": component.id,
        "config": component_config or get_obj_config(obj=component),
        "state": component.state,
        "multi_state": component.multi_state,
        MAINTENANCE_MODE: component.maintenance_mode == MaintenanceMode.ON,
        "display_name": component.display_name,
        "before_upgrade": get_before_upgrade(obj=component, host=host),
    }


def get_provider_variables(
    provider: HostProvider, provider_config: dict | None = None, host: Host | None = None
) -> dict:
    host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type="host")
    return {
        "config": provider_config or get_obj_config(obj=provider),
        "name": provider.name,
        "id": provider.id,
        "host_prototype_id": host_proto.id,
        "state": provider.state,
        "multi_state": provider.multi_state,
        "before_upgrade": get_before_upgrade(obj=provider, host=host),
    }


def get_group_config(obj: ADCMEntity, host: Host) -> dict | None:
    group = host.group_config.filter(object_id=obj.id, object_type=ContentType.objects.get_for_model(obj)).last()
    group_config = None
    if group:
        conf, attr = group.get_config_and_attr()
        group_config = process_config_and_attr(obj=group, conf=conf, attr=attr)
    return group_config


def get_host_vars(host: Host, obj: ADCMEntity) -> dict:
    variables = {}
    if not host.group_config.exists():
        return variables

    if isinstance(obj, Cluster):
        variables.update(
            {
                "cluster": get_cluster_variables(
                    cluster=obj,
                    cluster_config=get_group_config(obj=obj, host=host),
                    host=host,
                )
            }
        )
        variables.update({"services": {}})
        for service in ClusterObject.objects.filter(cluster=obj):
            variables["services"][service.prototype.name] = get_service_variables(
                service=service,
                service_config=get_group_config(obj=service, host=host),
                host=host,
            )
            for component in ServiceComponent.objects.filter(cluster=obj, service=service):
                variables["services"][service.prototype.name][component.prototype.name] = get_component_variables(
                    component=component, component_config=get_group_config(obj=component, host=host), host=host
                )

    elif isinstance(obj, (ClusterObject, ServiceComponent)):
        variables.update({"services": {}})

        for service in ClusterObject.objects.filter(cluster=obj.cluster):
            variables["services"][service.prototype.name] = get_service_variables(
                service=service,
                service_config=get_group_config(obj=service, host=host),
                host=host,
            )
            for component in ServiceComponent.objects.filter(cluster=obj.cluster, service=service):
                variables["services"][service.prototype.name][component.prototype.name] = get_component_variables(
                    component=component,
                    component_config=get_group_config(obj=component, host=host),
                    host=host,
                )

    else:
        obj: HostProvider
        variables.update(
            {
                "provider": get_provider_variables(
                    provider=obj,
                    provider_config=get_group_config(obj=obj, host=host),
                    host=host,
                )
            },
        )

    return variables


def get_cluster_config(cluster: Cluster) -> dict:
    result = {
        "cluster": get_cluster_variables(cluster=cluster),
        "services": {},
    }

    for service in ClusterObject.objects.filter(cluster=cluster):
        result["services"][service.prototype.name] = get_service_variables(service=service)
        for component in ServiceComponent.objects.filter(cluster=cluster, service=service):
            result["services"][service.prototype.name][component.prototype.name] = get_component_variables(
                component=component
            )

    return result


def get_provider_config(provider_id: int) -> dict:
    provider = HostProvider.objects.get(id=provider_id)
    return {"provider": get_provider_variables(provider=provider)}


def get_host_groups(
    cluster: Cluster,
    delta: dict | None = None,
    action_host: Host | None = None,
) -> dict:
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

        for key, _ in key_object_pairs:
            if hostcomponent.host.maintenance_mode == MaintenanceMode.ON:
                key = f"{key}.{MAINTENANCE_MODE}"

            if key not in groups:
                groups[key] = {"hosts": {}}

            if MAINTENANCE_MODE in key:
                groups[key]["vars"] = get_cluster_config(cluster=cluster)

            update_host_dict(hosts_group=groups[key]["hosts"], host=hostcomponent.host)
            groups[key]["hosts"][hostcomponent.host.fqdn].update(get_host_vars(host=hostcomponent.host, obj=cluster))

    for hc_acl_action in delta:
        for key in delta[hc_acl_action]:
            lkey = f"{key}.{hc_acl_action}"

            if lkey not in groups:
                groups[lkey] = {"hosts": {}}

            for fqdn in delta[hc_acl_action][key]:
                host = delta[hc_acl_action][key][fqdn]

                if host.maintenance_mode != MaintenanceMode.ON:
                    groups[lkey]["hosts"][host.fqdn] = get_obj_config(obj=host)

                if hc_acl_action == HcAclAction.REMOVE and host.maintenance_mode == MaintenanceMode.ON:
                    remove_maintenance_mode_group_name = f"{lkey}.{MAINTENANCE_MODE}"

                    if remove_maintenance_mode_group_name not in groups:
                        groups[remove_maintenance_mode_group_name] = {"hosts": {}}

                    update_host_dict(hosts_group=groups[remove_maintenance_mode_group_name]["hosts"], host=host)
                    groups[remove_maintenance_mode_group_name]["hosts"][host.fqdn].update(
                        get_host_vars(host=host, obj=cluster)
                    )

    return groups


def update_host_dict(hosts_group: dict, host: Host) -> None:
    hosts_group[host.fqdn] = get_obj_config(obj=host)
    hosts_group[host.fqdn]["adcm_hostid"] = host.id
    hosts_group[host.fqdn]["state"] = host.state
    hosts_group[host.fqdn]["multi_state"] = host.multi_state


def get_hosts(
    host_list: list[Host], obj: ADCMEntity, action_host: list[Host] | None = None, include_mm_hosts: bool = False
) -> dict:
    group = {}
    for host in host_list:
        skip_mm_host = host.maintenance_mode == MaintenanceMode.ON and not include_mm_hosts
        skip_host_not_in_action_host = action_host and host.id not in action_host

        if skip_mm_host or skip_host_not_in_action_host:
            continue

        update_host_dict(hosts_group=group, host=host)
        if not isinstance(obj, Host):
            group[host.fqdn].update(get_host_vars(host=host, obj=obj))

    return group


def get_cluster_hosts(cluster: Cluster, action_host: list[Host] | None = None) -> dict:
    return {
        "CLUSTER": {
            "hosts": get_hosts(host_list=Host.objects.filter(cluster=cluster), obj=cluster, action_host=action_host),
            "vars": get_cluster_config(cluster=cluster),
        },
    }


def get_provider_hosts(provider: HostProvider, action_host: list[Host] | None = None) -> dict:
    return {
        "PROVIDER": {
            "hosts": get_hosts(host_list=Host.objects.filter(provider=provider), obj=provider, action_host=action_host),
        },
    }


def get_host(host_id: int) -> dict:
    host = Host.objects.get(id=host_id)
    return {
        "HOST": {
            "hosts": get_hosts(host_list=[host], obj=host),
            "vars": get_provider_config(provider_id=host.provider.id),
        }
    }


def get_target_host(host_id: int) -> dict:
    host = Host.objects.get(id=host_id)
    return {
        "target": {
            "hosts": get_hosts(host_list=[host], obj=host, include_mm_hosts=True),
            "vars": get_cluster_config(cluster=host.cluster),
        }
    }


def get_inventory_data(
    obj: ADCMEntity,
    action: Action,
    action_host: list[Host] | None = None,
    delta: dict | None = None,
) -> dict:
    if delta is None:
        delta = {}

    inventory_data = {"all": {"children": {}}}
    cluster = get_object_cluster(obj=obj)

    if cluster:
        inventory_data["all"]["children"].update(get_cluster_hosts(cluster=cluster, action_host=action_host))
        inventory_data["all"]["children"].update(
            get_host_groups(cluster=cluster, delta=delta, action_host=action_host),
        )

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

    with open(
        settings.RUN_DIR / f"{job_id}/inventory.json", mode="w", encoding=settings.ENCODING_UTF_8
    ) as file_descriptor:
        inventory_data = get_inventory_data(obj=obj, action=action, action_host=action_host, delta=delta)
        json.dump(obj=inventory_data, fp=file_descriptor, separators=(",", ":"))
