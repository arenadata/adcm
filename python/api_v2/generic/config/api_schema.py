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

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from api_v2.api_schema import DefaultParams, responses
from api_v2.generic.config.serializers import ConfigLogListSerializer, ConfigLogSerializer


def document_config_viewset(object_type: str, operation_id_variant: str | None = None):
    capitalized_type = operation_id_variant or object_type.capitalize()

    return extend_schema_view(
        list=extend_schema(
            operation_id=f"get{capitalized_type}Configs",
            summary=f"GET {object_type}'s config versions",
            description=f"Get information about {object_type}'s config versions.",
            responses=responses(success=ConfigLogListSerializer, errors=HTTP_404_NOT_FOUND),
            parameters=[
                DefaultParams.LIMIT,
                DefaultParams.OFFSET,
                DefaultParams.ordering_by("id"),
                OpenApiParameter(
                    name="id",
                    type=int,
                    location=OpenApiParameter.PATH,
                    description="Config id.",
                ),
                OpenApiParameter(
                    name="description",
                    type=str,
                    location=OpenApiParameter.QUERY,
                    description="Case insensitive and partial filter by description.",
                ),
                OpenApiParameter(
                    name="ordering",
                    type=OpenApiTypes.STR,
                    location=OpenApiParameter.QUERY,
                    description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                    required=False,
                    enum=("description", "id", "-description", "-id"),
                    default="-id",
                ),
            ],
        ),
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}Config",
            summary=f"GET {object_type}'s config",
            description=f"Get {object_type}'s configuration information.",
            responses=responses(success=ConfigLogSerializer, errors=HTTP_404_NOT_FOUND),
        ),
        create=extend_schema(
            operation_id=f"post{capitalized_type}Configs",
            summary=f"POST {object_type}'s configs",
            description=f"Create a new version of {object_type}'s configuration.",
            responses=responses(
                success=ConfigLogSerializer, errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_409_CONFLICT)
            ),
        ),
    )
