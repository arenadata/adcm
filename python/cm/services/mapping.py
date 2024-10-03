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

from typing import Iterable, Protocol

from core.bundle.types import BundleRestrictions
from core.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.cluster.types import ClusterTopology, HostComponentEntry, TopologyHostDiff
from core.types import ADCMCoreType, BundleID, ClusterID, CoreObjectDescriptor, HostID
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from rbac.models import Policy
from rest_framework.status import HTTP_409_CONFLICT

from cm.errors import AdcmEx
from cm.models import Cluster, ConcernCause, Host, HostComponent, MaintenanceMode, Service
from cm.services.action_host_group import ActionHostGroupRepo
from cm.services.bundle import retrieve_bundle_restrictions
from cm.services.cluster import retrieve_cluster_topology
from cm.services.concern import create_issue, delete_issue, retrieve_issue
from cm.services.concern.checks import (
    check_mapping_restrictions,
    check_service_requirements,
    cluster_mapping_has_issue,
)
from cm.services.concern.distribution import (
    AffectedObjectConcernMap,
    lock_objects,
    redistribute_issues_and_flags,
    unlock_objects,
)
from cm.services.concern.locks import retrieve_lock_on_object
from cm.services.config_host_group import ConfigHostGroupRepo
from cm.services.status.notify import reset_hc_map, reset_objects_in_mm
from cm.status_api import notify_about_redistributed_concerns_from_maps, send_host_component_map_update_event


class PerformMappingChecks(Protocol):
    def __call__(
        self, bundle_restrictions: BundleRestrictions, new_topology: ClusterTopology, host_difference: TopologyHostDiff
    ) -> None:
        ...


def check_nothing(
    bundle_restrictions: BundleRestrictions, new_topology: ClusterTopology, host_difference: TopologyHostDiff
) -> None:
    _ = bundle_restrictions, new_topology, host_difference


def check_only_mapping(
    bundle_restrictions: BundleRestrictions,
    new_topology: ClusterTopology,
    host_difference: TopologyHostDiff,
    error_template="{}",
) -> None:
    _ = host_difference
    check_mapping_restrictions(
        mapping_restrictions=bundle_restrictions.mapping, topology=new_topology, error_message_template=error_template
    )


def check_all(
    bundle_restrictions: BundleRestrictions, new_topology: ClusterTopology, host_difference: TopologyHostDiff
) -> None:
    check_service_requirements(services_restrictions=bundle_restrictions.service_requires, topology=new_topology)
    check_only_mapping(
        bundle_restrictions=bundle_restrictions, new_topology=new_topology, host_difference=host_difference
    )
    check_no_host_in_mm(host_difference.mapped.all)


def change_host_component_mapping(
    cluster_id: ClusterID,
    bundle_id: BundleID,
    flat_mapping: Iterable[HostComponentEntry],
    checks_func: PerformMappingChecks = check_all,
) -> ClusterTopology:
    # force remove duplicates
    new_mapping_entries = set(flat_mapping)

    with atomic():
        # prepare
        current_topology = retrieve_cluster_topology(cluster_id=cluster_id)
        new_topology = _construct_new_topology_or_raise_on_invalid_input(
            base_topology=current_topology, new_entries=new_mapping_entries
        )
        host_difference = find_hosts_difference(new_topology=new_topology, old_topology=current_topology)
        bundle_restrictions = retrieve_bundle_restrictions(bundle_id=bundle_id)

        # business checks

        checks_func(bundle_restrictions=bundle_restrictions, new_topology=new_topology, host_difference=host_difference)

        # save
        _recreate_mapping_in_db(topology=new_topology)

        # updates of related entities
        added, removed = _update_concerns(
            old_topology=current_topology, new_topology=new_topology, bundle_restrictions=bundle_restrictions
        )
        ActionHostGroupRepo().remove_unmapped_hosts_from_groups(host_difference.unmapped)
        ConfigHostGroupRepo().remove_unmapped_hosts_from_groups(host_difference.unmapped)
        _update_policies(topology=new_topology)

    # update info in statistics service
    reset_hc_map()
    reset_objects_in_mm()
    send_host_component_map_update_event(cluster_id=cluster_id)
    notify_about_redistributed_concerns_from_maps(added=added, removed=removed)

    return new_topology


