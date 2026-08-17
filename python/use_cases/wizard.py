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

from dataclasses import dataclass
from typing import cast
from uuid import UUID

from cm.legacy.services import mapping
from cm.legacy.services.action_process.errors import ActionProcessOperationError, ActionProcessPayloadError
from cm.legacy.services.action_process.operations import (
    MappingRules,
    OperationContext,
    OperationPayload,
    convert_db_errors,
    find_hc_operation_distribution_violations,
    find_mapping_delta_objects_existence_violations,
    get_new_flat_mapping_from_delta_and_topology,
)
from cm.legacy.services.action_process.schema_validation import (
    ProcessOperationType,
    SubmitConfigurationStepParams,
    SubmitMappingStepParams,
    SubmitOperationStepParams,
    SubmitStepPayload,
)
from cm.legacy.services.action_process.types import ProcessContext, ProcessStepState, ProcessTarget
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.bundle_alt.errors import convert_bundle_errors_to_adcm_ex
from cm.legacy.services.bundle_alt.render import ActionArgs, TaskArgs
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern.flags import BuiltInFlag, lower_flag, raise_flag_for_process, update_hierarchy_for_flag
from cm.legacy.services.job.action import check_no_blocking_concerns
from cm.models import Cluster, TaskLog
from cm.transition.status import StatusScenarios
from core.action import CallingProcess
from core.action.job import JobService
from core.dynamic_bundle.render import BundleRenderer
from core.legacy.cluster.operations import create_topology_with_new_mapping, find_hosts_difference
from core.legacy.cluster.types import ClusterTopology
from core.scenarios.wizard import FillWizardStepSpec
from core.types import (
    ActionID,
    ActionProcessID,
    ActionProcessStepID,
    ComponentNameKey,
    CoreObjectDescriptor,
    HostGroupDescriptor,
)
from django.db.transaction import atomic
from django.utils import timezone
from rbac.scenarios import RBACScenarios
import core

from use_cases.dto import InputConfigConverter
from use_cases.transition.job.schedule import TaskStarter


@dataclass(slots=True, frozen=True)
class SubmitProcessDTO:
    process_id: ActionProcessID
    new_sync_key: UUID


@dataclass(slots=True, frozen=True)
class SubmitActionDTO:
    owner: CoreObjectDescriptor
    target: CoreObjectDescriptor | HostGroupDescriptor
    action_id: ActionID
    action_name: str
    action_display_name: str


@dataclass(slots=True)
class InitiateWizardProcess:
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs]
    bundle_service: core.bundle.BundleService
    wizard_repo: core.action.wizard.WizardRepoI
    wizard_service: core.action.wizard.WizardService
    fill_wizard_step_spec: FillWizardStepSpec[ActionArgs, TaskArgs]
    status_scenarios: StatusScenarios

    @atomic
    @convert_bundle_errors_to_adcm_ex
    def do(self, process_context: ProcessContext) -> ActionProcessID:
        cluster_relative_object_orm = process_context.cluster_relative_object()
        cluster_relative_object_cod = process_context.cluster_relative_object(as_descriptor=True)

        check_no_blocking_concerns(
            lock_owner=cluster_relative_object_orm,
            action_name=process_context.action.name,
        )

        action_args = process_context.build_action_args(process_id=None)
        bundle_context = self.bundle_service.retrieve_bundle_context_from_prototype(
            prototype_id=process_context.action.owner_prototype.id
        )
        if process_context.action.wizard_template is None:
            message = f"Wizard template is unexpectedly missing for action #{process_context.action.id}"
            raise RuntimeError(message)

        stages = self.bundle_renderer.render_wizard_stages(
            template=process_context.action.wizard_template,
            bundle_context=bundle_context,
            args=action_args,
        )

        process_id, current_step_id = self.wizard_service.initiate_process(
            target=process_context.target,
            owner=process_context.owner,
            action_id=process_context.action.id,
            stages=stages,
        )

        first_step = stages[0].steps[0]

        self.fill_wizard_step_spec.do(
            step_id=current_step_id,
            step_type=first_step.type,
            template=first_step.template,
            bundle_context=bundle_context,
            owner=process_context.owner,
            action_args=process_context.build_action_args(process_id=process_id),
            action_allow_to_terminate=process_context.action_orm.allow_to_terminate,
        )

        flag = BuiltInFlag.ACTION_PROCESS_RUNNING.value
        changed = raise_flag_for_process(
            flag=flag,
            on_objects=[cluster_relative_object_cod],
            action=process_context.action_orm,
            action_owner=cluster_relative_object_orm,
        )

        if changed:
            added = update_hierarchy_for_flag(flag=flag, on_objects=[cluster_relative_object_cod])
            self.status_scenarios.notify_about_redistributed_concerns_from_maps(added=added, removed={})

        return process_id


