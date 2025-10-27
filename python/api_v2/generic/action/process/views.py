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

from typing import Any

from adcm.mixins import GetParentObjectMixin, ParentObject
from cm.converters import core_type_to_model, orm_object_to_core_descriptor, orm_object_to_core_type
from cm.errors import AdcmEx
from cm.models import Action, Process, ProcessStep, ProcessStepInput, PrototypeConfig
from cm.services.action_process import repo
from cm.services.action_process.errors import (
    ActionProcessDBError,
    ActionProcessNotFoundError,
    ActionProcessOperationError,
    ActionProcessStepNotFoundError,
    SyncKeyMismatchError,
)
from cm.services.action_process.operations import (
    OperationContext,
    SerializedConfigStep,
    SerializedOperationStep,
    initiate_process,
    perform_operation,
    process_payload_config,
)
from cm.services.action_process.types import Step, StepType
from cm.services.bundle import BundlePathResolver
from cm.services.concern.flags import BuiltInFlag, raise_flag, update_hierarchy_for_flag
from cm.services.config import convert_attr_to_adcm_meta
from cm.services.job.run.repo import ActionRepoImpl
from cm.status_api import notify_about_redistributed_concerns_from_maps
from core.job.types import ActionInfo
from core.types import ActionProcessID, CoreObjectDescriptor
from django.db.transaction import atomic
from django.http.response import Http404
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from api_v2.generic.action.process.serializers import (
    OperationSerializer,
    ProcessSerializer,
    StepConfigurationSerializer,
    StepMappingSerializer,
    StepOperationSerializer,
    StepSerializer,
)
from api_v2.generic.action.utils import get_schema_config_meta
from api_v2.generic.action.views import ActionPermissionsMixin
from api_v2.views import ADCMGenericViewSet


class ProcessStepHandleExceptionMixin:
    def handle_exception(self, exc: Any):
        if exc_code := self.exc_conversion_map.get(exc.__class__):
            exc = AdcmEx(code=exc_code, msg=exc.msg)

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
    }

    def get_serializer_class(self):
        match self.action:
            case "create" | "retrieve":
                return ProcessSerializer
            case "operation":
                return OperationSerializer
            case _:
                raise NotImplementedError(f"No serializer for action: {self.action}")

    def get_parent_and_action_supporting_process(self) -> tuple[ParentObject, ActionInfo]:
        parent_object = self.get_parent_object(raise_=NotFound("Parent object not found"))

        try:
            action = ActionRepoImpl.get_action(id=self.kwargs["action_pk"])
        except Action.DoesNotExist:
            raise NotFound("Action not found") from None

        if not action.wizard_template:
            raise AdcmEx(
                code="ACTION_PROCESS_ACTION_NOT_SUITABLE",
                msg=f"Action #{action.id} does not support action process functionality.",
            )

        return parent_object, action

    def retrieve(self, request, *args, pk: str, **kwargs):  # noqa: ARG002
        parent_object, action_info = self.get_parent_and_action_supporting_process()
        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_info.id), parent_object=parent_object
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

    def create(self, request, *args, **kwargs):  # noqa: ARG002
        parent_object, action_info = self.get_parent_and_action_supporting_process()

        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_info.id), parent_object=parent_object
        )

        # TODO: check if Process already exists
        with atomic():
            process_id = initiate_process(object_=orm_object_to_core_descriptor(parent_object), action=action_info)
            flag = BuiltInFlag.ACTION_PROCESS_RUNNING.value
            targets = [CoreObjectDescriptor(id=parent_object.id, type=orm_object_to_core_type(parent_object))]
            changed = raise_flag(flag=flag, on_objects=targets)

            if changed:
                added = update_hierarchy_for_flag(flag=flag, on_objects=targets)
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
    def operation(self, request, *_, pk: ActionProcessID, **_kw):  # noqa: ARG002
        process_id = int(pk)
        parent_object, action_info = self.get_parent_and_action_supporting_process()

        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_info.id), parent_object=parent_object
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        context = OperationContext(
            object=orm_object_to_core_descriptor(object_=parent_object),
            action=action_info,
            config_processor=process_payload_config,
        )
        perform_operation(process_id=process_id, payload=payload, context=context)

        return Response(
            status=HTTP_200_OK,
            data=ProcessSerializer(
                Process.objects.get(pk=process_id),
                context={"step_names_id_state_map": repo.retrieve_step_names_id_state_map(process_id=process_id)},
            ).data,
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

        object_ = orm_object_to_core_descriptor(parent_object)

        step = repo.retrieve_step(process_id=process_id, step_id=step_id)
        data = step.model_dump(include={"id", "name", "display_name", "type", "state"})

        serialized_data = serialize_step(step=step, object_=object_, base_data=data)

        return Response(data=serialized_data, status=HTTP_200_OK)


def serialize_step(
    step: Step, object_: CoreObjectDescriptor, base_data: dict
) -> SerializedConfigStep | SerializedOperationStep | StepMappingSerializer:
    if step.is_render_required:
        raise AdcmEx("ACTION_PROCESS_STEP_NOT_RENDERED", msg=f"Step #{step.id} {step.display_name} is not rendered yet")

    step_input = ProcessStepInput.objects.filter(step_id=step.id).first()

    match step.type:
        case StepType.CONFIGURATION:
            return _serialize_config_step(step=step, object_=object_, step_input=step_input, base_data=base_data)
        case StepType.OPERATION:
            return _serialize_operation_step(step=step, step_input=step_input, base_data=base_data)
        case StepType.MAPPING:
            return _serialize_mapping_step(step=step, step_input=step_input, base_data=base_data)
        case _:
            raise NotImplementedError(f"Can't serialize {step.type} step.")


def _serialize_config_step(
    step: Step,
    object_: CoreObjectDescriptor,
    step_input: ProcessStepInput | None,
    base_data: dict,
) -> SerializedConfigStep:
    object_orm = core_type_to_model(object_.type).objects.get(pk=object_.id)
    path_resolver = BundlePathResolver(bundle_hash=object_orm.prototype.bundle.hash)

    prototype_configs = [PrototypeConfig(**config) for config in step.step_spec]
    schema, config, meta = get_schema_config_meta(
        object_=object_orm,
        prototype_configs=prototype_configs,
        path_resolver=path_resolver,
    )

    if step_input:
        config = step_input.configuration["config"]
        meta = convert_attr_to_adcm_meta(step_input.configuration["attr"])

    return StepConfigurationSerializer(
        base_data | {"configuration": {"config_schema": schema, "adcm_meta": meta, "config": config}}
    ).data


def _serialize_operation_step(
    step: Step, step_input: ProcessStepInput | None, base_data: dict
) -> SerializedOperationStep:
    process = repo.retrieve_process(process_id=step.process_id)
    step_spec_declaration = repo.find_step_spec_declaration(step=step, process_flow_spec=process.flow_spec)
    ui_options = step_spec_declaration.model_dump(include={"ui_options"}).get("ui_options")

    task = None
    if step_input:
        task = {"id": step_input.job_id}

    return StepOperationSerializer(base_data | {"ui_options": ui_options, "task": task}).data


def _serialize_mapping_step(
    step: Step,  # noqa: ARG001
    step_input: ProcessStepInput | None,  # noqa: ARG001
    base_data: dict,
) -> StepMappingSerializer:
    mapping_step_data = {"rules": step.step_spec, "suggestions": []}

    if step_input:
        mapping_step_data |= {
            "delta": step_input.mapping["delta"],
            "cumulative_delta": step_input.mapping["cumulative_delta"],
        }

    return StepMappingSerializer(base_data | mapping_step_data).data
