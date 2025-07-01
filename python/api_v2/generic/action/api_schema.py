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

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api_v2.api_schema import responses
from api_v2.generic.action.serializers import ActionListSerializer, ActionRetrieveSerializer
from api_v2.task.serializers import TaskListSerializer


def document_action_viewset(object_type: str, operation_id_variant: str | None = None):
    capitalized_type = operation_id_variant or object_type.capitalize()

    return extend_schema_view(
        run=extend_schema(
            operation_id=f"post{capitalized_type}Action",
            summary=f"POST {object_type}'s action",
            description=f"Run {object_type}'s action.",
            responses=responses(
                success=TaskListSerializer, errors=(HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            ),
        ),
        list=extend_schema(
            operation_id=f"get{capitalized_type}Actions",
            summary=f"GET {object_type}'s actions",
            description=f"Get a list of {object_type}'s actions.",
            parameters=[
                OpenApiParameter(
                    name="ordering",
                    description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                    enum=(
                        "id",
                        "-id",
                    ),
                    default="id",
                ),
            ],
            responses=responses(success=ActionListSerializer, errors=HTTP_404_NOT_FOUND),
        ),
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}Action",
            summary=f"GET {object_type}'s action",
            description=f"Get information about a specific {object_type}'s action.",
            responses=responses(success=ActionRetrieveSerializer, errors=HTTP_404_NOT_FOUND),
        ),
    )
