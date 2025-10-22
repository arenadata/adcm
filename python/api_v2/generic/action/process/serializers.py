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

from cm.models import Process
from cm.services.action_process.schema_validation import (
    CompleteStepPayload,
    OperationPayloadSchema,
    ResetStepPayload,
    SubmitStepPayload,
)
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import DateTimeField
from rest_framework.serializers import (
    CharField,
    DictField,
    IntegerField,
    ModelSerializer,
    Serializer,
    SerializerMethodField,
)
import pydantic


class StepFromStageSerializer(Serializer):
    id = IntegerField()
    state = CharField()
    display_name = CharField()
    type = SerializerMethodField()

    def get_type(self, data: dict) -> str:
        if data.get("config_template"):
            return "configuration"

        if data.get("scripts_template"):
            return "operation"

        if data.get("hc_template"):
            return "mapping"

        raise ValueError(f"Unknown step type for {data.get('id')=} {data.get('display_name')=}")


class StageSerializer(Serializer):
    display_name = CharField()
    steps = SerializerMethodField()

    # D
    def get_steps(self, data: dict) -> list[dict]:
        steps = data["steps"]
        for step in steps:
            step["id"] = self.context["step_names_id_state_map"][step["name"], step["display_name"]][0]
            step["state"] = self.context["step_names_id_state_map"][step["name"], step["display_name"]][1]

        return StepFromStageSerializer(sorted(steps, key=lambda x: x["id"]), many=True).data


class ProcessShortSerializer(ModelSerializer):
    sync_key = CharField()
    state = CharField()
    created_at = DateTimeField()

    class Meta:
        model = Process
        fields = ["id", "state", "current_step", "created_at", "sync_key"]


class ProcessSerializer(ProcessShortSerializer):
    stages = StageSerializer(source="flow_spec", many=True)

    class Meta:
        model = Process
        fields = ["id", "state", "current_step", "created_at", "stages", "sync_key"]


class StepSerializer(Serializer):
    id = IntegerField()
    display_name = CharField()
    type = CharField()
    state = CharField()


class OperationSerializer(Serializer):
    method = CharField()
    params = DictField()

    def validate(self, attrs: Any) -> SubmitStepPayload | CompleteStepPayload | ResetStepPayload:
        try:
            validated = OperationPayloadSchema.model_validate({"payload": attrs}).payload
        except pydantic.ValidationError as e:
            raise DRFValidationError(detail=e) from e

        return validated


class StepConfigurationSerializer(StepSerializer):
    configuration = DictField()


class StepOperationSerializer(StepSerializer):
    ui_options = DictField()
    task = DictField(allow_null=True, required=False)


class MappingRuleSerializer(Serializer):
    operation = CharField()
    component = CharField()
    service = CharField()


class MappingDeltaItemSerializer(Serializer):
    host_id = IntegerField()
    component_id = IntegerField()


class MappingDeltaSerializer(Serializer):
    add = MappingDeltaItemSerializer(many=True)
    remove = MappingDeltaItemSerializer(many=True)


class StepMappingSerializer(StepSerializer):
    rules = MappingRuleSerializer(many=True)
    delta = MappingDeltaSerializer()
    cumulative_delta = MappingDeltaSerializer()
    suggestions = MappingDeltaItemSerializer(many=True, required=False, default=list)
