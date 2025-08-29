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

from uuid import uuid4

from cm.services.wizard.schema_validation import ProcessOperationType
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
from api_v2.generic.wizard.serializers import ProcessSerializer


class Step(Serializer):
    id = IntegerField()
    display_name = CharField()
    type = CharField()
    state = CharField()


class StepConfigurationInternals(Serializer):
    config_schema = DictField()
    config = DictField()
    adcm_meta = DictField()


class StepConfiguration(Step):
    configuration = StepConfigurationInternals()


class StepOperation(Step):
    ui_options = DictField()
    task = DictField(allow_null=True, required=False)


class ParamsSerializer(Serializer):
    step_id = IntegerField()
    process_sync_key = UUIDField()


class CompleteParamsSerializer(Serializer):
    sync_key = UUIDField()


class SubmitConfig(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.SUBMIT, "submit with configuration")])
    configuration = DictField()
    params = ParamsSerializer(required=True)


class SubmitOperation(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.SUBMIT, "submit for operation")])
    params = ParamsSerializer(required=True)


class ResetOperation(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.RESET, ProcessOperationType.RESET)])
    params = ParamsSerializer(required=True)


class CompleteOperation(Serializer):
    method = ChoiceField(choices=[(ProcessOperationType.COMPLETE, ProcessOperationType.COMPLETE)])
    params = CompleteParamsSerializer(required=True)


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
                "displayName": "First stage",
                "steps": [{"id": 1, "displayName": "Stage1.Step1", "type": "configuration"}],
            },
            {
                "displayName": "Second stage",
                "steps": [
                    {"id": 2, "displayName": "Stage2.Step1", "type": "configuration"},
                    {"id": 3, "displayName": "Stage2.Step2", "type": "operation"},
                ],
            },
            {
                "displayName": "Third stage",
                "steps": [{"id": 4, "displayName": "Stage3.Step1", "type": "operation"}],
            },
            {
                "displayName": "Fourth stage",
                "steps": [
                    {"id": 5, "displayName": "Stage4.Step1", "type": "operation"},
                    {"id": 6, "displayName": "Stage4.Step2", "type": "operation"},
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
                        "configuration": {"config": {"new": "config"}, "adcmMeta": {}},
                        "method": ProcessOperationType.SUBMIT.value,
                        "params": {"step_id": 1, "process_sync_key": uuid4()},
                    },
                ),
                OpenApiExample(
                    "Submit operation",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.SUBMIT.value,
                        "params": {"step_id": 1, "process_sync_key": uuid4()},
                    },
                ),
                OpenApiExample(
                    "Reset operation",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.RESET.value,
                        "params": {"step_id": 1, "process_sync_key": uuid4()},
                    },
                ),
                OpenApiExample(
                    "Complete operation",
                    request_only=True,
                    value={
                        "method": ProcessOperationType.COMPLETE.value,
                        "params": {},
                    },
                ),
            ],
            request=PolymorphicProxySerializer(
                component_name=f"{object_type}Process",
                serializers=[SubmitConfig, SubmitOperation, ResetOperation, CompleteOperation],
                resource_type_field_name="method",
            ),
            responses={
                HTTP_200_OK: OpenApiResponse(
                    response=PolymorphicProxySerializer(
                        component_name=f"{object_type}Process",
                        serializers=[
                            ProcessSerializer,
                        ],
                        resource_type_field_name=None,
                    ),
                    examples=[example_process],
                ),
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
                        ],
                        resource_type_field_name="type",
                    ),
                    examples=[
                        OpenApiExample(
                            "Operation step",
                            value={
                                "displayName": "Stage2.Step2",
                                "id": 1,
                                "state": "created",
                                "task": None,
                                "type": "operation",
                                "uiOptions": {"buttonName": "ButtonName"},
                            },
                        ),
                        OpenApiExample(
                            "Configuration step",
                            value={
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
                                "displayName": "Stage1.Step1",
                                "id": 1,
                                "state": "created",
                                "type": "configuration",
                            },
                        ),
                    ],
                ),
                HTTP_404_NOT_FOUND: OpenApiResponse(description="Not found"),
            },
        ),
    )