def check_no_host_in_mm(hosts: Iterable[HostID]) -> None:
    if Host.objects.filter(id__in=hosts).exclude(maintenance_mode=MaintenanceMode.OFF).exists():
        raise AdcmEx("INVALID_HC_HOST_IN_MM")


def _construct_new_topology_or_raise_on_invalid_input(
    base_topology: ClusterTopology, new_entries: set[HostComponentEntry]
) -> ClusterTopology:
    cluster_id = base_topology.cluster_id

    unrelated_components = {entry.component_id for entry in new_entries}.difference(base_topology.component_ids)
    if unrelated_components:
        cluster_name = Cluster.objects.values_list("name", flat=True).get(id=cluster_id)
        ids_repr = ", ".join(f'"{component_id}"' for component_id in unrelated_components)
        raise AdcmEx(
            code="COMPONENT_NOT_FOUND",
            http_code=HTTP_409_CONFLICT,
            msg=f'Component(s) {ids_repr} do not belong to cluster "{cluster_name}"',
        ) from None

    unbound_hosts = {entry.host_id for entry in new_entries}.difference(base_topology.hosts)
    if unbound_hosts:
        cluster_name = Cluster.objects.values_list("name", flat=True).get(id=cluster_id)
        ids_repr = ", ".join(f'"{host_id}"' for host_id in sorted(unbound_hosts))
        raise AdcmEx(
            code="HOST_NOT_FOUND",
            http_code=HTTP_409_CONFLICT,
            msg=f'Host(s) {ids_repr} do not belong to cluster "{cluster_name}"',
        )

    return create_topology_with_new_mapping(topology=base_topology, new_mapping=new_entries)


def _recreate_mapping_in_db(topology: ClusterTopology) -> None:
    cluster_id = topology.cluster_id
    HostComponent.objects.filter(cluster_id=cluster_id).delete()
    HostComponent.objects.bulk_create(
        (
            HostComponent(cluster_id=cluster_id, service_id=service_id, component_id=component_id, host_id=host_id)
            for service_id, service in topology.services.items()
            for component_id, component in service.components.items()
            for host_id in component.hosts
        )
    )


def _update_concerns(
    old_topology: ClusterTopology, new_topology: ClusterTopology, bundle_restrictions: BundleRestrictions
) -> tuple[AffectedObjectConcernMap, AffectedObjectConcernMap]:
    # todo HC may break (?)
    #  We can't be sure this method is called after some sort of "check"
    cluster = CoreObjectDescriptor(id=old_topology.cluster_id, type=ADCMCoreType.CLUSTER)
    if not cluster_mapping_has_issue(cluster_id=cluster.id, bundle_restrictions=bundle_restrictions):
        delete_issue(owner=cluster, cause=ConcernCause.HOSTCOMPONENT)
    elif retrieve_issue(owner=cluster, cause=ConcernCause.HOSTCOMPONENT) is None:
        create_issue(owner=cluster, cause=ConcernCause.HOSTCOMPONENT)

    added, removed = redistribute_issues_and_flags(topology=new_topology)

    lock = retrieve_lock_on_object(object_=cluster)
    if lock:
        # Here we want to add locks on hosts that weren't mapped before, but are mapped now.
        # And remove from those that aren't mapped to any component anymore.
        unmapped_in_previous_topology = old_topology.unmapped_hosts
        unmapped_in_new_topology = new_topology.unmapped_hosts

        unmapped = unmapped_in_new_topology - unmapped_in_previous_topology
        if unmapped:
            unlock_objects(
                targets=(CoreObjectDescriptor(id=host_id, type=ADCMCoreType.HOST) for host_id in unmapped),
                lock_id=lock.id,
            )

        mapped = unmapped_in_previous_topology - unmapped_in_new_topology
        if mapped:
            lock_objects(
                targets=(CoreObjectDescriptor(id=host_id, type=ADCMCoreType.HOST) for host_id in mapped),
                lock_id=lock.id,
            )

    # since mechanism for locks redistribution is different from the one for flags/issues,
    # there's no need in considering them in concern update events
    return added, removed


def _update_policies(topology: ClusterTopology) -> None:
    service_content_type = ContentType.objects.get_for_model(model=Service)
    for policy in Policy.objects.filter(
        object__object_id__in=topology.services.keys(), object__content_type=service_content_type
    ):
        policy.apply()

    for policy in Policy.objects.filter(
        object__object_id=topology.cluster_id,
        object__content_type=ContentType.objects.get_for_model(model=Cluster),
    ):
        policy.apply()
