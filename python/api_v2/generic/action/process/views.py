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

from dataclasses import asdict
from typing import Any

from adcm.mixins import GetParentObjectMixin
from cm.converters import (
    action_target_type_to_model,
    core_type_to_model,
    orm_object_to_action_target_descriptor,
    orm_object_to_core_descriptor,
)
from cm.errors import AdcmEx
from cm.legacy.services.action_process import repo
from cm.legacy.services.action_process.errors import (
    ActionProcessDBError,
    ActionProcessNotFoundError,
    ActionProcessOperationError,
    ActionProcessPayloadError,
    ActionProcessStepNotFoundError,
    SyncKeyMismatchError,
)
from cm.legacy.services.action_process.operations import OperationContext, initiate_process, perform_operation
from cm.legacy.services.action_process.schema_validation import Configuration
from cm.legacy.services.action_process.types import ProcessContext, Step
from cm.legacy.services.bundle_alt.render import ActionArgs, TaskArgs
from cm.legacy.services.concern.flags import BuiltInFlag, raise_flag_for_process, update_hierarchy_for_flag
from cm.legacy.services.job.action import check_no_blocking_concerns
from cm.legacy.services.job.run.repo import ActionRepoImpl
from cm.legacy.status_api import notify_about_redistributed_concerns_from_maps
from cm.models import (
    Action,
    Process,
    ProcessStep,
    ProcessStepInput,
    TaskLog,
)
from core.dynamic_bundle.render import BundleRenderer
from core.legacy.job import JobService
from core.types import ActionProcessID, ActionTargetDescriptor, ExtraActionTargetType
from dishka import FromDishka
from django.db.transaction import atomic
from django.http.response import Http404
from infra.di.django import inject
from infra.services import get_config_service
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
import core

from api_v2.generic.action.process.serializers import (
    OperationSerializer,
    ProcessSerializer,
    StepConfigurationSerializer,
    StepMappingSerializer,
    StepOperationSerializer,
    StepSerializer,
)
from api_v2.generic.action.views import ActionPermissionsMixin
from api_v2.task.serializers import TaskListSerializer
from api_v2.utils.config import (
    add_selection_for_selectable_groups,
    convert_json_fields_to_strings,
    convert_main_config,
)
from api_v2.views import ADCMGenericViewSet


class ProcessStepHandleExceptionMixin:
    def handle_exception(self, exc: Any):
        if exc_code := self.exc_conversion_map.get(exc.__class__):
            # hacker mode ON, rework it
            try:
                message = exc.msg
            except AttributeError:
                message = exc.args[0]

            exc = AdcmEx(code=exc_code, msg=message)

        return super().handle_exception(exc)


