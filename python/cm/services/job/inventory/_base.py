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

from collections import defaultdict
from copy import deepcopy
from itertools import chain
from operator import attrgetter, itemgetter
from typing import Iterable

from core.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from core.cluster.types import ClusterTopology, MaintenanceModeOfObjects, ObjectMaintenanceModeState
from core.types import ADCMCoreType, HostID, HostName, ObjectID
from django.db.models import F

from cm.converters import core_type_to_model
from cm.models import (
    Action,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConfigLog,
    GroupConfig,
    Host,
    HostProvider,
    MaintenanceMode,
    ObjectType,
    Prototype,
    PrototypeExport,
    PrototypeImport,
    ServiceComponent,
)
from cm.services.cluster import retrieve_clusters_objects_maintenance_mode, retrieve_clusters_topology
from cm.services.group_config import GroupConfigInfo, retrieve_group_configs_for_hosts
from cm.services.job.inventory._constants import MAINTENANCE_MODE_GROUP_SUFFIX
from cm.services.job.inventory._groups import detect_host_groups, detect_host_groups_for_action_on_host
from cm.services.job.inventory._steps import (
    get_before_upgrade,
    get_group_config,
    get_obj_config,
    process_config_and_attr,
)
from cm.services.job.inventory._types import (
    ClusterVars,
    HostGroupName,
    InventoryORMObject,
    _ClusterNode,
    _ComponentNode,
    _HostNode,
    _HostProviderNode,
    _ServiceNode,
)

_ObjectsInInventoryMap = dict[type[InventoryORMObject], set[ObjectID]]


_STATIC_CLUSTER_VARS_GROUPS: frozenset[str] = frozenset({"CLUSTER", "target"})
# PROVIDER not in here, because provider group doesn't have vars
_STATIC_HOSTPROVIDER_VARS_GROUPS: frozenset[str] = frozenset({"HOST"})


def is_cluster_vars_required_for_group(group_name: HostGroupName) -> bool:
    return group_name in _STATIC_CLUSTER_VARS_GROUPS or MAINTENANCE_MODE_GROUP_SUFFIX in group_name


def is_host_provider_vars_required_for_group(group_name: HostGroupName) -> bool:
    return group_name in _STATIC_HOSTPROVIDER_VARS_GROUPS


