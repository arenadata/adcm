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
from uuid import UUID

from cm.models import Process, ProcessStep, ProcessStepState
from cm.services.wizard.types import ProcessOperationType
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    DictField,
    IntegerField,
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)
from rest_framework.status import HTTP_400_BAD_REQUEST
import pydantic


class StepFromStageSerializer(Serializer):
    id = IntegerField()
    display_name = CharField()
    type = SerializerMethodField()

    def get_type(self, data: dict) -> str:
        if data.get("config_template"):
            return "configuration"

        if data.get("scripts_template"):
            return "operation"

        raise ValueError(f"Unknown step type for {data.get('id')=} {data.get('display_name')=}")


class StageSerializer(Serializer):
    display_name = CharField()
    steps = SerializerMethodField()

    def get_steps(self, data: dict) -> list[dict]:
        steps = data["steps"]
        for step in steps:
            step["id"] = self.context["step_names_id_map"][step["name"], step["display_name"]]

        return StepFromStageSerializer(sorted(steps, key=lambda x: x["id"]), many=True).data


class ProcessSerializer(ModelSerializer):
    current_step = SerializerMethodField(source="get_current_step")
    stages = StageSerializer(source="flow_spec", many=True)
    sync_key = CharField(source="hash")

    class Meta:
        model = Process
        fields = ["id", "state", "current_step", "created_at", "stages", "sync_key"]

    def get_current_step(self, instance: Process) -> int:
        _ = instance

        latest = None
        step_ids = []
        for stage in reversed(instance.flow_spec):
            for step in reversed(stage["steps"]):
                step_id = self.context["step_names_id_map"][step["name"], step["display_name"]]
                step_ids.append(step_id)
                state = ProcessStep.objects.values_list("state", flat=True).get(id=step_id)
                if state in (ProcessStepState.CREATED, ProcessStepState.RUNNING):
                    latest = step_id

        if latest is None:
            latest = step_ids[0]

        return latest


class StepSerializer(Serializer):
    id = IntegerField()
    display_name = CharField()
    type = CharField()


# Operations on Step


class ProcessSyncKey(pydantic.BaseModel):
    process_sync_key: UUID


class Configuration(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    config: dict
    adcm_meta: dict


class SubmitOperation(ProcessSyncKey):
    model_config = pydantic.ConfigDict(extra="forbid")

    step_id: int
    configuration: Configuration | None = None


class OperationSerializer(Serializer):
    method = ChoiceField(choices=[e.value for e in ProcessOperationType])
    # todo add validation
    params = DictField()

    def validate(self, attrs: Any) -> Any:
        res = super().validate(attrs)

        params = attrs.get("params") or {}

        try:
            match res.get("method"):
                case ProcessOperationType.COMPLETE:
                    ProcessSyncKey.model_validate(params)
                case ProcessOperationType.SUBMIT:
                    SubmitOperation.model_validate(params)
        except pydantic.ValidationError as e:
            raise DRFValidationError(detail=e, code=HTTP_400_BAD_REQUEST) from e

        return res
