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

from typing import Iterable, TypeAlias

from adcm.serializers import EmptySerializer
from drf_spectacular.utils import OpenApiExample, OpenApiParameter
from rest_framework.fields import CharField
from rest_framework.serializers import Serializer
from rest_framework.status import (
    HTTP_200_OK,
)


class ErrorSerializer(EmptySerializer):
    code = CharField()
    level = CharField()
    desc = CharField()


class DefaultParams:
    LIMIT = OpenApiParameter(name="limit", description="Number of records included in the selection.", type=int)
    OFFSET = OpenApiParameter(name="offset", description="Record number from which the selection starts.", type=int)
    _CONCERN_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "type": {"type": "string"},
                "reason": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "placeholder": {"type": "object"},
                    },
                },
                "isBlocking": {"type": "boolean"},
                "cause": {"type": "string"},
                "owner": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "type": {"type": "string"}},
                },
            },
        },
    }
    CONFIG_SCHEMA_EXAMPLE = [
        OpenApiExample(
            name="schema example",
            value={
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Configuration",
                "description": "",
                "readOnly": False,
                "adcmMeta": {
                    "isAdvanced": False,
                    "isInvisible": False,
                    "activation": None,
                    "synchronization": None,
                    "nullValue": None,
                    "isSecret": False,
                    "stringExtra": None,
                    "enumExtra": None,
                },
                "type": "object",
                "properties": {
                    "param_1": {
                        "title": "Special Param",
                        "type": "string",
                        "description": "",
                        "default": "heh",
                        "readOnly": True,
                        "adcmMeta": {"isAdvanced": True, "isInvisible": False},
                    }
                },
                "additionalProperties": False,
                "required": [],
            },
            response_only=True,
        )
    ]
    ADD_HOST_TO_CLUSTER_RESPONSE_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "hostprovider": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "displayName": {"type": "string"},
                    },
                },
                "prototype": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "displayName": {"type": "string"},
                        "version": {"type": "string"},
                    },
                },
                "cluster": {"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}},
                "status": {"type": "string"},
                "state": {"type": "string"},
                "multiState": {"type": "array", "items": {"type": "string"}},
                "concerns": _CONCERN_SCHEMA,
                "isMaintenanceModeAvailable": {"type": "boolean"},
                "maintenanceMode": {"type": "string"},
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "displayName": {"type": "string"},
                        },
                    },
                },
            },
        },
    }
    ADD_SERVICE_TO_CLUSTER_RESPONSE_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "displayName": {"type": "string"},
                "prototype": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "displayName": {"type": "string"},
                        "version": {"type": "string"},
                    },
                },
                "cluster": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                },
                "status": {"type": "string"},
                "state": {"type": "string"},
                "multiState": {"type": "array", "items": {"type": "string"}},
                "concerns": _CONCERN_SCHEMA,
                "isMaintenanceModeAvailable": {"type": "boolean"},
                "maintenanceMode": {"type": "string"},
                "mainInfo": {"type": "string"},
            },
        },
    }


ResponseOKType: TypeAlias = Serializer | type[Serializer] | type[dict] | type[list] | None


def responses(
    success: ResponseOKType | tuple[int, ResponseOKType], errors: Iterable[int] | int
) -> dict[int, Serializer]:
    if not isinstance(success, tuple):
        success = (HTTP_200_OK, success)

    if isinstance(errors, int):
        errors = (errors,)

    return {success[0]: success[1]} | {status: ErrorSerializer for status in errors}
