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

from cm.errors import AdcmEx
from cm.legacy.services.action_process.types import ProcessStepState
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.job.run.executors import InternalScriptResult
from cm.legacy.services.mapping import change_host_component_mapping_no_lock, check_nothing, lock_cluster_mapping
from cm.models import Process, ProcessStep, Prototype
from core.action import AssociatedProcess, HcAclRule, Task, TaskMappingDelta
from core.action.types import HcApplyScript, RichJob
from core.cluster import ClusterService
from core.types import ADCMCoreType, ClusterID, ComponentNameKey
from django.db.models import Q
from django.db.transaction import atomic

from use_cases.internal_scripts.common import build_result_message


@dataclass(slots=True)
class HcApplyInternalScript:
    cluster_service: ClusterService

    def do(self, task: Task, job: RichJob) -> InternalScriptResult:
        owner = task.owner
        if owner is None:
            raise RuntimeError("Task owner: was given None, expected an object")

        if owner.type not in {ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
            raise AdcmEx(
                code="WRONG_OWNER",
                msg="Internal script `hc_apply` can only be defined in cluster, service or component context`",
            )

        script = job.spec.script
        if not isinstance(script, HcApplyScript):
            message = f"Job script: was given {type(script).__name__}, expected {HcApplyScript.__name__}"
            raise RuntimeError(message)  # noqa: TRY004

        params = script.params
        hc_apply_rules = params.rules if params else None

        if not hc_apply_rules:
            hc_apply_rules = task.action.hc_acl

        if owner.type == ADCMCoreType.CLUSTER:
            cluster_id = owner.id
            cluster_prototype_id = owner.prototype_id
        else:
            cluster = owner.related_objects.cluster
            if cluster is None:
                raise RuntimeError("Task owner's cluster: was given None, expected an object")

            cluster_id = cluster.id
            cluster_prototype_id = cluster.prototype_id

        bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=cluster_prototype_id)

        with_updates = False
        with atomic():
            lock_cluster_mapping(cluster_id=cluster_id)

            if (
                isinstance(task.action_process, AssociatedProcess)
                and (process := Process.objects.filter(id=task.action_process.id).first()) is not None
            ):
                mapping_delta = _extract_hc_apply_delta_for_process(process)
                #  hc rule for process are validated during step submissions hence cumulative delta is valid
                delta_part = mapping_delta
            else:
                mapping_delta = task.hostcomponent.mapping_delta
                if mapping_delta is None:
                    mapping_delta = TaskMappingDelta(add={}, remove={})

                delta_part = _extract_mapping_delta_part(
                    cluster_id=cluster_id, mapping_delta=mapping_delta, hc_apply_rules=hc_apply_rules
                )

            with_updates = not delta_part.is_empty
            if with_updates:
                change_host_component_mapping_no_lock(
                    cluster_id=cluster_id,
                    bundle_id=bundle_id,
                    mapping_delta=delta_part,
                    cluster_service=self.cluster_service,
                    checks_func=check_nothing,
                )

        result_message = build_result_message(
            script_name="hc_apply",
            full_complete_message="the component mapping is complete",
            without_updates_message="the component mapping was done",
            with_updates=with_updates,
        )
        return InternalScriptResult(code=0, message=result_message)


def _extract_hc_apply_delta_for_process(process: Process) -> TaskMappingDelta:
    last_mapping_step = (
        ProcessStep.objects.filter(process=process, state=ProcessStepState.COMPLETED)
        .exclude(Q(processstepinput__mapping__isnull=True) | Q(processstepinput__mapping={}))
        .order_by("-id")
        .first()
    )

    if not last_mapping_step:
        return TaskMappingDelta(add={}, remove={})

    cumulative_delta = last_mapping_step.processstepinput.mapping["cumulative_delta"]  # pyright: ignore[reportAttributeAccessIssue]

    add_mapping: dict[int, set[int]] = {}
    for entry in cumulative_delta.get("add", []):
        add_mapping.setdefault(entry["component_id"], set()).add(entry["host_id"])

    remove_mapping: dict[int, set[int]] = {}
    for entry in cumulative_delta.get("remove", []):
        remove_mapping.setdefault(entry["component_id"], set()).add(entry["host_id"])

    return TaskMappingDelta(add=add_mapping, remove=remove_mapping)


def _extract_mapping_delta_part(
    cluster_id: ClusterID, mapping_delta: TaskMappingDelta, hc_apply_rules: list[HcAclRule]
) -> TaskMappingDelta:
    topology = retrieve_cluster_topology(cluster_id=cluster_id)
    components_map = topology.component_full_name_id_mapping

    delta_data = defaultdict(lambda: defaultdict(set))
    for hc_rule in hc_apply_rules:
        component_id = components_map.get(ComponentNameKey(service=hc_rule.service, component=hc_rule.component))
        if component_id is None:
            continue
        delta_data[hc_rule.action][component_id].update(
            getattr(mapping_delta, hc_rule.action, {}).get(component_id, ())
        )

    return TaskMappingDelta(**delta_data)
