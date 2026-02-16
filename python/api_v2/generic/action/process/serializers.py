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

from cm.legacy.services.action_process.schema_validation import (
    CompleteProcessPayload,
    OperationPayloadSchema,
    ResetStepPayload,
    SubmitStepPayload,
)
from cm.models import Process
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
    name = CharField()
    description = CharField(source="extra.description", default="")
    display_name = CharField(source="extra.display_name")
    type = CharField()


class StageSerializer(Serializer):
    name = CharField()
    description = CharField(source="extra.description", default="")
    display_name = CharField(source="extra.display_name")
    steps = SerializerMethodField()

    def get_steps(self, data: dict) -> list[dict]:
        steps = data["steps"]
        for step in steps:
            step["id"] = self.context["step_names_id_state_map"][step["name"], step["extra"]["display_name"]][0]
            step["state"] = self.context["step_names_id_state_map"][step["name"], step["extra"]["display_name"]][1]

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
    description = CharField()
    name = CharField()
    type = CharField()
    state = CharField()


class OperationSerializer(Serializer):
    method = CharField()
    params = DictField()

    def validate(self, attrs: Any) -> SubmitStepPayload | CompleteProcessPayload | ResetStepPayload:
        try:
            validated = OperationPayloadSchema.model_validate({"payload": attrs}).payload
        except pydantic.ValidationError as e:
            raise DRFValidationError(detail=e) from e

        return validated


class StepConfigurationSerializer(StepSerializer):
    configuration = DictField()


class StepOperationSerializer(StepSerializer):
    ui_options = DictField()
    # should be actually TaskListSerializer, but not for now due to circular imports
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
    delta = MappingDeltaSerializer(allow_null=True, default=None)
    cumulative_delta = MappingDeltaSerializer(allow_null=True, default=None)
