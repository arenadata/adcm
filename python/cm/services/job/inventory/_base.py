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
from itertools import chain
from operator import itemgetter

from core.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from core.cluster.types import ClusterTopology, MaintenanceModeOfObjects, ObjectMaintenanceModeState
from core.types import ADCMCoreType, CoreObjectDescriptor, HostID, HostName, ObjectID
from django.db.models import F

from cm.models import (
    Action,
    Cluster,
    ClusterBind,
    ClusterObject,
    ConfigLog,
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
from cm.services.group_config import GroupConfigName, retrieve_group_configs_for_hosts
from cm.services.job.inventory._before_upgrade import extract_objects_before_upgrade, get_before_upgrades
from cm.services.job.inventory._config import (
    get_group_config_alternatives_for_hosts_in_cluster_groups,
    get_objects_configurations,
)
from cm.services.job.inventory._constants import MAINTENANCE_MODE_GROUP_SUFFIX
from cm.services.job.inventory._groups import detect_host_groups, detect_host_groups_for_action_on_host
from cm.services.job.inventory._steps import (
    process_config_and_attr,
)
from cm.services.job.inventory._types import (
    ClusterNode,
    ClusterVars,
    ComponentNode,
    HostGroupName,
    HostNode,
    HostProviderNode,
    ObjectsInInventoryMap,
    ServiceNode,
)

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
    _ = action_host  # todo cleanup
    if isinstance(obj, HostProvider):
        # is special case for now
        return _get_inventory_for_hostprovider(hostprovider=obj)

    cluster_topology = None
    if isinstance(obj, Cluster):
        cluster_topology = next(retrieve_clusters_topology([obj.pk]))
    elif obj.cluster_id is not None:
        cluster_topology = next(retrieve_clusters_topology([obj.cluster_id]))

    hosts_in_maintenance_mode: set[int] = set(
        Host.objects.filter(maintenance_mode=MaintenanceMode.ON).values_list("id", flat=True)
    )
    host_groups: dict[HostGroupName, set[tuple[HostID, HostName]]] = {}
    objects_in_inventory: ObjectsInInventoryMap = defaultdict(set)

    if isinstance(obj, Host):
        host_groups |= detect_host_groups_for_action_on_host(
            host_id=obj.pk,
            host_name=obj.name,
            host_is_in_maintenance_mode=obj.pk in hosts_in_maintenance_mode,
            action_belongs_to_this_host=not action.host_action,
            cluster_topology=cluster_topology,
        )
        objects_in_inventory[ADCMCoreType.HOSTPROVIDER] = {obj.provider_id}

    objects_in_maintenance_mode = MaintenanceModeOfObjects({}, {}, {})
    if cluster_topology:
        host_groups |= detect_host_groups(
            cluster_topology=cluster_topology, hosts_in_maintenance_mode=hosts_in_maintenance_mode, hc_delta=delta or {}
        )
        objects_in_inventory[ADCMCoreType.CLUSTER] = {cluster_topology.cluster_id}
        objects_in_inventory[ADCMCoreType.SERVICE] = set(cluster_topology.services)
        objects_in_inventory[ADCMCoreType.COMPONENT] = set(cluster_topology.component_ids)
        objects_in_maintenance_mode = calculate_maintenance_mode_for_cluster_objects(
            topology=cluster_topology,
            own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=[cluster_topology.cluster_id]),
        )

    objects_in_inventory[ADCMCoreType.HOST] = set(map(itemgetter(0), chain.from_iterable(host_groups.values())))

    group_configs = retrieve_group_configs_for_hosts(
        hosts=objects_in_inventory[ADCMCoreType.HOST],
        restrict_by_owner_type=(ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT),
    )
    objects_before_upgrades = get_before_upgrades(
        before_upgrades=extract_objects_before_upgrade(objects=objects_in_inventory),
        group_configs=group_configs.values(),
    )

    basic_nodes = _get_objects_basic_info(
        objects_in_inventory=objects_in_inventory,
        objects_configuration=get_objects_configurations(objects_in_inventory),
        objects_before_upgrade=objects_before_upgrades,
        objects_maintenance_mode=objects_in_maintenance_mode,
    )

    cluster_vars_dict = (
        _prepare_cluster_vars(topology=cluster_topology, objects_information=basic_nodes).dict(
            by_alias=True, exclude_defaults=True
        )
        if ADCMCoreType.CLUSTER in objects_in_inventory
        else {}
    )

    hostprovider_vars_dict = {}
    if hostprovider_id := next(iter(objects_in_inventory.get(ADCMCoreType.HOSTPROVIDER, (None,)))):
        hostprovider_vars_dict = {
            "provider": basic_nodes[ADCMCoreType.HOSTPROVIDER, hostprovider_id].dict(
                by_alias=True, exclude_defaults=True
            )
        }

    children = {}
    for group_name, host_tuples in host_groups.items():
        # group configs will be calculated here
        hosts = {
            host_name: basic_nodes[ADCMCoreType.HOST, host_id].dict(by_alias=True, exclude_defaults=True)
            for host_id, host_name in host_tuples
        }
        children[group_name] = {"hosts": hosts}

        if is_cluster_vars_required_for_group(group_name):
            children[group_name]["vars"] = cluster_vars_dict

        if is_host_provider_vars_required_for_group(group_name):
            children[group_name]["vars"] = hostprovider_vars_dict

    if group_configs:
        alternative_host_nodes = get_group_config_alternatives_for_hosts_in_cluster_groups(
            group_configs=group_configs.values(),
            cluster_vars=cluster_vars_dict,
            objects_before_upgrade=objects_before_upgrades,
            topology=cluster_topology,
        )

        for node in children.values():
            for host_name, host_node in node["hosts"].items():
                host_node.update(alternative_host_nodes.get(host_name, cluster_vars_dict))

    return {"all": {"children": children}}


