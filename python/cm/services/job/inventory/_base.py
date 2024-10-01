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
from operator import itemgetter
from typing import Iterable

from core.cluster.operations import calculate_maintenance_mode_for_cluster_objects
from core.cluster.types import ClusterTopology, MaintenanceModeOfObjects, ObjectMaintenanceModeState
from core.job.types import RelatedObjects
from core.types import (
    ActionTargetDescriptor,
    ADCMCoreType,
    CoreObjectDescriptor,
    ExtraActionTargetType,
    HostID,
    HostName,
    ObjectID,
)
from django.db.models import F

from cm.converters import core_type_to_model
from cm.models import (
    ActionHostGroup,
    Cluster,
    Component,
    Host,
    HostProvider,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Service,
)
from cm.services.cluster import (
    retrieve_cluster_topology,
    retrieve_clusters_objects_maintenance_mode,
)
from cm.services.group_config import GroupConfigName, retrieve_group_configs_for_hosts
from cm.services.job.inventory._before_upgrade import extract_objects_before_upgrade, get_before_upgrades
from cm.services.job.inventory._config import (
    get_group_config_alternatives_for_hosts_in_cluster_groups,
    get_group_config_alternatives_for_hosts_in_hostprovider_groups,
    get_objects_configurations,
)
from cm.services.job.inventory._groups import detect_host_groups_for_cluster_bundle_action
from cm.services.job.inventory._imports import get_imports_for_inventory
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
from cm.services.job.types import TaskMappingDelta


def get_inventory_data(
    target: ActionTargetDescriptor,
    is_host_action: bool,
    delta: TaskMappingDelta | None = None,
    related_objects: RelatedObjects | None = None,
) -> dict:
    if target.type == ExtraActionTargetType.ACTION_HOST_GROUP:
        # Some time ago `_get_inventory_for_action_from_cluster_bundle` required full ORM object to proceed,
        # now it's not the case, so you can optimize this call if you want to.
        group = ActionHostGroup.objects.prefetch_related("hosts", "object").get(id=target.id)

        # It is possible that `object` does not exist at that point (deleted via `delete_service` in previous jobs),
        # but it's inadequate situation and in "context of action target group" such mutations aren't expected.
        return _get_inventory_for_action_from_cluster_bundle(
            cluster_id=group.object.id if isinstance(group.object, Cluster) else group.object.cluster_id,
            delta=delta or TaskMappingDelta(),
            target_hosts=tuple((host.pk, host.fqdn) for host in group.hosts.all()),
        )

    if target.type == ADCMCoreType.HOSTPROVIDER or (target.type == ADCMCoreType.HOST and not is_host_action):
        return _get_inventory_for_action_from_hostprovider_bundle(
            object_=core_type_to_model(target.type).objects.get(id=target.id)
        )

    # Retrieval of full object was changed to `cluster_id` only for cluster-related action inventory building,
    # because target deletion cases exists.
    # For example, action is defined on service and previous job calls `delete_service` ansible plugin,
    # then there will be no service at this point.
    # And we don't actually need the full object, just `cluster_id` to detect the topology.
    # We also has information about `owner` (not `target`) related objects with possible presence of `cluster_id`.
    # It is still possible that `cluster_id` will be undetected, then this approach should be reworked
    # by storing required info at point when object has to exist (e.g. at task start).
    cluster_id: int | None = None
    target_hosts: tuple[tuple[int, str], ...] = ()
    if target.type == ADCMCoreType.HOST:
        if not is_host_action:
            message = "Only actions with `host_action: true` can be launched on host"
            raise RuntimeError(message)

        host_id, host_name, cluster_id = Host.objects.filter(id=target.id).values_list("id", "fqdn", "cluster_id").get()
        target_hosts = ((host_id, host_name),)

    if not cluster_id:
        if target.type == ADCMCoreType.CLUSTER:
            cluster_id = target.id
        elif related_objects and related_objects.cluster:
            cluster_id = related_objects.cluster.id
        elif target.type in (ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT):
            # In real scenarios it's unlikely situation, but since we can get it that way, we should.
            # It also easies testing when we don't want to specify `related_object` due to object existence.
            # We don't catch non-existence errors in here, since it'll be descriptive enough.
            cluster_id = core_type_to_model(target.type).objects.values_list("cluster_id", flat=True).get(id=target.id)

    if not cluster_id:
        message = (
            f"Failed to detect cluster id based on target and related objects.\n"
            f"Target: {target}\n"
            f"Related objects: {related_objects}"
        )
        raise RuntimeError(message)

    return _get_inventory_for_action_from_cluster_bundle(
        cluster_id=cluster_id, delta=delta or TaskMappingDelta(), target_hosts=target_hosts
    )


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


