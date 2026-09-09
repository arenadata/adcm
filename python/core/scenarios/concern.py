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
from dataclasses import dataclass
from typing import cast

from core.action import Job, Task
from core.action.job import JobRepoI, TaskUpdateDTO
from core.cluster import ClusterService
from core.concern.operations import (
    build_id_chain,
    build_task_concern,
    detect_concern_distribution,
    detect_hosts_concern_distribution,
)
from core.concern.repo import ConcernRepoI
from core.concern.types import ConcernRelatedObjects, ConcernTarget, ConcernType
from core.provider import ProviderService
from core.scenarios.status import StatusScenariosI
from core.types import (
    ADCMCoreType,
    ClusterID,
    ConcernID,
    CoreObjectDescriptor,
    ExtraActionTargetType,
    HostID,
    ProviderID,
)


@dataclass(slots=True)
class ConcernDistributionScenarios:
    provider_service: ProviderService
    cluster_service: ClusterService

    def detect_concern_distribution(
        self, *, owner: CoreObjectDescriptor, concern_type: ConcernType, cluster_id: ClusterID | None = None
    ) -> ConcernRelatedObjects:
        """
        Compute which objects a concern of `concern_type` owned by `owner` should be linked to, resolving whatever
        DB access is required (topology, provider hosts) for the owner's type.

        `cluster_id` must be supplied by the caller for SERVICE/COMPONENT/HOST owners — this scenario doesn't resolve
        it itself (e.g. via `ClusterService.retrieve_related_cluster_id`), that's the caller's job
        (`ConcernScenarios.create_job_concern` gets it for free from `task.owner.related_objects.cluster`).

        For HOST specifically, `None` is a legitimate value meaning "not in any cluster", not "not resolved yet" —
        the caller is trusted to have actually checked.

        PROVIDER is the one exception: a provider's hosts can span several clusters at once, so there's no single
        `cluster_id` a caller could sensibly supply for it.
        """
        match owner.type:
            case ADCMCoreType.ADCM:
                return {ADCMCoreType.ADCM: {owner.id}}

            case ADCMCoreType.PROVIDER:
                # PROVIDER never backtracks either (see `detect_concern_distribution`), so
                # `concern_type` doesn't apply here
                return self._detect_provider_concern_distribution(provider_id=owner.id)

            case ADCMCoreType.CLUSTER:
                topology = self.cluster_service.retrieve_topology(cluster_id=owner.id)
                return detect_concern_distribution(topology=topology, owner=owner, concern_type=concern_type)

            case ADCMCoreType.SERVICE | ADCMCoreType.COMPONENT:
                if cluster_id is None:
                    message = f"cluster_id is required to detect concern distribution for a {owner.type.value} owner"
                    raise ValueError(message)

                topology = self.cluster_service.retrieve_topology(cluster_id=cluster_id)
                return detect_concern_distribution(topology=topology, owner=owner, concern_type=concern_type)

            case ADCMCoreType.HOST:
                if cluster_id is None:
                    return {ADCMCoreType.HOST: {owner.id}}

                topology = self.cluster_service.retrieve_topology(cluster_id=cluster_id)
                return detect_hosts_concern_distribution(topology=topology, host_ids=[owner.id])

            case _:
                message = f"Concern distribution isn't implemented for {owner.type}"
                raise NotImplementedError(message)

    def _detect_provider_concern_distribution(self, *, provider_id: ProviderID) -> ConcernRelatedObjects:
        # a provider's hosts can be spread across several clusters (or none) at once, so this groups them by
        # cluster first and resolves each cluster's group in one pass, merging the results
        hosts = self.provider_service.retrieve_hosts_by_provider(provider_id=provider_id)

        host_ids_by_cluster: dict[ClusterID, set[HostID]] = defaultdict(set)
        unbound_host_ids: set[HostID] = set()
        for host in hosts:
            if host.cluster_id is None:
                unbound_host_ids.add(host.id)
            else:
                host_ids_by_cluster[host.cluster_id].add(host.id)

        topologies = self.cluster_service.retrieve_topologies(cluster_ids=host_ids_by_cluster)

        targets: ConcernRelatedObjects = defaultdict(set)
        targets[ADCMCoreType.PROVIDER].add(provider_id)
        targets[ADCMCoreType.HOST] |= unbound_host_ids

        for cluster_id, host_ids in host_ids_by_cluster.items():
            cluster_targets = detect_hosts_concern_distribution(topology=topologies[cluster_id], host_ids=host_ids)
            for core_type, ids in cluster_targets.items():
                targets[core_type] |= ids

        return targets


@dataclass(slots=True)
class ConcernScenarios:
    concern_repo: ConcernRepoI
    job_repo: JobRepoI
    status_scenarios: StatusScenariosI
    concern_distribution: ConcernDistributionScenarios

    def create_job_concern(self, *, task: Task, first_job: Job) -> ConcernID:
        if task.target is None:
            message = f"Task #{task.id} has no target, can't create concern"
            raise RuntimeError(message)

        if isinstance(task.target.type, ExtraActionTargetType):
            # action host groups aren't real concern owners — the object the group (and its action) belongs to
            # is the task's owner, no extra lookup needed
            if task.owner is None:
                message = f"Task #{task.id} targets an action host group but has no owner, can't create concern"
                raise RuntimeError(message)

            owner = task.owner
        else:
            owner = task.target

        # `owner.type` is always `ADCMCoreType`: `task.owner.type` is declared as such, and `task.target.type`
        # is narrowed by the `isinstance` check above in the `else` branch
        target = ConcernTarget(
            id=owner.id, type=cast(ADCMCoreType, owner.type), name=owner.name, id_chain=build_id_chain(task.selector)
        )
        draft = build_task_concern(task=task, job=first_job, target=target)

        # `task.owner` already carries the cluster the task is running against (`None` for a host that isn't
        # linked to one) via `related_objects`, straight from the DB — covers CLUSTER/SERVICE/COMPONENT owners
        # and both HOST cases (`host_action` and a plain host-level action) alike, so the distribution scenario
        # never needs to look it up again here
        cluster_id = (
            task.owner.related_objects.cluster.id if task.owner and task.owner.related_objects.cluster else None
        )

        related_objects = self.concern_distribution.detect_concern_distribution(
            owner=target.as_descriptor, concern_type=draft.type, cluster_id=cluster_id
        )

        concern_id = self.concern_repo.create(draft)
        self.concern_repo.link(concern_id=concern_id, targets=related_objects)

        if draft.type == ConcernType.LOCK:
            self.job_repo.update_task(id=task.id, data=TaskUpdateDTO(lock_id=concern_id))

        self.status_scenarios.notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

        return concern_id