def get_cluster_vars(topology: ClusterTopology) -> ClusterVars:
    objects_required_for_vars = {
        ADCMCoreType.CLUSTER: {topology.cluster_id},
        ADCMCoreType.SERVICE: set(topology.services),
        ADCMCoreType.COMPONENT: set(topology.component_ids),
    }

    return _prepare_cluster_vars(
        topology=topology,
        objects_information=_get_objects_basic_info(
            objects_in_inventory=objects_required_for_vars,
            objects_configuration=get_objects_configurations(objects_required_for_vars),
            objects_before_upgrade=get_before_upgrades(
                before_upgrades=extract_objects_before_upgrade(objects=objects_required_for_vars),
                # group configs aren't important for vars, so they can be just ignored
                group_configs=(),
            ),
            objects_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=[topology.cluster_id]),
        ),
    )


def _get_inventory_for_hostprovider(hostprovider: HostProvider) -> dict:
    hosts_group: set[tuple[HostID, HostName]] = set()
    hosts_in_maintenance_mode: set[HostID] = set()

    for host_id, host_name, host_mm in Host.objects.values_list("id", "fqdn", "maintenance_mode").filter(
        provider=hostprovider
    ):
        hosts_group.add((host_id, host_name))
        if host_mm == MaintenanceMode.ON:
            hosts_in_maintenance_mode.add(host_id)

    objects_in_inventory = {
        ADCMCoreType.HOSTPROVIDER: {hostprovider.pk},
        ADCMCoreType.HOST: set(map(itemgetter(0), hosts_group)),
    }

    nodes_info = _get_objects_basic_info(
        objects_in_inventory=objects_in_inventory,
        objects_configuration=get_objects_configurations(objects_in_inventory),
        objects_before_upgrade=get_before_upgrades(
            before_upgrades=extract_objects_before_upgrade(objects=objects_in_inventory),
            # todo IMO group configs are unimportant to provider and host own actions
            #  as well as topology, so no need to consider them here
            group_configs=(),
        ),
        objects_maintenance_mode=MaintenanceModeOfObjects(
            services={},
            components={},
            hosts={host_id: ObjectMaintenanceModeState.ON for host_id in hosts_in_maintenance_mode},
        ),
    )

    return {
        "all": {
            "children": {
                "PROVIDER": {
                    "hosts": {
                        host_name: nodes_info[ADCMCoreType.HOST, host_id].dict(by_alias=True, exclude_defaults=True)
                        for host_id, host_name in hosts_group
                        # should it be filtered out?
                        if host_id not in hosts_in_maintenance_mode
                    },
                }
            },
            "vars": {
                "provider": nodes_info[ADCMCoreType.HOSTPROVIDER, hostprovider.pk].dict(
                    by_alias=True, exclude_defaults=True
                )
            },
        }
    }


def _prepare_cluster_vars(
    topology: ClusterTopology,
    objects_information: dict[tuple[ADCMCoreType, ObjectID], ClusterNode | ServiceNode | ComponentNode],
) -> ClusterVars:
    result = ClusterVars(cluster=objects_information[ADCMCoreType.CLUSTER, topology.cluster_id], services={})

    for service in topology.services.values():
        service_node = objects_information[ADCMCoreType.SERVICE, service.info.id]
        for component in service.components.values():
            setattr(service_node, component.info.name, objects_information[ADCMCoreType.COMPONENT, component.info.id])
        result.services[service.info.name] = service_node

    return result


