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

# Shortened version of `cm.legacy.services.concern.messages`, covering only what's required
# to build a lock/flag concern for a task. Should be extended (or the full templating
# machinery ported here) as more concern kinds are handled by core.

from collections import defaultdict
from collections.abc import Iterable

from core.action import Job, Task
from core.cluster import ClusterTopology
from core.concern.types import ConcernCause, ConcernDraft, ConcernRelatedObjects, ConcernTarget, ConcernType
from core.constants import ADCM_DELETE_SERVICE_ACTION_NAME
from core.types import ADCMCoreType, CoreObjectDescriptor, HostID, TaskID


def detect_hosts_concern_distribution(topology: ClusterTopology, host_ids: Iterable[HostID]) -> ConcernRelatedObjects:
    """
    Compute which cluster/service/component objects are touched by the given hosts, based purely on the
    cluster's topology (no DB access) — one pass over the topology regardless of how many hosts are given.
    This is the building block both for a HOST-owned concern (a single host) and for the LOCK/ISSUE backtrack
    in `detect_concern_distribution` (the owner's own hosts).
    """
    host_ids = set(host_ids)
    targets: ConcernRelatedObjects = defaultdict(set)
    targets[ADCMCoreType.HOST] |= host_ids

    for service_id, service in topology.services.items():
        for component_id, component in service.components.items():
            if not host_ids.isdisjoint(component.hosts):
                targets[ADCMCoreType.CLUSTER].add(topology.cluster_id)
                targets[ADCMCoreType.SERVICE].add(service_id)
                targets[ADCMCoreType.COMPONENT].add(component_id)

    return targets


def detect_concern_distribution(
    topology: ClusterTopology, owner: CoreObjectDescriptor, concern_type: ConcernType
) -> ConcernRelatedObjects:
    """
    Compute which objects a concern of `concern_type` owned by `owner` should be linked to, based purely on the
    cluster's topology (no DB access).

    CLUSTER/SERVICE/COMPONENT owners only; HOST is a degenerate single-element case of
    `detect_hosts_concern_distribution` instead, and PROVIDER is handled at the scenario level (its hosts may
    span several clusters at once).
    """
    targets: ConcernRelatedObjects = defaultdict(set)
    targets[owner.type].add(owner.id)

    match owner.type:
        case ADCMCoreType.CLUSTER:
            for service in topology.services.values():
                targets[ADCMCoreType.SERVICE].add(service.info.id)
                targets[ADCMCoreType.COMPONENT].update(service.components)
                targets[ADCMCoreType.HOST].update(service.host_ids)

        case ADCMCoreType.SERVICE:
            targets[ADCMCoreType.CLUSTER].add(topology.cluster_id)
            service = topology.services[owner.id]
            targets[ADCMCoreType.COMPONENT].update(service.components)
            targets[ADCMCoreType.HOST].update(service.host_ids)

        case ADCMCoreType.COMPONENT:
            targets[ADCMCoreType.CLUSTER].add(topology.cluster_id)
            service_node = topology.get_service_by_component(owner.id)
            targets[ADCMCoreType.SERVICE].add(service_node.info.id)
            targets[ADCMCoreType.HOST].update(service_node.components[owner.id].hosts)

        case _:
            message = f"Concern distribution by topology isn't implemented for {owner.type}"
            raise NotImplementedError(message)

    # LOCK/ISSUE carry "blocking" meaning (even a non-blocking issue still says "something here isn't right
    # yet"), so they need to backtrack onto whatever actually shares infrastructure with the owner — a sibling
    # service/component sitting on the same host is affected too, even though it isn't in the owner's own
    # hierarchy.
    #
    # FLAG is purely informational and stays exactly where it was raised, so it's excluded here. This is keyed
    # on concern *type*, not `blocking`, as a deliberate business decision (a FLAG can be non-blocking yet
    # still shouldn't backtrack).
    #
    # Only SERVICE/COMPONENT owners can backtrack this way: a CLUSTER-owned concern already covers every host
    # in the cluster, and HOST/PROVIDER have nothing "below" them to widen into.
    if owner.type in (ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT) and concern_type in (
        ConcernType.LOCK,
        ConcernType.ISSUE,
    ):
        widened = detect_hosts_concern_distribution(topology=topology, host_ids=targets[ADCMCoreType.HOST])
        for core_type, ids in widened.items():
            targets[core_type] |= ids

    return targets


def build_id_chain(selector: dict) -> dict:
    """
    Reshape `Task.selector` (`{type: {"id": ..., "name": ...}}`) into the `{type}_id: id` format expected by
    front-end URL generation in message placeholders — same underlying ancestry data, no extra DB lookup needed.
    """
    return {f"{type_name}_id": info["id"] for type_name, info in selector.items()}


def build_task_concern(task: Task, job: Job, target: ConcernTarget) -> ConcernDraft:
    if task.is_blocking:
        name = (
            task.name
            if task.name == ADCM_DELETE_SERVICE_ACTION_NAME
            else f"{ConcernCause.JOB.value}_{ConcernType.LOCK.value}"
        )
        reason = {
            "message": "Object was locked by running job ${job} on ${target}",
            "placeholder": {"job": _job_placeholder(task.id, job), "target": _target_placeholder(target)},
        }

        return ConcernDraft(
            type=ConcernType.LOCK,
            cause=ConcernCause.JOB,
            name=name,
            reason=reason,
            blocking=True,
            owner=target.as_descriptor,
        )

    name = f"adcm_running_job_{task.name}"
    reason = {
        "message": "${source} has a flag: running job ${job}",
        "placeholder": {"job": _job_placeholder(task.id, job), "source": _target_placeholder(target)},
    }

    return ConcernDraft(
        type=ConcernType.FLAG,
        cause=ConcernCause.JOB,
        name=name,
        reason=reason,
        blocking=False,
        owner=target.as_descriptor,
    )


def _job_placeholder(task_id: TaskID, job: Job) -> dict:
    return {
        "type": "job",
        "name": job.display_name or job.name,
        "params": {"task_id": task_id},
    }


def _target_placeholder(target: ConcernTarget) -> dict:
    return {"type": target.type.value, "name": target.name, "params": target.id_chain}
