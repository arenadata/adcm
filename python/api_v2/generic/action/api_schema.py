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
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api_v2.api_schema import DefaultParams, responses
from api_v2.generic.action.serializers import ActionListSerializer, ActionRetrieveSerializer
from api_v2.task.serializers import TaskListSerializer

_schema_common_filters = (
    OpenApiParameter(
        name="name",
        required=False,
        location=OpenApiParameter.QUERY,
        description="System name of an action",
        type=str,
    ),
    OpenApiParameter(
        name="displayName",
        required=False,
        location=OpenApiParameter.QUERY,
        description="Visible name of an action",
        type=str,
    ),
)


def document_action_viewset(object_type: str, operation_id_variant: str | None = None):
    capitalized_type = operation_id_variant or object_type.capitalize()

    return extend_schema_view(
        run=extend_schema(
            operation_id=f"post{capitalized_type}Action",
            summary=f"POST {object_type}'s action",
            description=f"Run {object_type}'s action.",
            responses=responses(
                success=TaskListSerializer,
                errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
            ),
        ),
        list=extend_schema(
            operation_id=f"get{capitalized_type}Actions",
            summary=f"GET {object_type}'s actions",
            description=f"Get a list of {object_type}'s actions.",
            parameters=[
                DefaultParams.ordering_by("id"),
                OpenApiParameter(
                    name="name",
                    required=False,
                    location=OpenApiParameter.QUERY,
                    description="Case insensitive and partial filter by name.",
                    type=str,
                ),
                OpenApiParameter(
                    name="displayName",
                    required=False,
                    location=OpenApiParameter.QUERY,
                    description="Case insensitive and partial filter by display name.",
                    type=str,
                ),
                OpenApiParameter(
                    name="isHostOwnAction",
                    required=False,
                    location=OpenApiParameter.QUERY,
                    description="Filter for host's own actions / actions from another objects",
                    type=bool,
                ),
                OpenApiParameter(
                    name="prototypeId",
                    required=False,
                    location=OpenApiParameter.QUERY,
                    description="Identifier of action's owner",
                    type=int,
                ),
                OpenApiParameter(
                    name="description",
                    required=False,
                    location=OpenApiParameter.QUERY,
                    description="Case insensitive and partial filter by description.",
                    type=str,
                ),
                OpenApiParameter(
                    name="ordering",
                    description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                    type=str,
                    enum=(
                        "name",
                        "-name",
                        "id",
                        "-id",
                    ),
                    default="id",
                ),
                *_schema_common_filters,
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
