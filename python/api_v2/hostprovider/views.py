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

from adcm.permissions import VIEW_PROVIDER_PERM
from audit.utils import audit
from cm.api import add_host_provider, delete_host_provider
from cm.errors import AdcmEx
from cm.models import HostProvider, ObjectType, Prototype
from django.db.utils import IntegrityError
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from api_v2.api_schema import ErrorSerializer
from api_v2.config.utils import ConfigSchemaMixin
from api_v2.generic.group_config.api_schema import document_group_config_viewset, document_host_group_config_viewset
from api_v2.generic.group_config.audit import audit_group_config_viewset, audit_host_group_config_viewset
from api_v2.generic.group_config.views import GroupConfigViewSet, HostGroupConfigViewSet
from api_v2.hostprovider.filters import HostProviderFilter
from api_v2.hostprovider.permissions import HostProviderPermissions
from api_v2.hostprovider.serializers import (
    HostProviderCreateSerializer,
    HostProviderSerializer,
)
from api_v2.utils.audit import parent_hostprovider_from_lookup
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getHostproviders",
        summary="GET hostproviders",
        description="Get a list of ADCM hostproviders with information on them.",
        parameters=[
            OpenApiParameter(
                name="name",
                required=False,
                location=OpenApiParameter.QUERY,
                description="Case insensitive and partial filter by hostprovider name.",
                type=str,
            ),
            OpenApiParameter(
                name="prototypeName",
                required=False,
                location=OpenApiParameter.QUERY,
                description="Hostprovider prototype name.",
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                required=False,
                location=OpenApiParameter.QUERY,
                description="Field to sort by. To sort in descending order, precede the attribute name with a '-'.",
                type=str,
            ),
        ],
    ),
    create=extend_schema(
        operation_id="postHostproviders",
        summary="POST hostproviders",
        description="Creation of a new ADCM hostprovider.",
        responses={
            201: HostProviderSerializer,
            403: ErrorSerializer,
            409: ErrorSerializer,
        },
    ),
    retrieve=extend_schema(
        operation_id="getHostprovider",
        summary="GET hostprovider",
        description="Get information about a specific hostprovider.",
        parameters=[
            OpenApiParameter(
                name="hostproviderId",
                required=True,
                location=OpenApiParameter.QUERY,
                description="Hostprovider id.",
                type=int,
            ),
        ],
        responses={200: HostProviderSerializer, 404: ErrorSerializer},
    ),
    destroy=extend_schema(
        operation_id="deleteHostprovider",
        summary="DELETE hostprovider",
        description="Delete a specific ADCM hostprovider.",
        parameters=[
            OpenApiParameter(
                name="hostproviderId",
                required=True,
                location=OpenApiParameter.QUERY,
                description="Get information about a specific hostprovider.",
                type=int,
            ),
        ],
        responses={
            200: OpenApiResponse(description="OK"),
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    ),
)
class HostProviderViewSet(
    PermissionListMixin, ConfigSchemaMixin, RetrieveModelMixin, ListModelMixin, ADCMGenericViewSet
):
    queryset = HostProvider.objects.select_related("prototype").order_by("name")
    serializer_class = HostProviderSerializer
    permission_classes = [HostProviderPermissions]
    permission_required = [VIEW_PROVIDER_PERM]
    filterset_class = HostProviderFilter
    filter_backends = (DjangoFilterBackend,)

    def get_serializer_class(self):
        if self.action == "create":
            return HostProviderCreateSerializer

        return self.serializer_class

    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG001, ARG002
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            raise AdcmEx(code="HOSTPROVIDER_CREATE_ERROR")

        try:
            host_provider = add_host_provider(
                prototype=Prototype.objects.get(pk=serializer.validated_data["prototype_id"], type=ObjectType.PROVIDER),
                name=serializer.validated_data["name"],
                description=serializer.validated_data.get("description", ""),
            )
        except IntegrityError as e:
            raise AdcmEx(code="PROVIDER_CONFLICT") from e

        return Response(data=HostProviderSerializer(host_provider).data, status=HTTP_201_CREATED)

    @audit
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        host_provider = self.get_object()
        delete_host_provider(host_provider)
        return Response(status=HTTP_204_NO_CONTENT)


@document_group_config_viewset(object_type="hostprovider")
@audit_group_config_viewset(retrieve_owner=parent_hostprovider_from_lookup)
class HostProviderGroupConfigViewSet(GroupConfigViewSet):
    ...


@document_host_group_config_viewset(object_type="hostprovider")
@audit_host_group_config_viewset(retrieve_owner=parent_hostprovider_from_lookup)
class HostProviderHostGroupConfigViewSet(HostGroupConfigViewSet):
    ...
