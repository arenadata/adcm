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

from cm.legacy.services.action_process.schema_validation import ProcessOperationType
from django.db.models.fields import BooleanField
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_view,
)
from rest_framework.fields import CharField, ChoiceField, DictField, IntegerField, UUIDField
from rest_framework.serializers import Serializer
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import ErrorSerializer, responses
from api_v2.generic.action.process.serializers import MappingDeltaSerializer, MappingRuleSerializer, ProcessSerializer


class Step(Serializer):
    id = IntegerField()
    name = CharField()
    description = CharField()
    display_name = CharField()
    type = CharField()
    state = CharField()
    required = BooleanField()


class SubmitStepConfiguration(Serializer):
    config = DictField()
    adcm_meta = DictField()


class StepConfigurationInternals(SubmitStepConfiguration):
    config_schema = DictField()


class StepConfiguration(Step):
    configuration = StepConfigurationInternals()


class StepTask(Serializer):
    id = IntegerField()


class StepOperation(Step):
    ui_options = DictField()
    task = StepTask(allow_null=True)


class StepMapping(Step):
    rules = MappingRuleSerializer(many=True)
    delta = MappingDeltaSerializer(allow_null=True, default=None)
    cumulative_delta = MappingDeltaSerializer(allow_null=True, default=None)


class ResetStepParamsSerializer(Serializer):
    step_id = IntegerField()
    process_sync_key = UUIDField()


class SkipStepParamsSerializer(ResetStepParamsSerializer):
    ...


class SubmitStepParamsSerializer(ResetStepParamsSerializer):
    configuration = SubmitStepConfiguration(required=False)


class CompleteProcessParamsSerializer(Serializer):
    process_sync_key = UUIDField()


class OperationSubmitStep(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.SUBMIT.value, ProcessOperationType.SUBMIT.value)])
    params = SubmitStepParamsSerializer(required=True)


class OperationSkipStep(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.SKIP.value, ProcessOperationType.SKIP.value)])
    params = SkipStepParamsSerializer(required=True)


class OperationResetStep(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.RESET.value, ProcessOperationType.RESET.value)])
    params = ResetStepParamsSerializer(required=True)


class OperationCompleteProcess(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.COMPLETE.value, ProcessOperationType.COMPLETE.value)])
    params = CompleteProcessParamsSerializer(required=True)


example_process = OpenApiExample(
    "Process example",
    value={
        "id": 1,
        "state": "created",
        "currentStep": 3,
        "createdAt": "2025-08-29T07:12:17.847185Z",
        "syncKey": "c0ffead5-054f-4ef7-8776-607ea80812f2",
        "stages": [
            {
                "name": "first_stage",
                "displayName": "First stage",
                "description": "",
                "steps": [
                    {
                        "id": 1,
                        "name": "stage1_step1",
                        "description": "",
                        "displayName": "Stage1.Step1",
                        "type": "configuration",
                    }
                ],
            },
            {
                "name": "second_stage",
                "displayName": "Second stage",
                "description": "",
                "steps": [
                    {
                        "id": 2,
                        "name": "stage2_step2",
                        "description": "",
                        "displayName": "Stage2.Step1",
                        "type": "configuration",
                    },
                    {
                        "id": 3,
                        "name": "stage2_step2",
                        "description": "",
                        "displayName": "Stage2.Step2",
                        "type": "operation",
                    },
                ],
            },
            {
                "name": "third_stage",
                "displayName": "Third stage",
                "description": "",
                "steps": [
                    {
                        "id": 4,
                        "name": "stage3_step1",
                        "description": "",
                        "displayName": "Stage3.Step1",
                        "type": "operation",
                    }
                ],
            },
            {
                "name": "fourth_stage",
                "displayName": "Fourth stage",
                "description": "",
                "steps": [
                    {
                        "id": 5,
                        "name": "stage4_step1",
                        "description": "",
                        "displayName": "Stage4.Step1",
                        "type": "operation",
                    },
                    {
                        "id": 6,
                        "name": "stage4_step2",
                        "description": "",
                        "displayName": "Stage4.Step2",
                        "type": "operation",
                    },
                ],
            },
        ],
    },
    response_only=True,  # this is an API response example
)