def _get_objects_basic_info(
    objects_in_inventory: ObjectsInInventoryMap,
    objects_configuration: dict[tuple[ADCMCoreType, ObjectID], dict],
    objects_before_upgrade: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, GroupConfigName], dict],
    objects_maintenance_mode: MaintenanceModeOfObjects,
) -> dict[
    tuple[ADCMCoreType, ObjectID],
    ClusterNode | ServiceNode | ComponentNode | HostNode | HostProviderNode,
]:
    result = {}
    basic_fields = ("id", "state")
    basic_spec_fields = {"multi_state": F("_multi_state")}

    if hosts := objects_in_inventory.get(ADCMCoreType.HOST):
        result |= {
            (ADCMCoreType.HOST, host_info["id"]): HostNode(
                **host_info,
                # it should be placed in basic_nodes already, see comment for function that retrieves those
                **objects_configuration[ADCMCoreType.HOST, host_info["id"]],
            )
            for host_info in Host.objects.filter(id__in=hosts).values(*basic_fields, **basic_spec_fields)
        }

    if hostproviders := objects_in_inventory.get(ADCMCoreType.HOSTPROVIDER):
        # for actions that really rely on provider there will be always 1 provider, right?
        hostprovider_id = next(iter(hostproviders))
        info = HostProvider.objects.values(*basic_fields, "name", "prototype__bundle_id", **basic_spec_fields).get(
            id=hostprovider_id
        )
        host_prototype_id = Prototype.objects.values_list("id", flat=True).get(
            type=ObjectType.HOST, bundle_id=info.pop("prototype__bundle_id")
        )
        result[(ADCMCoreType.HOSTPROVIDER, hostprovider_id)] = HostProviderNode(
            **info,
            host_prototype_id=host_prototype_id,
            config=objects_configuration[ADCMCoreType.HOSTPROVIDER, hostprovider_id],
            before_upgrade=objects_before_upgrade[
                CoreObjectDescriptor(type=ADCMCoreType.HOSTPROVIDER, id=hostprovider_id)
            ],
        )

    if clusters := objects_in_inventory.get(ADCMCoreType.CLUSTER):
        # if there's an action, there will be exactly one cluster
        cluster_id = next(iter(clusters))
        imports = _get_import(Cluster.objects.get(id=cluster_id))
        result[(ADCMCoreType.CLUSTER, cluster_id)] = ClusterNode(
            **Cluster.objects.values(
                *basic_fields,
                "name",
                **basic_spec_fields,
                version=F("prototype__version"),
                edition=F("prototype__bundle__edition"),
            ).get(id=cluster_id),
            config=objects_configuration[ADCMCoreType.CLUSTER, cluster_id],
            before_upgrade=objects_before_upgrade[CoreObjectDescriptor(type=ADCMCoreType.CLUSTER, id=cluster_id)],
            imports=imports or None,  # none for it to be thrown out of result dict
        )

        if services := objects_in_inventory.get(ADCMCoreType.SERVICE):
            result |= {
                (ADCMCoreType.SERVICE, service_info["id"]): ServiceNode(
                    **service_info,
                    maintenance_mode=objects_maintenance_mode.services[service_info["id"]]
                    == ObjectMaintenanceModeState.ON,
                    config=objects_configuration[ADCMCoreType.SERVICE, service_info["id"]],
                    before_upgrade=objects_before_upgrade[
                        CoreObjectDescriptor(type=ADCMCoreType.SERVICE, id=service_info["id"])
                    ],
                )
                for service_info in ClusterObject.objects.values(
                    *basic_fields,
                    **basic_spec_fields,
                    version=F("prototype__version"),
                    display_name=F("prototype__display_name"),
                ).filter(id__in=services)
            }

        if components := objects_in_inventory.get(ADCMCoreType.COMPONENT):
            result |= {
                (ADCMCoreType.COMPONENT, component_info["id"]): ComponentNode(
                    **component_info,
                    maintenance_mode=objects_maintenance_mode.components[component_info["id"]]
                    == ObjectMaintenanceModeState.ON,
                    config=objects_configuration[ADCMCoreType.COMPONENT, component_info["id"]],
                    before_upgrade=objects_before_upgrade[
                        CoreObjectDescriptor(type=ADCMCoreType.COMPONENT, id=component_info["id"])
                    ],
                )
                for component_info in ServiceComponent.objects.values(
                    *basic_fields, **basic_spec_fields, display_name=F("prototype__display_name")
                ).filter(id__in=components)
            }

    return result


# fixme NOT OPTIMIZED CHAOS SECTION


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
