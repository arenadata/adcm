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
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import DefaultParams, responses
from api_v2.generic.action.api_schema import document_action_viewset
from api_v2.generic.action_host_group.serializers import ActionHostGroupSerializer, ShortHostSerializer


def document_action_host_group_viewset(object_type: str):
    capitalized_type = object_type.capitalize()

    return extend_schema_view(
        create=extend_schema(
            operation_id=f"post{capitalized_type}ActionHostGroup",
            summary=f"POST {object_type}'s Action Host Group",
            description=f"Create a new {object_type}'s action host group.",
            responses=responses(
                success=(HTTP_201_CREATED, ActionHostGroupSerializer),
                errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
            ),
        ),
        list=extend_schema(
            operation_id=f"get{capitalized_type}ActionHostGroups",
            summary=f"GET {object_type}'s Action Host Groups",
            description=f"Return list of {object_type}'s action host groups.",
            responses=responses(
                success=ActionHostGroupSerializer(many=True), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)
            ),
        ),
        retrieve=extend_schema(
            operation_id=f"get{capitalized_type}ActionHostGroup",
            summary=f"GET {object_type}'s Action Host Group",
            description=f"Return information about specific {object_type}'s action host group.",
            responses=responses(success=ActionHostGroupSerializer, errors=HTTP_404_NOT_FOUND),
        ),
        destroy=extend_schema(
            operation_id=f"delete{capitalized_type}ActionHostGroup",
            summary=f"DELETE {object_type}'s Action Host Group",
            description=f"Delete specific {object_type}'s action host group.",
            responses=responses(success=(HTTP_204_NO_CONTENT, None), errors=(HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)),
        ),
        host_candidate=extend_schema(
            operation_id=f"get{capitalized_type}ActionHostGroupCandidates",
            summary=f"GET {object_type}'s Action Host Group's host candidates",
            description=f"Return list of {object_type}'s hosts that can be added to action host group.",
            responses=responses(success=ShortHostSerializer(many=True), errors=HTTP_404_NOT_FOUND),
        ),
        owner_host_candidate=extend_schema(
            operation_id=f"get{capitalized_type}ActionHostGroupOwnCandidates",
            summary=f"GET {object_type}'s host candidates for new Action Host Group",
            description=f"Return list of {object_type}'s hosts that can be added to newly created action host group.",
            responses=responses(
                success=ShortHostSerializer(many=True), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND)
            ),
        ),
    )


def document_action_host_group_hosts_viewset(object_type: str):
    capitalized_type = object_type.capitalize()

    return extend_schema_view(
        list=extend_schema(
            operation_id=f"get{capitalized_type}ActionHostGroupHosts",
            description=f"Get information about {object_type}'s Action Host Group hosts.",
            summary="GET {object_type}'s action host group hosts.",
            parameters=[
                DefaultParams.ordering_by("name"),
                OpenApiParameter(
                    name="name",
                    location=OpenApiParameter.QUERY,
                    description="Case insensitive and partial filter by host name.",
                    type=str,
                ),
            ],
            responses=responses(success=ShortHostSerializer(many=True), errors=HTTP_403_FORBIDDEN),
        ),
        create=extend_schema(
            operation_id=f"post{capitalized_type}ActionHostGroupHosts",
            summary=f"POST {object_type}'s Action Host Group hosts",
            description=f"Add hosts to {object_type}'s action host group.",
            responses=responses(
                success=(HTTP_201_CREATED, ShortHostSerializer),
                errors=(HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT),
            ),
        ),
        destroy=extend_schema(
            operation_id=f"delete{capitalized_type}ActionHostGroupHosts",
            summary=f"DELETE {object_type}'s Action Host Group hosts",
            description=f"Delete specific host from {object_type}'s action host group.",
            responses=responses(success=(HTTP_204_NO_CONTENT, None), errors=(HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)),
        ),
    )


def document_action_host_group_actions_viewset(object_type: str):
    return document_action_viewset(
        object_type=f"{object_type}'s action host group",
        operation_id_variant=f"{object_type.capitalize()}ActionHostGroup",
    )
