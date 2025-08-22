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

from pathlib import Path
from typing import Any

from adcm.mixins import GetParentObjectMixin, ParentObject
from cm.converters import core_type_to_model, orm_object_to_core_descriptor, orm_object_to_core_type
from cm.errors import AdcmEx
from cm.models import Action, Process, ProcessStep, ProcessStepInput
from cm.services.bundle import BundlePathResolver
from cm.services.concern.flags import BuiltInFlag, raise_flag
from cm.services.config.jinja import _get_jinja_config_new
from cm.services.job.run.repo import ActionRepoImpl
from cm.services.wizard import repo
from cm.services.wizard.errors import (
    NotCurrentStepSubmissionError,
    SyncKeyMismatchError,
)
from cm.services.wizard.operations import (
    SerializedConfigStep,
    SerializedOperationStep,
    initiate_process,
    perform_operation,
    render_template,
)
from cm.services.wizard.types import Step, StepType, StepUpdateDTO
from cm.services.wizard.validation import validate_operation
from core.bundle_alt.schema import WizardStep
from core.job.types import ActionInfo
from core.templates._types import RendererEnv
from core.types import ActionID, ActionProcessID, ActionProcessStepID, CoreObjectDescriptor
from django.db.transaction import atomic
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from api_v2.generic.action.utils import get_schema_config_meta
from api_v2.generic.action.views import ActionPermissionsMixin
from api_v2.generic.config.utils import convert_attr_to_adcm_meta
from api_v2.generic.wizard.serializers import OperationSerializer, ProcessSerializer, StepSerializer
from api_v2.views import ADCMGenericViewSet


class ActionProcessViewSet(GetParentObjectMixin, ADCMGenericViewSet, ActionPermissionsMixin):
    queryset = Process.objects.all()
    exc_conversion_map = {
        SyncKeyMismatchError: AdcmEx("WIZARD_SYNC_KEY_CONFLICT"),
        NotCurrentStepSubmissionError: AdcmEx("WIZARD_SUBMIT_STEP_CONFLICT", msg="Only current step can be submitted"),
    }

    def get_serializer_class(self):
        match self.action:
            case "create" | "retrieve":
                return ProcessSerializer
            case "operation":
                return OperationSerializer
            case _:
                raise NotImplementedError(f"No serializer for action: {self.action}")

    def get_parent_and_action_supporting_wizard(self) -> tuple[ParentObject, ActionInfo]:
        parent_object = self.get_parent_object(raise_=NotFound("Parent object not found"))

        action = ActionRepoImpl.get_action(id=self.kwargs["action_pk"])
        if not action.wizard_template:
            raise RuntimeError(f"Action #{action.id} does not support wizard functionality.")

        return parent_object, action

    def retrieve(self, request, *args, pk: str, **kwargs):  # noqa: ARG002
        parent_object, action_info = self.get_parent_and_action_supporting_wizard()
        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_info.id), parent_object=parent_object
        )
        instance = self.get_object()
        context = {
            "process_id": instance.pk,
            "step_names_id_map": repo.retrieve_step_names_id_map(process_id=instance.pk),
        }
        serializer = self.get_serializer(instance, context=context)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):  # noqa: ARG002
        parent_object, action_info = self.get_parent_and_action_supporting_wizard()

        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_info.id), parent_object=parent_object
        )

        if not action_info.wizard_template:
            raise RuntimeError(f"Action #{action_info.id} does not support wizard functionality.")

        # TODO: check if Process already exists
        with atomic():
            process_id = initiate_process(object_=orm_object_to_core_descriptor(parent_object), action=action_info)
            raise_flag(
                BuiltInFlag.WIZARD_PROCESS_RUNNING.value,
                on_objects=[CoreObjectDescriptor(id=parent_object.id, type=orm_object_to_core_type(parent_object))],
            )

        context = {
            "process_id": process_id,
            "step_names_id_map": repo.retrieve_step_names_id_map(process_id=process_id),
        }

        serializer = self.get_serializer(
            instance=Process.objects.get(pk=process_id),
            context=context,
        )

        return Response(data=serializer.data, status=HTTP_201_CREATED)

    @action(methods=["post"], detail=True, url_path="operation")
    def operation(self, request, *_, pk: ActionProcessID, **_kw):  # noqa: ARG002
        process_id = int(pk)
        parent_object, action_info = self.get_parent_and_action_supporting_wizard()

        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_info.id), parent_object=parent_object
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        validate_operation(process_id=process_id, payload=payload)
        perform_operation(process_id=process_id, payload=payload, object_=parent_object, action=action_info)

        return Response(
            status=HTTP_200_OK,
            data=ProcessSerializer(
                Process.objects.get(pk=process_id),
                context={"step_names_id_map": repo.retrieve_step_names_id_map(process_id=process_id)},
            ).data,
        )

    def handle_exception(self, exc: Any):
        return super().handle_exception(self.exc_conversion_map.get(exc.__class__, exc))


