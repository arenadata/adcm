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
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, responses
from api_v2.generic.config_host_group.serializers import CHGSerializer, HostCHGSerializer
from api_v2.host.serializers import HostShortSerializer


def document_config_host_group_viewset(object_type: str):
    capitalized_type = object_type.capitalize()

    return extend_schema_view(
        list=extend_schema(
            operation_id=f"get{capitalized_type}ConfigGroups",
            summary=f"GET {object_type}'s config groups",
            description=f"Get information about {object_type}'s config-groups.",
            parameters=[
                DefaultParams.LIMIT,
                DefaultParams.OFFSET,
            ],
            responses=responses(success=(HTTP_200_OK, CHGSerializer(many=True)), errors=HTTP_404_NOT_FOUND),
        ),
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}ConfigGroup",
            summary=f"GET {object_type}'s config group",
            description=f"Get information about {object_type}'s config-group.",
            responses=responses(success=(HTTP_200_OK, CHGSerializer), errors=HTTP_404_NOT_FOUND),
        ),
        create=extend_schema(
            operation_id=f"post{capitalized_type}ConfigGroups",
            summary=f"POST {object_type}'s config-groups",
            description=f"Create new {object_type}'s config-group.",
            responses=responses(success=(HTTP_200_OK, CHGSerializer), errors=HTTP_404_NOT_FOUND),
        ),
        partial_update=extend_schema(
            operation_id=f"patch{capitalized_type}ConfigGroup",
            summary=f"PATCH {object_type}'s config-group",
            description=f"Change {object_type}'s config-group's name and description.",
            responses=responses(success=(HTTP_200_OK, CHGSerializer), errors=HTTP_404_NOT_FOUND),
        ),
        destroy=extend_schema(
            operation_id=f"delete{capitalized_type}ConfigGroup",
            summary=f"DELETE {object_type}'s config-group",
            description=f"Delete specific {object_type}'s config-group.",
            responses=responses(success=(HTTP_204_NO_CONTENT, None), errors=HTTP_404_NOT_FOUND),
        ),
        host_candidates=extend_schema(
            operation_id=f"get{capitalized_type}ConfigGroupHostCandidates",
            summary=f"GET {object_type}'s config-group host candidates",
            description=f"Get a list of hosts available for adding to {object_type}'s config group.",
            parameters=[
                OpenApiParameter(
                    name="name",
                    description="Case insensitive and partial filter by host name.",
                ),
                OpenApiParameter(
                    name="hostprovider_name",
                    description="Filter by hostprovider name.",
                ),
                OpenApiParameter(
                    name="ordering",
                    description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                    enum=(
                        "name",
                        "-name",
                        "state",
                        "-state",
                        "id",
                        "-id",
                        "hostproviderName",
                        "-hostproviderName",
                    ),
                    default="name",
                ),
            ],
            responses=responses(success=(HTTP_200_OK, HostCHGSerializer(many=True)), errors=HTTP_404_NOT_FOUND),
        ),
        owner_host_candidates=extend_schema(
            operation_id=f"get{capitalized_type}ConfigGroupHostOwnCandidates",
            summary=f"GET {object_type}'s host candidates for new config group",
            description=f"Get a list of hosts available for adding to {object_type}'s new config group.",
            parameters=[
                OpenApiParameter(
                    name="name",
                    description="Case insensitive and partial filter by host name.",
                ),
                OpenApiParameter(
                    name="hostprovider_name",
                    description="Filter by hostprovider name.",
                ),
                OpenApiParameter(
                    name="ordering",
                    description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                    enum=(
                        "name",
                        "-name",
                        "state",
                        "-state",
                        "id",
                        "-id",
                        "hostproviderName",
                        "-hostproviderName",
                    ),
                    default="name",
                ),
            ],
            responses=responses(success=(HTTP_200_OK, HostShortSerializer(many=True)), errors=HTTP_404_NOT_FOUND),
        ),
    )


def document_host_config_host_group_viewset(object_type: str):
    capitalized_type = object_type.capitalize()

    return extend_schema_view(
        list=extend_schema(
            operation_id=f"get{capitalized_type}ConfigGroupHosts",
            summary=f"GET {object_type}'s config-group hosts",
            description=f"Get a list of hosts added to {object_type}'s config-group.",
            parameters=[
                OpenApiParameter(
                    name="name",
                    description="Case insensitive and partial filter by host name.",
                ),
                OpenApiParameter(
                    name="hostprovider_name",
                    description="Filter by hostprovider name.",
                ),
                OpenApiParameter(
                    name="ordering",
                    description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                    enum=(
                        "name",
                        "-name",
                        "state",
                        "-state",
                        "id",
                        "-id",
                        "hostproviderName",
                        "-hostproviderName",
                    ),
                    default="name",
                ),
            ],
            responses=responses(success=(HTTP_200_OK, HostCHGSerializer(many=True)), errors=HTTP_404_NOT_FOUND),
        ),
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}ConfigGroupHost",
            summary=f"GET {object_type}'s config-group host",
            description=f"Get information about a specific host of {object_type}'s config-group.",
            responses=responses(success=(HTTP_200_OK, HostCHGSerializer(many=True)), errors=HTTP_404_NOT_FOUND),
        ),
        create=extend_schema(
            operation_id=f"post{capitalized_type}ConfigGroupHosts",
            summary=f"POST {object_type}'s config-group host",
            description=f"Add host to {object_type}'s config-group.",
            responses=responses(
                success=(HTTP_201_CREATED, HostCHGSerializer),
                errors=(HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT, HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN),
            ),
        ),
        destroy=extend_schema(
            operation_id=f"delete{capitalized_type}ConfigGroupHosts",
            summary=f"DELETE host from {object_type}'s config-group",
            description=f"Remove host from {object_type}'s config-group.",
            responses=responses(success=(HTTP_204_NO_CONTENT, None), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)),
        ),
    )