class ActionProcessViewSet(
    ProcessStepHandleExceptionMixin, GetParentObjectMixin, ADCMGenericViewSet, ActionPermissionsMixin
):
    queryset = Process.objects.all()
    exc_conversion_map = {
        SyncKeyMismatchError: "ACTION_PROCESS_UPDATE_CONFLICT",
        ActionProcessDBError: "ACTION_PROCESS_UPDATE_CONFLICT",
        ActionProcessOperationError: "ACTION_PROCESS_OPERATION_CONFLICT",
        ActionProcessNotFoundError: "ACTION_PROCESS_NOT_FOUND",
        core.config.ConfigOperationError: "ACTION_PROCESS_OPERATION_CONFLICT",
        ActionProcessPayloadError: "BAD_REQUEST",
    }

    def get_serializer_class(self):
        match self.action:
            case "create" | "retrieve":
                return ProcessSerializer
            case "operation":
                return OperationSerializer
            case _:
                raise NotImplementedError(f"No serializer for action: {self.action}")

    def get_process_context(self, job_service: JobService) -> ProcessContext:
        target_orm = self.get_parent_object(raise_=NotFound("Parent object not found"))

        try:
            action = ActionRepoImpl.get_action(id=self.kwargs["action_pk"])
            action_orm = Action.objects.get(id=self.kwargs["action_pk"])
        except Action.DoesNotExist:
            raise NotFound("Action not found") from None

        if not action.wizard_template:
            raise AdcmEx(
                code="ACTION_PROCESS_ACTION_NOT_SUITABLE",
                msg=f"Action #{action.id} does not support action process functionality.",
            )

        target = orm_object_to_action_target_descriptor(target_orm)
        owner = job_service.repo.find_action_owner(action_id=action.id, target=target)
        owner_orm = core_type_to_model(owner.type).objects.get(id=owner.id)

        return ProcessContext(
            action=action, action_orm=action_orm, target=target, target_orm=target_orm, owner=owner, owner_orm=owner_orm
        )

    @inject
    def retrieve(self, request, *args, pk: str, job_service: FromDishka[JobService], **kwargs):  # noqa: ARG002
        process_context = self.get_process_context(job_service=job_service)

        self.check_permissions_for_run(
            request=request,
            action=process_context.action_orm,
            parent_object=process_context.cluster_relative_object(),
        )
        try:
            instance = self.get_object()
        except Http404 as error:
            raise ActionProcessNotFoundError from error

        context = {
            "process_id": instance.pk,
            "step_names_id_state_map": repo.retrieve_step_names_id_state_map(process_id=instance.pk),
        }
        serializer = self.get_serializer(instance, context=context)
        return Response(serializer.data)

    @inject
    def create(
        self,
        request,
        job_service: FromDishka[JobService],
        bundle_renderer: FromDishka[BundleRenderer[ActionArgs, TaskArgs]],
        **_,
    ):
        process_context = self.get_process_context(job_service=job_service)
        cluster_relative_object_orm = process_context.cluster_relative_object()
        cluster_relative_object_cod = process_context.cluster_relative_object(as_descriptor=True)

        self.check_permissions_for_run(
            request=request, action=process_context.action_orm, parent_object=cluster_relative_object_orm
        )
        check_no_blocking_concerns(lock_owner=cluster_relative_object_orm, action_name=process_context.action.name)

        # TODO: check if Process already exists
        with atomic():
            process_id = initiate_process(process_context=process_context, bundle_renderer=bundle_renderer)

            flag = BuiltInFlag.ACTION_PROCESS_RUNNING.value
            changed = raise_flag_for_process(
                flag=flag,
                on_objects=[cluster_relative_object_cod],
                action=process_context.action_orm,
                action_owner=cluster_relative_object_orm,
            )

            if changed:
                added = update_hierarchy_for_flag(flag=flag, on_objects=[cluster_relative_object_cod])
                notify_about_redistributed_concerns_from_maps(added=added, removed={})

        context = {
            "process_id": process_id,
            "step_names_id_state_map": repo.retrieve_step_names_id_state_map(process_id=process_id),
        }

        serializer = self.get_serializer(
            instance=Process.objects.get(pk=process_id),
            context=context,
        )

        return Response(data=serializer.data, status=HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="operation")
    @inject
    def operation(
        self,
        request,
        *,
        pk: ActionProcessID,
        job_service: FromDishka[JobService],
        config_service: FromDishka[core.config.ConfigService],
        bundle_renderer: FromDishka[BundleRenderer[ActionArgs, TaskArgs]],
        **_,
    ):  # noqa: ARG002
        process_id = int(pk)
        process_context = self.get_process_context(job_service=job_service)

        self.check_permissions_for_run(
            request=request,
            action=Action.objects.get(pk=process_context.action.id),
            parent_object=process_context.cluster_relative_object(),
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        context = OperationContext(process_context=process_context, config_processor=self._convert_configuration)
        perform_operation(
            process_id=process_id,
            payload=payload,
            context=context,
            config_service=config_service,
            job_service=job_service,
            bundle_renderer=bundle_renderer,
        )

        return Response(
            status=HTTP_200_OK,
            data=ProcessSerializer(
                Process.objects.get(pk=process_id),
                context={"step_names_id_state_map": repo.retrieve_step_names_id_state_map(process_id=process_id)},
            ).data,
        )

    def _convert_configuration(
        self, configuration: Configuration, specification: core.config.spec.FullSpec
    ) -> core.config.Configuration:
        return convert_main_config(
            configuration={"attr": configuration.adcm_meta, "config": configuration.config}, specification=specification
        )


class ProcessStepViewSet(
    ProcessStepHandleExceptionMixin,
    GetParentObjectMixin,
    RetrieveModelMixin,
    ADCMGenericViewSet,
    ActionPermissionsMixin,
):
    queryset = ProcessStep.objects.all()
    serializer_class = StepSerializer
    exc_conversion_map = {
        ActionProcessNotFoundError: "ACTION_PROCESS_NOT_FOUND",
        ActionProcessStepNotFoundError: "ACTION_PROCESS_STEP_NOT_FOUND",
    }

    def retrieve(self, request, *args, **kwargs):
        _ = request, args

        process_id, step_id, action_id = kwargs["process_pk"], kwargs["pk"], kwargs["action_pk"]

        parent_object = self.get_parent_object(raise_=NotFound("Parent object not found"))

        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_id), parent_object=parent_object
        )

        target = orm_object_to_action_target_descriptor(parent_object)

        step = repo.retrieve_step(process_id=process_id, step_id=step_id)
        data = step.model_dump(include={"id", "name", "display_name", "description", "type", "state"})

        config_service = get_config_service()

        serialized_data = serialize_step(step=step, object_=target, base_data=data, config_service=config_service)

        return Response(data=serialized_data, status=HTTP_200_OK)