@dataclass(slots=True)
class PerformWizardProcessOperation:
    wizard_repo: core.action.wizard.WizardRepoI

    config_service: core.config.ConfigService
    job_service: JobService
    wizard_service: core.action.wizard.WizardService
    bundle_service: core.bundle.BundleService

    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs]
    fill_wizard_step_spec: FillWizardStepSpec[ActionArgs, TaskArgs]
    start_task: TaskStarter
    rbac_scenarios: RBACScenarios
    available_contract_versions: core.bundle.AvailableContractVersions

    @convert_db_errors
    @convert_bundle_errors_to_adcm_ex
    @atomic
    def do(
        self,
        *,
        process_id: ActionProcessID,
        payload: OperationPayload,
        context: OperationContext,
    ) -> None:
        process = self.wizard_repo.retrieve_process(process_id=process_id)
        if process.sync_key != payload.params.process_sync_key:
            message = f"Can't find Process #{process.id} ({str(payload.params.process_sync_key)})"
            raise core.action.wizard.SyncKeyMismatchError(message)

        new_process_sync_key = core.action.wizard.operations.get_new_process_sync_key()

        bundle_context = self.bundle_service.retrieve_bundle_context_from_prototype(
            prototype_id=context.process_context.action.owner_prototype.id
        )

        match payload.method:
            case ProcessOperationType.SUBMIT:
                steps = tuple(self.wizard_repo.retrieve_steps(process_id=process.id))

                step = core.action.wizard.operations.get_step_by_id(steps=steps, step_id=payload.params.step_id)
                if step.state in (ProcessStepState.RUNNING, ProcessStepState.BROKEN):
                    raise core.action.wizard.ActionProcessOperationError(f"The {step.state} step can't be submitted")

                current_step_id, _ = core.action.wizard.operations.find_current_and_last_completed_steps(steps=steps)
                if payload.params.step_id != current_step_id:
                    raise core.action.wizard.ActionProcessOperationError("Only current step can be submitted")

                step_spec = step.spec
                if not step_spec:
                    message = f"Step spec is unexpectedly missing: {step=}"
                    raise RuntimeError(message)

                current_id = self._submit_step(
                    payload=cast(SubmitStepPayload, payload),
                    process=SubmitProcessDTO(process_id=process.id, new_sync_key=new_process_sync_key),
                    action=SubmitActionDTO(
                        owner=context.process_context.owner,
                        target=context.process_context.target.as_core_or_group_descriptor,
                        action_id=context.process_context.action.id,
                        action_name=context.process_context.action.name,
                        action_display_name=context.process_context.action_orm.display_name,
                    ),
                    target=context.process_context.target_orm,
                    step=self._to_typed_submit_step(step=step, spec=step_spec),
                    config_processor=context.config_processor,
                )
                if current_id:
                    step = self.wizard_repo.retrieve_step(process_id=process.id, step_id=current_id)
                    template = core.action.wizard.operations.find_step_spec_declaration(
                        step=step, process_flow_spec=process.flow_spec
                    ).template
                    self.fill_wizard_step_spec.do(
                        step_id=current_id,
                        step_type=step.type,
                        template=template,
                        bundle_context=bundle_context,
                        owner=context.process_context.owner,
                        action_args=context.process_context.build_action_args(process_id=process.id),
                        action_allow_to_terminate=context.process_context.action_orm.allow_to_terminate,
                    )

            case ProcessOperationType.RESET:
                step = self.wizard_repo.retrieve_step(process_id=process.id, step_id=payload.params.step_id)
                self.wizard_service.reset_step(process_id=process.id, step_id=payload.params.step_id)

                template = core.action.wizard.operations.find_step_spec_declaration(
                    step=step, process_flow_spec=process.flow_spec
                ).template
                self.fill_wizard_step_spec.do(
                    step_id=step.id,
                    step_type=step.type,
                    template=template,
                    bundle_context=bundle_context,
                    owner=context.process_context.owner,
                    action_args=context.process_context.build_action_args(process_id=process.id),
                    action_allow_to_terminate=context.process_context.action_orm.allow_to_terminate,
                )

            case ProcessOperationType.COMPLETE:
                self.wizard_service.complete_process(process=process)
                lower_flag(
                    BuiltInFlag.ACTION_PROCESS_RUNNING.value.name,
                    on_objects=[context.process_context.cluster_relative_object(as_descriptor=True)],
                )

            case ProcessOperationType.SKIP:
                current_id = self.wizard_service.skip_step(process_id=process.id, step_id=payload.params.step_id)
                if current_id:
                    step = self.wizard_repo.retrieve_step(process_id=process.id, step_id=current_id)
                    template = core.action.wizard.operations.find_step_spec_declaration(
                        step=step, process_flow_spec=process.flow_spec
                    ).template
                    self.fill_wizard_step_spec.do(
                        step_id=current_id,
                        step_type=step.type,
                        template=template,
                        bundle_context=bundle_context,
                        owner=context.process_context.owner,
                        action_args=context.process_context.build_action_args(process_id=process.id),
                        action_allow_to_terminate=context.process_context.action_orm.allow_to_terminate,
                    )

        self.wizard_service.update_process_sync_key(
            process_id=process_id,
            sync_key=payload.params.process_sync_key,
            new_sync_key=new_process_sync_key,
        )

    # Temporary extraction to keep `do` smaller; should become a dedicated scenario.
    def _submit_step(
        self,
        *,
        payload: SubmitStepPayload,
        process: SubmitProcessDTO,
        action: SubmitActionDTO,
        target: ProcessTarget,
        step: core.action.wizard.Step,
        # typehint is vague, because isolation is a bit broken and API-related stuff is coming in here
        config_processor: InputConfigConverter[object],
    ) -> ActionProcessStepID | None:
        msg_wrong_payload = f"Wrong params for {step.type} step"

        match step.type:
            case core.action.wizard.StepType.CONFIGURATION:
                if not isinstance(payload.params, SubmitConfigurationStepParams):
                    raise ActionProcessPayloadError(msg_wrong_payload)

                step_spec = step.spec
                if step_spec is None:
                    message = f"Step spec is unexpectedly missing: {step=}"
                    raise RuntimeError(message)
                specification = step_spec[0]

                try:
                    target_config = self.config_service.retrieve_current_configuration(owner=action.owner)
                except core.config.ObjectWithoutConfigError:
                    target_config = None

                configuration = config_processor(payload.params.configuration, specification)
                step_configuration = self.config_service.prepare_action_configuration(
                    configuration=configuration,
                    specification=specification,
                    owner=action.owner,
                    owner_configuration=target_config,
                )
                prefix = core.config.files.build_action_process_step_prefix(
                    process_id=process.process_id, step_id=step.id
                )
                self.config_service.prepare_file_parameter_values_on_fs(
                    configuration=step_configuration,
                    specification=specification,
                    owner_prefix=prefix,
                )

                step_input_data = core.action.wizard.StepInputDTO(
                    configuration=step_configuration, created_at=timezone.now()
                )
                self.wizard_repo.upsert_step_input(step_id=step.id, data=step_input_data)

                self.wizard_service.revoke_next_steps(process_id=process.process_id, step_id=step.id)
                return self.wizard_service.complete_step(process_id=process.process_id, step_id=step.id)

            case core.action.wizard.StepType.OPERATION:
                if not isinstance(payload.params, SubmitOperationStepParams):
                    raise ActionProcessPayloadError(msg_wrong_payload)

                step_spec = step.spec
                if step_spec is None:
                    message = f"Step spec is unexpectedly missing: {step=}"
                    raise RuntimeError(message)

                if isinstance(target, Cluster) and core.action.operations.has_bundle_revert_script(step_spec):
                    previous_bundle_cv = self.bundle_renderer.bundle_service.retrieve_before_upgrade_contract_version(
                        before_upgrade_data=target.before_upgrade
                    )
                    if previous_bundle_cv and not core.bundle.is_contract_version_supported(
                        current_version=previous_bundle_cv,
                        available_contract_versions=self.available_contract_versions,
                    ):
                        raise ActionProcessOperationError(
                            f"Execution of step {action.action_display_name or action.action_name} is not allowed. "
                            "The bundle for revert is unsupported"
                        )

                task_display_name = f"{action.action_display_name} ({step.extra.display_name})"
                task_extra = core.action.job.TaskExtraInfo(
                    name=action.action_name,
                    display_name=task_display_name,
                    description="",
                )
                task_payload = core.action.job.TaskCreateDTO(
                    owner=action.owner,
                    target=action.target,
                    action_id=action.action_id,
                    extra=task_extra,
                    process=CallingProcess(
                        id=process.process_id, sync_key=process.new_sync_key, step_id=payload.params.step_id
                    ),
                )

                task_id = self.job_service.create_task(payload=task_payload)
                scripts = tuple(step_spec)
                self.job_service.create_jobs(task_id=task_id, scripts=scripts)

                step_input_data = core.action.wizard.StepInputDTO(job_id=task_id, created_at=timezone.now())
                self.wizard_repo.upsert_step_input(step_id=payload.params.step_id, data=step_input_data)
                self.wizard_repo.update_step(
                    step_id=payload.params.step_id,
                    data=core.action.wizard.StepUpdateDTO(state=core.action.wizard.ProcessStepState.RUNNING),
                )

                self.wizard_service.revoke_next_steps(process_id=process.process_id, step_id=payload.params.step_id)

                # todo write pid to task (executor)
                # todo actually should use starter to avoid hardcoding
                task_orm = TaskLog.objects.get(id=task_id)

                self.rbac_scenarios.re_apply_policy_for_jobs(task=task_orm)

                self.start_task(task_orm)
                return None

            case core.action.wizard.StepType.MAPPING:
                if not isinstance(payload.params, SubmitMappingStepParams):
                    raise ActionProcessPayloadError(msg_wrong_payload)

                step_spec = step.spec
                if step_spec is None:
                    message = f"Step spec is unexpectedly missing: {step=}"
                    raise RuntimeError(message)

                step_input_data = core.action.wizard.StepInputDTO(
                    mapping=core.action.wizard.MappingInputDTO(delta=payload.params.host_component_map_delta),
                    created_at=timezone.now(),
                )

                cluster_id, bundle_id = self.wizard_repo.retrieve_related_cluster_id_and_cluster_bundle_id(
                    object_=action.owner
                )
                topology = retrieve_cluster_topology(cluster_id=cluster_id)

                if existence_violations := find_mapping_delta_objects_existence_violations(
                    delta=payload.params.host_component_map_delta, topology=topology
                ):
                    existence_violations[0].raise_error()

                if (
                    previous_mapping_input
                    := self.wizard_repo.retrieve_previous_mapping_step_input_with_cumulative_delta(
                        process_id=process.process_id, step_id=step.id
                    )
                ):
                    if previous_mapping_input.mapping.cumulative_delta is None:
                        message = f"Unexpected mapping input without cumulative_delta for step #{step.id}"
                        raise RuntimeError(message)

                    mapping_considering_cumulative_delta = get_new_flat_mapping_from_delta_and_topology(
                        delta=previous_mapping_input.mapping.cumulative_delta,
                        topology=topology,
                    )
                    topology = create_topology_with_new_mapping(
                        topology=topology, new_mapping=mapping_considering_cumulative_delta
                    )

                mapping_rules = self._prepare_mapping_rules_from_step_spec(step_spec=step_spec, topology=topology)
                if distribution_violations := find_hc_operation_distribution_violations(
                    delta=payload.params.host_component_map_delta,
                    rules=mapping_rules,
                    topology=topology,
                ):
                    distribution_violations[0].raise_error()

                new_mapping = get_new_flat_mapping_from_delta_and_topology(
                    delta=payload.params.host_component_map_delta, topology=topology
                )
                new_topology = create_topology_with_new_mapping(topology=topology, new_mapping=new_mapping)
                host_difference = find_hosts_difference(new_topology=new_topology, old_topology=topology)
                bundle_restrictions = retrieve_bundle_restrictions(bundle_id=bundle_id)

                mapping.check_for_main_mapping(
                    bundle_restrictions=bundle_restrictions,
                    new_topology=new_topology,
                    host_difference=host_difference,
                )

                self.wizard_service.perform_mapping(
                    process_id=process.process_id,
                    step_id=step.id,
                    step_input_data=step_input_data,
                )

                self.wizard_service.revoke_next_steps(process_id=process.process_id, step_id=step.id)
                return self.wizard_service.complete_step(process_id=process.process_id, step_id=step.id)

    def _to_typed_submit_step(
        self,
        *,
        step: core.action.wizard.ActionProcessStepModel,
        spec: core.action.wizard.ConfigStepSpec
        | core.action.wizard.OperationStepSpec
        | core.action.wizard.MappingStepSpec,
    ) -> core.action.wizard.Step:
        common = {
            "id": step.id,
            "full_name": (step.stage, step.name),
            "state": step.state,
            "required": step.required,
            "extra": core.action.wizard.StepExtra(
                display_name=step.display_name,
                description=step.description,
            ),
        }

        match step.type:
            case core.action.wizard.StepType.CONFIGURATION:
                return core.action.wizard.ConfigStep(
                    **common,
                    type=core.action.wizard.StepType.CONFIGURATION,
                    spec=cast(core.action.wizard.ConfigStepSpec, spec),
                )
            case core.action.wizard.StepType.OPERATION:
                return core.action.wizard.OperationStep(
                    **common,
                    type=core.action.wizard.StepType.OPERATION,
                    spec=cast(core.action.wizard.OperationStepSpec, spec),
                )
            case core.action.wizard.StepType.MAPPING:
                return core.action.wizard.MappingStep(
                    **common,
                    type=core.action.wizard.StepType.MAPPING,
                    spec=cast(core.action.wizard.MappingStepSpec, spec),
                )

    def _prepare_mapping_rules_from_step_spec(
        self,
        *,
        step_spec: core.action.wizard.MappingStepSpec,
        topology: ClusterTopology,
    ) -> MappingRules:
        comp_full_name_id_map = topology.component_full_name_id_mapping
        rules: MappingRules = {"add": set(), "remove": set()}

        for spec in step_spec:
            key = ComponentNameKey(service=spec.service, component=spec.component)
            if component_id := comp_full_name_id_map.get(key):
                rules[spec.operation].add(component_id)

        return rules


