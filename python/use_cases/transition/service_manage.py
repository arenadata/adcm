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

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import NamedTuple, cast

from cm.errors import AdcmEx
from cm.legacy.services.job._utils import construct_delta_for_task
from cm.legacy.services.job.run._config import create_related_configs
from cm.legacy.services.mapping import (
    change_host_component_mapping_no_lock,
    check_for_action_mapping,
    lock_cluster_mapping,
)
from cm.models import Cluster, ObjectType, Prototype, Service
from core.action import ServiceManageServiceEntry
from core.cluster import ClusterService
from core.legacy.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.legacy.cluster.types import ClusterTopology, HostComponentEntry
from core.legacy.job.types import TaskMappingDelta, TaskOwner
from core.types import BundleID, ClusterID, JobID, PrototypeID
from django.db.transaction import atomic

from use_cases.transition.cluster.create import CreateServicesFromPrototypes
from use_cases.transition.config import UpdateConfigurationFromJob, apply_config_changes


class ServiceManageOutcome(NamedTuple):
    added_services: tuple[str, ...]
    configs_changed: bool
    mapping_changed: bool

    @property
    def with_updates(self) -> bool:
        return bool(self.added_services) or self.configs_changed or self.mapping_changed


@dataclass(slots=True)
class ManageClusterServices:
    add_services: CreateServicesFromPrototypes
    update_configuration_from_job: UpdateConfigurationFromJob
    cluster_service: ClusterService

    def add(
        self,
        *,
        cluster_id: ClusterID,
        entries: Sequence[ServiceManageServiceEntry],
        job_id: JobID,
        task_owner: TaskOwner,
        changes_description: str,
    ) -> ServiceManageOutcome:
        # TODO: remove cast when `core.legacy.cluster.types.ClusterTopology`
        #  and `core.cluster._types.ClusterTopology` are united
        topology = cast(ClusterTopology, self.cluster_service.retrieve_topology(cluster_id=cluster_id))
        present_services = {service.info.name for service in topology.services.values()}
        names_to_add = [entry.name for entry in entries if entry.name not in present_services]
        mapping_is_requested = any(entry.hc_changes for entry in entries)

        configs_changed = False
        mapping_changed = False
        with atomic():
            if mapping_is_requested:
                lock_cluster_mapping(cluster_id=cluster_id)

            if names_to_add:
                cluster, bundle_id = _retrieve_cluster_with_bundle(cluster_id=cluster_id)
                self.add_services.do(
                    cluster=cluster, prototype_ids=_resolve_service_prototypes(bundle_id, names_to_add)
                )
                # Services and components are created while the job is running,
                # so job's related configs should be updated for new objects to be configurable below.
                create_related_configs(job_id=job_id, owner=task_owner)
                topology = cast(ClusterTopology, self.cluster_service.retrieve_topology(cluster_id=cluster_id))
            else:
                _, bundle_id = _retrieve_cluster_with_bundle(cluster_id=cluster_id)

            services_by_name = _retrieve_services_by_name(
                cluster_id=cluster_id, names=[entry.name for entry in entries]
            )
            for entry in entries:
                if not entry.config_changes:
                    continue

                has_changed = apply_config_changes(
                    job_id=job_id,
                    db_object=services_by_name[entry.name],
                    parameters=[change.model_dump() for change in entry.config_changes],
                    changes_description=changes_description,
                    update_configuration_from_job=self.update_configuration_from_job,
                )
                configs_changed = configs_changed or has_changed

            mapping_delta = _build_mapping_delta(topology=topology, entries=entries)
            if not mapping_delta.is_empty:
                change_host_component_mapping_no_lock(
                    cluster_id=cluster_id,
                    bundle_id=bundle_id,
                    mapping_delta=mapping_delta,
                    cluster_service=self.cluster_service,
                    checks_func=check_for_action_mapping,
                )
                mapping_changed = True

        return ServiceManageOutcome(
            added_services=tuple(names_to_add), configs_changed=configs_changed, mapping_changed=mapping_changed
        )


def _build_mapping_delta(topology: ClusterTopology, entries: Sequence[ServiceManageServiceEntry]) -> TaskMappingDelta:
    requested_entries = _resolve_requested_mapping_entries(topology=topology, entries=entries)
    if not requested_entries:
        return TaskMappingDelta()

    current_entries = {
        HostComponentEntry(host_id=host_id, component_id=component_id)
        for service in topology.services.values()
        for component_id, component in service.components.items()
        for host_id in component.hosts
    }

    new_topology = create_topology_with_new_mapping(topology=topology, new_mapping=current_entries | requested_entries)
    host_difference = find_hosts_difference(new_topology=new_topology, old_topology=topology)

    return construct_delta_for_task(host_difference=host_difference)


def _resolve_requested_mapping_entries(
    topology: ClusterTopology, entries: Sequence[ServiceManageServiceEntry]
) -> set[HostComponentEntry]:
    services_by_name = {service.info.name: service for service in topology.services.values()}
    host_id_by_name = {host.name: host_id for host_id, host in topology.hosts.items()}

    requested_entries = set()
    for entry in entries:
        if not entry.hc_changes:
            continue

        service_topology = services_by_name.get(entry.name)
        if service_topology is None:
            raise AdcmEx(
                code="SERVICE_NOT_FOUND",
                msg=f'Service "{entry.name}" not found in cluster mapping',
            )

        component_id_by_name = {
            component.info.name: component_id for component_id, component in service_topology.components.items()
        }
        for change in entry.hc_changes:
            component_id = component_id_by_name.get(change.component)
            if component_id is None:
                raise AdcmEx(
                    code="COMPONENT_NOT_FOUND",
                    msg=f'Component "{change.component}" not found in service "{entry.name}"',
                )

            if missing_hosts := set(change.hosts) - set(host_id_by_name):
                raise AdcmEx(
                    code="HOST_NOT_FOUND",
                    msg=f"Host(s) {', '.join(sorted(missing_hosts))} not found in cluster",
                )

            requested_entries.update(
                HostComponentEntry(host_id=host_id_by_name[host_name], component_id=component_id)
                for host_name in change.hosts
            )

    return requested_entries


def _retrieve_cluster_with_bundle(cluster_id: ClusterID) -> tuple[Cluster, BundleID]:
    cluster = Cluster.objects.select_related("prototype").get(id=cluster_id)
    return cluster, cluster.prototype.bundle_id


def _resolve_service_prototypes(bundle_id: BundleID, names: Collection[str]) -> tuple[PrototypeID, ...]:
    prototype_name_id_map = dict(
        Prototype.objects.values_list("name", "id").filter(bundle_id=bundle_id, type=ObjectType.SERVICE, name__in=names)
    )
    if missing_prototypes := set(names) - set(prototype_name_id_map):
        raise AdcmEx(
            code="PROTOTYPE_NOT_FOUND",
            msg=f"Failed to locate service prototype(s) in cluster's bundle: {', '.join(sorted(missing_prototypes))}",
        )

    return tuple(prototype_name_id_map.values())


def _retrieve_services_by_name(cluster_id: ClusterID, names: Collection[str]) -> dict[str, Service]:
    return {
        service.prototype.name: service
        for service in Service.objects.select_related("prototype").filter(
            cluster_id=cluster_id, prototype__name__in=names
        )
    }