def serialize_step(
    step: Step, object_: ActionTargetDescriptor, base_data: dict, config_service: core.config.ConfigService
) -> dict:
    if step.is_render_required:
        raise AdcmEx("ACTION_PROCESS_STEP_NOT_RENDERED", msg=f"Step #{step.id} {step.display_name} is not rendered yet")

    step_input = ProcessStepInput.objects.filter(step_id=step.id).first()

    match step.type:
        case core.action.wizard.StepType.CONFIGURATION:
            return _serialize_config_step(
                step=step, object_=object_, step_input=step_input, base_data=base_data, config_service=config_service
            )
        case core.action.wizard.StepType.OPERATION:
            return _serialize_operation_step(step=step, step_input=step_input, base_data=base_data)
        case core.action.wizard.StepType.MAPPING:
            return _serialize_mapping_step(step=step, step_input=step_input, base_data=base_data)


def _serialize_config_step(
    step: Step,
    object_: ActionTargetDescriptor,
    step_input: ProcessStepInput | None,
    base_data: dict,
    config_service: core.config.ConfigService,
) -> dict:
    if not (isinstance(step.spec, tuple) and len(step.spec) == 2):
        message = f"Incorrect spec for config step: {step=}"
        raise ValueError(message)

    object_orm = action_target_type_to_model(object_.type).objects.get(pk=object_.id)
    if object_.type == ExtraActionTargetType.ACTION_HOST_GROUP:
        object_orm = object_orm.object
    owner = orm_object_to_core_descriptor(object_orm)

    spec, defaults = step.spec
    if not (isinstance(spec, core.config.spec.FullSpec) and isinstance(defaults, core.config.Defaults)):
        message = f"Incorrect spec for config step: {spec=} {defaults=}"
        raise TypeError(message)

    schema = config_service.retrieve_jsonschema_for_action(
        action_specification=spec,
        action_config_defaults=defaults,
        action_owner=core.config.ConfigOwner(descriptor=owner, state=object_orm.state),
    )

    if step_input:
        config = step_input.configuration["values"]
        attributes = step_input.configuration["attributes"]
    else:
        default_config = core.config.operations.prepare_config_from_defaults(defaults=defaults, specification=spec)
        config = default_config.values
        attributes = {name: asdict(attrs) for name, attrs in default_config.attributes.items()}

    config = add_selection_for_selectable_groups(values=config, spec=spec)
    config = convert_json_fields_to_strings(values=config, spec=spec, inplace=True)

    meta = {}
    for name, attrs in attributes.items():
        meta[name] = {}

        if (is_active := attrs.get("is_active")) is not None:
            meta[name]["isActive"] = is_active

        if (is_synced := attrs.get("is_synced")) is not None:
            meta[name]["isSynchronized"] = is_synced

    return StepConfigurationSerializer(
        base_data | {"configuration": {"config_schema": schema, "adcm_meta": meta, "config": config}}
    ).data


def _serialize_operation_step(
    step: Step,
    step_input: ProcessStepInput | None,
    base_data: dict,
    # Any returned for faster development until feature flag is removed
) -> dict:
    process = repo.retrieve_process(process_id=step.process_id)
    step_spec_declaration = repo.find_step_spec_declaration(step=step, process_flow_spec=process.flow_spec)
    if not isinstance(step_spec_declaration.extra, core.action.wizard.OperationStepExtra):
        raise TypeError(f"Incorrect extra for operation step: {step_spec_declaration=}")

    ui_options = asdict(step_spec_declaration.extra.ui_options)

    task_data = None
    if step_input:
        # `job_id` is `task_id` for now
        task_id = step_input.job_id  # JobLog.objects.values_list("task_id", flat=True).get(id=step_input.job_id)
        task = TaskLog.objects.select_related("action").get(id=task_id)
        task_serializer = TaskListSerializer(task)
        task_data = task_serializer.data

    return StepOperationSerializer(base_data | {"ui_options": ui_options, "task": task_data}).data


def _serialize_mapping_step(
    step: Step,  # noqa: ARG001
    step_input: ProcessStepInput | None,  # noqa: ARG001
    base_data: dict,
) -> dict:
    mapping_step_data = {"rules": step.step_spec, "suggestions": []}

    if step_input:
        mapping_step_data |= {
            "delta": step_input.mapping["delta"],
            "cumulative_delta": step_input.mapping["cumulative_delta"],
        }
    else:
        # todo requires action processing rework to get in here Process "meta" repr
        previous_mapping_input = repo.retrieve_previous_mapping_step_input_with_cumulative_delta(
            process_id=step.process_id, step_id=step.id
        )
        if previous_mapping_input:
            mapping_step_data["cumulative_delta"] = previous_mapping_input.mapping.cumulative_delta

    return StepMappingSerializer(base_data | mapping_step_data).data