def get_inventory_data(
    obj: Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    action: Action,
    action_host: list[Host] | None = None,
    delta: dict | None = None,
) -> dict:
    if isinstance(obj, HostProvider):
        # is special case for now
        return _get_inventory_for_hostprovider(hostprovider=obj, action_host=action_host)

    cluster_topology = None
    if isinstance(obj, Cluster):
        cluster_topology = next(retrieve_clusters_topology([obj.pk]))
    elif obj.cluster_id is not None:
        cluster_topology = next(retrieve_clusters_topology([obj.cluster_id]))

    hosts_in_maintenance_mode: set[int] = set(
        Host.objects.filter(maintenance_mode=MaintenanceMode.ON).values_list("id", flat=True)
    )
    host_groups: dict[HostGroupName, set[tuple[HostID, HostName]]] = {}
    objects_in_inventory: _ObjectsInInventoryMap = defaultdict(set)

    if isinstance(obj, Host):
        host_groups |= detect_host_groups_for_action_on_host(
            host_id=obj.pk,
            host_name=obj.name,
            host_is_in_maintenance_mode=obj.pk in hosts_in_maintenance_mode,
            action_belongs_to_this_host=not action.host_action,
            cluster_topology=cluster_topology,
        )
        objects_in_inventory[HostProvider] = {obj.provider_id}

    objects_in_maintenance_mode = MaintenanceModeOfObjects({}, {}, {})
    if cluster_topology:
        host_groups |= detect_host_groups(
            cluster_topology=cluster_topology, hosts_in_maintenance_mode=hosts_in_maintenance_mode, hc_delta=delta or {}
        )
        objects_in_inventory[Cluster] = {cluster_topology.cluster_id}
        objects_in_inventory[ClusterObject] = set(cluster_topology.services)
        objects_in_inventory[ServiceComponent] = set(cluster_topology.component_ids)
        objects_in_maintenance_mode = calculate_maintenance_mode_for_cluster_objects(
            topology=cluster_topology,
            own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=[cluster_topology.cluster_id]),
        )

    objects_in_inventory[Host] = set(map(itemgetter(0), chain.from_iterable(host_groups.values())))

    basic_nodes = _get_objects_basic_info(
        objects_in_inventory=objects_in_inventory,
        objects_configuration=_get_objects_configurations(objects_in_inventory),
        objects_before_upgrade=_get_objects_before_upgrade(objects_in_inventory),
        objects_maintenance_mode=objects_in_maintenance_mode,
    )

    cluster_vars_dict = (
        _prepare_cluster_vars(topology=cluster_topology, objects_information=basic_nodes).dict(
            by_alias=True, exclude_defaults=True
        )
        if Cluster in objects_in_inventory
        else {}
    )

    hostprovider_vars_dict = {}
    if hostprovider_id := next(iter(objects_in_inventory.get(HostProvider, (None,)))):
        hostprovider_vars_dict = {
            "provider": basic_nodes[HostProvider, hostprovider_id].dict(by_alias=True, exclude_defaults=True)
        }

    children = {}
    for group_name, host_tuples in host_groups.items():
        # group configs will be calculated here
        hosts = {
            host_name: basic_nodes[Host, host_id].dict(by_alias=True, exclude_defaults=True)
            for host_id, host_name in host_tuples
        }
        children[group_name] = {"hosts": hosts}

        if is_cluster_vars_required_for_group(group_name):
            children[group_name]["vars"] = cluster_vars_dict

        if is_host_provider_vars_required_for_group(group_name):
            children[group_name]["vars"] = hostprovider_vars_dict

    group_configs = retrieve_group_configs_for_hosts(
        hosts=objects_in_inventory[Host],
        restrict_by_owner_type=(ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT),
    )
    if group_configs:
        alternative_host_nodes = _get_group_config_alternatives_for_hosts_in_cluster_groups(
            group_configs=group_configs.values(), cluster_vars=cluster_vars_dict, topology=cluster_topology
        )

        for node in children.values():
            for host_name, host_node in node["hosts"].items():
                host_node.update(alternative_host_nodes.get(host_name, cluster_vars_dict))

    return {"all": {"children": children}}


def get_cluster_vars(topology: ClusterTopology) -> ClusterVars:
    objects_required_for_vars = {
        Cluster: {topology.cluster_id},
        ClusterObject: set(topology.services),
        ServiceComponent: set(topology.component_ids),
    }

    return _prepare_cluster_vars(
        topology=topology,
        objects_information=_get_objects_basic_info(
            objects_in_inventory=objects_required_for_vars,
            objects_configuration=_get_objects_configurations(objects_required_for_vars),
            objects_before_upgrade=_get_objects_before_upgrade(objects_required_for_vars),
            objects_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=[topology.cluster_id]),
        ),
    )


def _prepare_cluster_vars(
    topology: ClusterTopology,
    objects_information: dict[
        tuple[type[Cluster | ClusterObject | ServiceComponent], ObjectID], _ClusterNode | _ServiceNode | _ComponentNode
    ],
) -> ClusterVars:
    result = ClusterVars(cluster=objects_information[Cluster, topology.cluster_id], services={})

    for service in topology.services.values():
        service_node = objects_information[ClusterObject, service.info.id]
        for component in service.components.values():
            setattr(service_node, component.info.name, objects_information[ServiceComponent, component.info.id])
        result.services[service.info.name] = service_node

    return result