class ProcessStepViewSet(
    GetParentObjectMixin, ListModelMixin, RetrieveModelMixin, ADCMGenericViewSet, ActionPermissionsMixin
):
    queryset = ProcessStep.objects.all()
    serializer_class = StepSerializer

    def retrieve(self, request, *args, **kwargs):
        _ = request, args

        process_id, step_id, action_id = kwargs["process_pk"], kwargs["pk"], kwargs["action_pk"]

        parent_object = self.get_parent_object(raise_=NotFound("Parent object not found"))

        self.check_permissions_for_run(
            request=request, action=Action.objects.get(pk=action_id), parent_object=parent_object
        )

        object_ = orm_object_to_core_descriptor(parent_object)

        step = repo.retrieve_step(process_id=process_id, step_id=step_id)
        data = step.model_dump(include={"id", "display_name", "type", "state"})

        extra = serialize_step(process_id=process_id, step_id=step_id, action_id=action_id, object_=object_)
        data.update(**extra)

        return Response(data=data, status=HTTP_200_OK)


def serialize_step(
    process_id: ActionProcessID, step_id: ActionProcessStepID, action_id: ActionID, object_: CoreObjectDescriptor
) -> SerializedConfigStep | SerializedOperationStep:
    process = repo.retrieve_process(process_id=process_id)
    step = repo.retrieve_step(process_id=process_id, step_id=step_id)
    step_spec_raw = repo.find_step_spec(step=step, process_flow_spec=process.flow_spec)

    if step.is_render_required:
        _render_step_from_flow_spec(step=step, step_spec_raw=step_spec_raw, action_id=action_id, object_=object_)
        step = repo.retrieve_step(process_id=process_id, step_id=step_id)

    # TODO: merge with StepInput if exists
    step_input = ProcessStepInput.objects.filter(step_id=step.id).first()

    match step.type:
        case StepType.CONFIGURATION:
            return _serialize_config_step(
                step=step, step_spec_raw=step_spec_raw, action_id=action_id, object_=object_, step_input=step_input
            )
        case StepType.OPERATION:
            return _serialize_operation_step(step_spec_raw=step_spec_raw, step_input=step_input)
        case _:
            raise NotImplementedError(f"Can't serialize {step.type} step.")


def _serialize_config_step(
    step: Step,
    step_spec_raw: WizardStep,
    action_id: ActionID,
    object_: CoreObjectDescriptor,
    step_input: ProcessStepInput | None,
) -> SerializedConfigStep:
    action_orm = repo.retrieve_action_orm(action_id=action_id)
    object_orm = core_type_to_model(object_.type).objects.get(pk=object_.id)
    path_resolver = BundlePathResolver(bundle_hash=action_orm.prototype.bundle.hash)
    config_file = Path(path_resolver.bundle_root, step_spec_raw.template.file.path)

    prototype_configs, _ = _get_jinja_config_new(
        data=step.step_spec,
        action=action_orm,
        config_file=config_file,
        resolver=path_resolver,
        object_=object_orm,
    )

    schema, config, meta = get_schema_config_meta(
        object_=object_orm,
        prototype_configs=prototype_configs,
        path_resolver=path_resolver,
    )

    if step_input:
        config = step_input.configuration["config"]
        meta = convert_attr_to_adcm_meta(step_input.configuration["attr"])

    return {"configuration": {"config_schema": schema, "adcm_meta": meta, "config": config}}


def _serialize_operation_step(
    step_spec_raw: WizardStep, step_input: ProcessStepInput | None
) -> SerializedOperationStep:
    ui_options = step_spec_raw.model_dump(include={"ui_options"}).get("ui_options")

    task = None
    if step_input:
        task = {"id": step_input.job_id}

    # TODO: get job based on ProcessStepInput
    return {"ui_options": ui_options, "task": task}


def _render_step_from_flow_spec(
    step: Step, step_spec_raw: WizardStep, action_id: ActionID, object_: CoreObjectDescriptor
) -> None:
    action = ActionRepoImpl.get_action(id=action_id)
    environment = RendererEnv(
        discovery_root=repo.get_bundle_root_from_prototype(prototype_id=action.owner_prototype.id)
    )

    rendered = render_template(
        template=step_spec_raw.template, environment=environment, action_id=action.id, object_=object_
    )
    # todo conversion is missing

    repo.update_step(step_id=step.id, data=StepUpdateDTO(step_spec=rendered))