def _get_inventory_for_action_from_cluster_bundle(
    cluster_id: int, delta: TaskMappingDelta, target_hosts: Iterable[tuple[HostID, HostName]]
) -> dict:
    host_groups: dict[HostGroupName, set[tuple[HostID, HostName]]] = {}

    if target_hosts:
        host_groups["target"] = set(target_hosts)

    cluster_topology = retrieve_cluster_topology(cluster_id)

    hosts_in_maintenance_mode: set[int] = set(
        Host.objects.filter(maintenance_mode=MaintenanceMode.ON).values_list("id", flat=True)
    )

    host_groups |= detect_host_groups_for_cluster_bundle_action(
        cluster_topology=cluster_topology, hosts_in_maintenance_mode=hosts_in_maintenance_mode, hc_delta=delta
    )

    objects_in_inventory = {
        ADCMCoreType.CLUSTER: {cluster_topology.cluster_id},
        ADCMCoreType.SERVICE: set(cluster_topology.services),
        ADCMCoreType.COMPONENT: set(cluster_topology.component_ids),
        ADCMCoreType.HOST: set(map(itemgetter(0), chain.from_iterable(host_groups.values()))),
    }

    objects_in_maintenance_mode = calculate_maintenance_mode_for_cluster_objects(
        topology=cluster_topology,
        own_maintenance_mode=retrieve_clusters_objects_maintenance_mode(cluster_ids=[cluster_topology.cluster_id]),
    )

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

    cluster_vars_dict = _prepare_cluster_vars(topology=cluster_topology, objects_information=basic_nodes).dict(
        by_alias=True, exclude_defaults=True
    )

    alternative_host_nodes = get_group_config_alternatives_for_hosts_in_cluster_groups(
        group_configs=group_configs.values(),
        cluster_vars=cluster_vars_dict,
        objects_before_upgrade=objects_before_upgrades,
        topology=cluster_topology,
    )

    return {
        "all": {
            "children": {
                group_name: {
                    "hosts": {
                        host_name: basic_nodes[ADCMCoreType.HOST, host_id].dict(by_alias=True, exclude_defaults=True)
                        | alternative_host_nodes.get(host_name, {})
                        for host_id, host_name in sorted(host_tuples, key=itemgetter(0))
                    }
                }
                for group_name, host_tuples in host_groups.items()
            },
            "vars": cluster_vars_dict,
        }
    }


def _get_inventory_for_action_from_hostprovider_bundle(object_: HostProvider | Host) -> dict:
    if isinstance(object_, HostProvider):
        hostprovider_id = object_.pk
        hosts_group = set(Host.objects.values_list("id", "fqdn").filter(provider=object_))
        group_name = "PROVIDER"
    else:
        hostprovider_id = int(object_.provider_id)
        hosts_group = {(object_.pk, object_.fqdn)}
        group_name = "HOST"

    objects_in_inventory = {
        ADCMCoreType.HOSTPROVIDER: {hostprovider_id},
        ADCMCoreType.HOST: set(map(itemgetter(0), hosts_group)),
    }

    group_configs = retrieve_group_configs_for_hosts(
        hosts=objects_in_inventory[ADCMCoreType.HOST], restrict_by_owner_type=[ADCMCoreType.HOSTPROVIDER]
    )

    objects_before_upgrades = get_before_upgrades(
        before_upgrades=extract_objects_before_upgrade(objects=objects_in_inventory),
        group_configs=group_configs.values(),
    )

    nodes_info = _get_objects_basic_info(
        objects_in_inventory=objects_in_inventory,
        objects_configuration=get_objects_configurations(objects_in_inventory),
        objects_before_upgrade=objects_before_upgrades,
        objects_maintenance_mode=MaintenanceModeOfObjects(services={}, components={}, hosts={}),
    )

    hostprovider_vars = {
        "provider": nodes_info[ADCMCoreType.HOSTPROVIDER, hostprovider_id].dict(by_alias=True, exclude_defaults=True)
    }

    alternative_host_nodes = get_group_config_alternatives_for_hosts_in_hostprovider_groups(
        group_configs=group_configs.values(),
        hostprovider_vars=hostprovider_vars,
        objects_before_upgrade=objects_before_upgrades,
    )

    return {
        "all": {
            "children": {
                group_name: {
                    "hosts": {
                        host_name: nodes_info[ADCMCoreType.HOST, host_id].dict(by_alias=True, exclude_defaults=True)
                        | alternative_host_nodes.get(host_name, {})
                        for host_id, host_name in sorted(hosts_group, key=itemgetter(0))
                    },
                }
            },
            "vars": hostprovider_vars,
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
        imports = get_imports_for_inventory(cluster_id=cluster_id)
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
                for service_info in Service.objects.values(
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
                for component_info in Component.objects.values(
                    *basic_fields, **basic_spec_fields, display_name=F("prototype__display_name")
                ).filter(id__in=components)
            }

    return result


def get_basic_info_for_hosts(hosts: set[HostID]) -> dict[HostID, HostNode]:
    objects_in_inventory = {ADCMCoreType.HOST: hosts}
    hosts_info = _get_objects_basic_info(
        objects_in_inventory=objects_in_inventory,
        objects_configuration=get_objects_configurations(objects_in_inventory),
        objects_before_upgrade={},
        objects_maintenance_mode=MaintenanceModeOfObjects(services={}, components={}, hosts={}),
    )

    return {host_id: host_node for (_, host_id), host_node in hosts_info.items()}