def _get_objects_basic_info(
    objects_in_inventory: _ObjectsInInventoryMap,
    objects_configuration: dict[tuple[type[InventoryORMObject], ObjectID], dict],
    objects_before_upgrade: dict[tuple[type[InventoryORMObject], ObjectID], dict],
    objects_maintenance_mode: MaintenanceModeOfObjects,
) -> dict[
    tuple[type[InventoryORMObject], ObjectID],
    _ClusterNode | _ServiceNode | _ComponentNode | _HostNode | _HostProviderNode,
]:
    result = {}
    basic_fields = ("id", "state")
    basic_spec_fields = {"multi_state": F("_multi_state")}

    if hosts := objects_in_inventory.get(Host):
        result |= {
            (Host, host_info["id"]): _HostNode(
                **host_info,
                # it should be placed in basic_nodes already, see comment for function that retrieves those
                **objects_configuration[Host, host_info["id"]],
            )
            for host_info in Host.objects.filter(id__in=hosts).values(*basic_fields, **basic_spec_fields)
        }

    if hostproviders := objects_in_inventory.get(HostProvider):
        # for actions that really rely on provider there will be always 1 provider, right?
        hostprovider_id = next(iter(hostproviders))
        info = HostProvider.objects.values(*basic_fields, "name", "prototype__bundle_id", **basic_spec_fields).get(
            id=hostprovider_id
        )
        host_prototype_id = Prototype.objects.values_list("id", flat=True).get(
            type=ObjectType.HOST, bundle_id=info.pop("prototype__bundle_id")
        )
        result[(HostProvider, hostprovider_id)] = _HostProviderNode(
            **info,
            host_prototype_id=host_prototype_id,
            config=objects_configuration[HostProvider, hostprovider_id],
            before_upgrade=objects_before_upgrade[HostProvider, hostprovider_id],
        )

    if clusters := objects_in_inventory.get(Cluster):
        # if there's an action, there will be exactly one cluster
        cluster_id = next(iter(clusters))
        imports = _get_import(Cluster.objects.get(id=cluster_id))
        result[(Cluster, cluster_id)] = _ClusterNode(
            **Cluster.objects.values(
                *basic_fields,
                "name",
                **basic_spec_fields,
                version=F("prototype__version"),
                edition=F("prototype__bundle__edition"),
            ).get(id=cluster_id),
            config=objects_configuration[Cluster, cluster_id],
            before_upgrade=objects_before_upgrade[Cluster, cluster_id],
            imports=imports or None,  # none for it to be thrown out of result dict
        )

        if services := objects_in_inventory.get(ClusterObject):
            result |= {
                (ClusterObject, service_info["id"]): _ServiceNode(
                    **service_info,
                    maintenance_mode=objects_maintenance_mode.services[service_info["id"]]
                    == ObjectMaintenanceModeState.ON,
                    config=objects_configuration[ClusterObject, service_info["id"]],
                    before_upgrade=objects_before_upgrade[ClusterObject, service_info["id"]],
                )
                for service_info in ClusterObject.objects.values(
                    *basic_fields,
                    **basic_spec_fields,
                    version=F("prototype__version"),
                    display_name=F("prototype__display_name"),
                ).filter(id__in=services)
            }

        if components := objects_in_inventory.get(ServiceComponent):
            result |= {
                (ServiceComponent, component_info["id"]): _ComponentNode(
                    **component_info,
                    maintenance_mode=objects_maintenance_mode.components[component_info["id"]]
                    == ObjectMaintenanceModeState.ON,
                    config=objects_configuration[ServiceComponent, component_info["id"]],
                    before_upgrade=objects_before_upgrade[ServiceComponent, component_info["id"]],
                )
                for component_info in ServiceComponent.objects.values(
                    *basic_fields, **basic_spec_fields, display_name=F("prototype__display_name")
                ).filter(id__in=components)
            }

    return result


# FIXME  PROVIDER BRANCH


def _get_inventory_for_hostprovider(
    hostprovider: HostProvider,
    # is `action_host` even necessary ?? looks like a "host action" flag of something
    action_host: list[Host] | None,
) -> dict:
    return {
        "all": {
            "children": {
                "PROVIDER": {
                    "hosts": _get_hosts(
                        host_list=Host.objects.filter(provider=hostprovider), obj=hostprovider, action_host=action_host
                    ),
                }
            },
            "vars": _get_provider_config(provider_id=hostprovider.pk),
        }
    }