def document_action_process_viewset(object_type: str, operation_id_variant: str | None = None):
    capitalized_type = operation_id_variant or object_type.capitalize()

    return extend_schema_view(
        create=extend_schema(
            operation_id=f"post{capitalized_type}Process",
            description=f"Create a new {object_type} action's process.",
            summary=f"POST {object_type} process",
            request={},
            responses=responses(
                success=(HTTP_201_CREATED, ProcessSerializer), errors=(HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            ),
            examples=[example_process],
        ),
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}Process",
            description=f"Get information about a specific {object_type} action's process.",
            summary=f"GET {object_type} process",
            responses=responses(success=(HTTP_200_OK, ProcessSerializer), errors=HTTP_404_NOT_FOUND),
            examples=[example_process],
        ),
        operation=extend_schema(
            operation_id=f"post{capitalized_type}Operation",
            description=f"Perform operation on {object_type} action's process.",
            summary=f"POST {object_type} operation",
            examples=[
                OpenApiExample(
                    "Submit configuration",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.SUBMIT.value,
                        "params": {
                            "stepId": 1,
                            "configuration": {"config": {"new": "config"}, "adcmMeta": {}},
                            "processSyncKey": "c0a71f0b-4a6b-489c-a352-cfba8d8c3c17",
                        },
                    },
                ),
                OpenApiExample(
                    "Submit operation",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.SUBMIT.value,
                        "params": {"stepId": 1, "processSyncKey": "c0a71f0b-4a6b-489c-a352-cfba8d8c3c17"},
                    },
                ),
                OpenApiExample(
                    "Reset operation",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.RESET.value,
                        "params": {"stepId": 1, "processSyncKey": "c0a71f0b-4a6b-489c-a352-cfba8d8c3c17"},
                    },
                ),
                OpenApiExample(
                    "Skip operation",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.SKIP.value,
                        "params": {"stepId": 1, "processSyncKey": "c0a71f0b-4a6b-489c-a352-cfba8d8c3c17"},
                    },
                ),
                OpenApiExample(
                    "Complete operation",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.COMPLETE.value,
                        "params": {"processSyncKey": "c0a71f0b-4a6b-489c-a352-cfba8d8c3c17"},
                    },
                ),
            ],
            request=PolymorphicProxySerializer(
                component_name=f"{object_type}Process",
                serializers=[OperationSubmitStep, OperationResetStep, OperationSkipStep, OperationCompleteProcess],
                resource_type_field_name="method",
            ),
            responses={
                HTTP_200_OK: OpenApiResponse(response=ProcessSerializer, examples=[example_process]),
                HTTP_400_BAD_REQUEST: ErrorSerializer,
                HTTP_404_NOT_FOUND: ErrorSerializer,
                HTTP_409_CONFLICT: ErrorSerializer,
            },
        ),
    )


def document_action_process_step_viewset(object_type: str, operation_id_variant: str | None = None):
    capitalized_type = operation_id_variant or object_type.capitalize()

    return extend_schema_view(
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}ProcessStep",
            description=f"Get information about a specific {object_type} action's process step.",
            summary=f"GET {object_type} process step",
            responses={
                HTTP_200_OK: OpenApiResponse(
                    response=PolymorphicProxySerializer(
                        component_name="ProcessStep",
                        serializers=[
                            StepConfiguration,
                            StepOperation,
                            StepMapping,
                        ],
                        resource_type_field_name="type",
                    ),
                    examples=[
                        OpenApiExample(
                            "Operation step",
                            value={
                                "id": 1,
                                "type": "operation",
                                "name": "stage2_step2",
                                "displayName": "Stage2.Step2",
                                "description": "",
                                "state": "created",
                                "task": {"id": 8},
                                "uiOptions": {"buttonName": "ButtonName"},
                                "required": True,
                            },
                        ),
                        OpenApiExample(
                            "Configuration step",
                            value={
                                "id": 1,
                                "type": "configuration",
                                "name": "stage1_step1",
                                "displayName": "Stage1.Step1",
                                "description": "",
                                "state": "created",
                                "required": True,
                                "configuration": {
                                    "adcmMeta": {},
                                    "config": {"integer_field": 1, "string_field": "string_value"},
                                    "configSchema": {
                                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                                        "adcmMeta": {
                                            "activation": None,
                                            "enumExtra": None,
                                            "isAdvanced": False,
                                            "isInvisible": False,
                                            "isSecret": False,
                                            "nullValue": None,
                                            "stringExtra": None,
                                            "synchronization": None,
                                        },
                                        "additionalProperties": False,
                                        "description": "",
                                        "properties": {
                                            "integer_field": {
                                                "adcmMeta": {
                                                    "activation": None,
                                                    "enumExtra": None,
                                                    "isAdvanced": False,
                                                    "isInvisible": False,
                                                    "isSecret": False,
                                                    "stringExtra": None,
                                                    "synchronization": None,
                                                },
                                                "default": 1,
                                                "description": "",
                                                "readOnly": False,
                                                "title": "integer_field",
                                                "type": "integer",
                                            },
                                        },
                                        "readOnly": False,
                                        "required": ["integer_field"],
                                        "title": "Configuration",
                                        "type": "object",
                                    },
                                },
                            },
                        ),
                        OpenApiExample(
                            "Mapping step",
                            value={
                                "id": 1,
                                "type": "configuration",
                                "name": "stage1_step1",
                                "displayName": "Stage1.Step1",
                                "description": "",
                                "state": "created",
                                "required": True,
                                "rules": [{"operation": "add", "component": "component", "service": "service"}],
                                "delta": {
                                    "add": [{"hostId": 1, "componentId": 1}],
                                    "remove": [{"hostId": 2, "componentId": 2}],
                                },
                                "cumulativeDelta": {
                                    "add": [{"hostId": 1, "componentId": 1}],
                                    "remove": [{"hostId": 2, "componentId": 2}],
                                },
                            },
                        ),
                    ],
                ),
                HTTP_404_NOT_FOUND: OpenApiResponse(description="Not found"),
            },
        ),
    )