# scenario candidate


@dataclass(slots=True)
class CompleteWizardOperationStep:
    bundle_service: core.bundle.BundleService
    bundle_renderer: BundleRenderer[ActionArgs, TaskArgs]
    wizard_repo: core.action.wizard.WizardRepoI
    wizard_service: core.action.wizard.WizardService
    fill_wizard_step_spec: FillWizardStepSpec[ActionArgs, TaskArgs]

    def do(
        self,
        *,
        process_id: ActionProcessID,
        process_sync_key: UUID,
        step_id: ActionProcessStepID,
        process_context: ProcessContext,
        is_operation_success: bool,
    ) -> None:
        self.wizard_service.update_process_sync_key(
            process_id=process_id,
            sync_key=process_sync_key,
            new_sync_key=core.action.wizard.operations.get_new_process_sync_key(),
        )

        if not is_operation_success:
            self.wizard_service.update_step(
                step_id=step_id,
                state=core.action.wizard.ProcessStepState.CREATED,
            )
            return

        current_id = self.wizard_service.complete_step(process_id=process_id, step_id=step_id)

        if current_id:
            process = self.wizard_repo.retrieve_process(process_id=process_id)
            step = self.wizard_repo.retrieve_step(process_id=process_id, step_id=current_id)
            template = core.action.wizard.operations.find_step_spec_declaration(
                step=step, process_flow_spec=process.flow_spec
            ).template
            bundle_context = self.bundle_service.retrieve_bundle_context_from_prototype(
                prototype_id=process_context.action.owner_prototype.id
            )
            self.fill_wizard_step_spec.do(
                step_id=current_id,
                step_type=step.type,
                template=template,
                bundle_context=bundle_context,
                owner=process_context.owner,
                action_args=process_context.build_action_args(process_id=process_id),
                action_allow_to_terminate=process_context.action_orm.allow_to_terminate,
            )