def _get_hosts(
    host_list: list[Host], obj: HostProvider, action_host: list[Host] | None = None, include_mm_hosts: bool = False
) -> dict:
    group = {}
    for host in host_list:
        skip_mm_host = host.maintenance_mode == MaintenanceMode.ON and not include_mm_hosts
        skip_host_not_in_action_host = action_host and host.id not in action_host

        if skip_mm_host or skip_host_not_in_action_host:
            continue

        group[host.fqdn] = {
            **get_obj_config(obj=host),
            "adcm_hostid": host.id,
            "state": host.state,
            "multi_state": host.multi_state,
        }

        if host.group_config.exists():
            group[host.fqdn] |= {
                "provider": {
                    "config": get_group_config(obj=obj, host=host),
                    "name": obj.name,
                    "id": obj.id,
                    "host_prototype_id": host.prototype_id,
                    "state": obj.state,
                    "multi_state": obj.multi_state,
                    "before_upgrade": get_before_upgrade(obj=obj, host=host),
                }
            }

    return group


def _get_provider_config(provider_id: int) -> dict:
    provider = HostProvider.objects.get(id=provider_id)
    host_proto = Prototype.objects.get(bundle=provider.prototype.bundle, type="host")
    return {
        "provider": {
            "config": get_obj_config(obj=provider),
            "name": provider.name,
            "id": provider.id,
            "host_prototype_id": host_proto.id,
            "state": provider.state,
            "multi_state": provider.multi_state,
            "before_upgrade": get_before_upgrade(obj=provider, host=None),
        }
    }


# fixme NOT OPTIMIZED CHAOS SECTION


def _get_group_config_alternatives_for_hosts_in_cluster_groups(
    group_configs: Iterable[GroupConfigInfo], cluster_vars: dict, topology: ClusterTopology
) -> dict[str, dict]:
    # this whole recollection should be avoided, there is enough information already
    hosts = {
        host.id: host
        for host in Host.objects.filter(
            id__in=chain.from_iterable(map(attrgetter("id"), group.hosts) for group in group_configs)
        )
    }

    result = defaultdict(lambda: deepcopy(cluster_vars))

    for group in group_configs:
        if not group.hosts:
            continue

        object_ = core_type_to_model(group.owner.type).objects.select_related("prototype").get(id=group.owner.id)

        orm_group = GroupConfig.objects.get(id=group.id)
        # `get_config_and_attr` is a suspicious function to call at that point
        # probably should be avoided during config of group config retrieval optimization
        conf, attr = orm_group.get_config_and_attr()
        group_config = process_config_and_attr(obj=orm_group, conf=conf, attr=attr)

        for host_info in group.hosts:
            before_upgrade = get_before_upgrade(obj=object_, host=hosts[host_info.id])

            node = None
            match group.owner.type:
                case ADCMCoreType.CLUSTER:
                    node = result[host_info.name]["cluster"]
                case ADCMCoreType.SERVICE:
                    node = result[host_info.name]["services"][topology.services[group.owner.id].info.name]
                case ADCMCoreType.COMPONENT:
                    service = next(
                        (service_ for service_ in topology.services.values() if group.owner.id in service_.components),
                        None,
                    )
                    if service:
                        node = result[host_info.name]["services"][service.info.name][
                            service.components[group.owner.id].info.name
                        ]

            if not node:
                raise RuntimeError(f"Failed to determine node in `vars` for {group.owner}")

            node["before_upgrade"] = before_upgrade
            node["config"] = group_config

    return result


def _get_objects_before_upgrade(
    objects_in_inventory: _ObjectsInInventoryMap,
) -> dict[tuple[type[InventoryORMObject], ObjectID], dict]:
    return {
        (type_, object_id): get_before_upgrade(obj=type_.objects.get(pk=object_id), host=None)
        for type_, ids in objects_in_inventory.items()
        for object_id in ids
        if type_ != Host
    }


def _get_objects_configurations(
    objects_in_inventory: _ObjectsInInventoryMap,
) -> dict[tuple[type[InventoryORMObject], ObjectID], dict]:
    return {
        (type_, object_id): get_obj_config(type_.objects.get(pk=object_id))
        for type_, ids in objects_in_inventory.items()
        for object_id in ids
    }


# fixme this function may be useful as a public one
#  if it'll return some ImportedConfig object
#  otherwise it should stay protected AS IS
def _get_import(cluster: Cluster) -> dict:
    imports = {}
    for obj in chain([cluster], ClusterObject.objects.filter(cluster=cluster)):
        imports = _get_prototype_imports(obj=obj, imports=imports)

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


def _get_prototype_imports(obj: Cluster | ClusterObject, imports: dict) -> dict:
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
