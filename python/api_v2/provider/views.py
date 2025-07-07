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
from audit.alt.api import audit_create, audit_delete
from cm.api import add_host_provider, delete_host_provider
from cm.errors import AdcmEx
from cm.models import ObjectType, Prototype, Provider
from django.db.utils import IntegrityError
from django_filters.rest_framework.backends import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from guardian.mixins import PermissionListMixin
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.api_schema import responses
from api_v2.generic.action.api_schema import document_action_viewset
from api_v2.generic.action.audit import audit_action_viewset
from api_v2.generic.action.views import ActionViewSet
from api_v2.generic.config.api_schema import document_config_viewset
from api_v2.generic.config.audit import audit_config_viewset
from api_v2.generic.config.utils import ConfigSchemaMixin, extend_config_schema
from api_v2.generic.config.views import ConfigLogViewSet
from api_v2.generic.config_host_group.api_schema import (
    document_config_host_group_viewset,
    document_host_config_host_group_viewset,
)
from api_v2.generic.config_host_group.audit import (
    audit_config_config_host_group_viewset,
    audit_config_host_group_viewset,
    audit_host_config_host_group_viewset,
)
from api_v2.generic.config_host_group.views import CHGViewSet, HostCHGViewSet
from api_v2.generic.upgrade.api_schema import document_upgrade_viewset
from api_v2.generic.upgrade.audit import audit_upgrade_viewset
from api_v2.generic.upgrade.views import UpgradeViewSet
from api_v2.provider.filters import ProviderFilter
from api_v2.provider.permissions import ProviderPermissions
from api_v2.provider.serializers import (
    ProviderCreateSerializer,
    ProviderSchemaSerializer,
    ProviderSerializer,
)
from api_v2.utils.audit import parent_provider_from_lookup, provider_from_lookup, provider_from_response
from api_v2.views import ADCMGenericViewSet


@extend_schema_view(
    list=extend_schema(
        operation_id="getHostproviders",
        summary="GET hostproviders",
        description="Get a list of ADCM hostproviders with information on them.",
        parameters=[
            OpenApiParameter(
                name="ordering",
                description='Field to sort by. To sort in descending order, precede the attribute name with a "-".',
                enum=(
                    "name",
                    "-name",
                ),
                default="name",
            ),
        ],
        responses=responses(success=ProviderSchemaSerializer(many=True)),
    ),
    create=extend_schema(
        operation_id="postHostproviders",
        summary="POST hostproviders",
        description="Creation of a new ADCM hostprovider.",
        responses=responses(
            success=(HTTP_201_CREATED, ProviderSchemaSerializer), errors=(HTTP_403_FORBIDDEN, HTTP_409_CONFLICT)
        ),
    ),
    retrieve=extend_schema(
        operation_id="getHostprovider",
        summary="GET hostprovider",
        description="Get information about a specific hostprovider.",
        responses=responses(success=ProviderSerializer, errors=HTTP_404_NOT_FOUND),
    ),
    destroy=extend_schema(
        operation_id="deleteHostprovider",
        summary="DELETE hostprovider",
        description="Delete a specific ADCM hostprovider.",
        responses=responses(
            success=(HTTP_204_NO_CONTENT, None), errors=(HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
        ),
    ),
    config_schema=extend_config_schema("provider"),
)
class ProviderViewSet(PermissionListMixin, ConfigSchemaMixin, RetrieveModelMixin, ListModelMixin, ADCMGenericViewSet):
    queryset = Provider.objects.select_related("prototype").order_by("name")
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated, ProviderPermissions]
    permission_required = [VIEW_PROVIDER_PERM]
    filterset_class = ProviderFilter
    filter_backends = (DjangoFilterBackend,)

    def get_serializer_class(self):
        if self.action == "create":
            return ProviderCreateSerializer

        return self.serializer_class

    @audit_create(name="Provider created", object_=provider_from_response)
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

        return Response(data=ProviderSerializer(host_provider).data, status=HTTP_201_CREATED)

    @audit_delete(name="Provider deleted", object_=provider_from_lookup, removed_on_success=True)
    def destroy(self, request, *args, **kwargs):  # noqa: ARG002
        host_provider = self.get_object()
        delete_host_provider(host_provider)
        return Response(status=HTTP_204_NO_CONTENT)


@document_config_host_group_viewset(object_type="hostprovider")
@audit_config_host_group_viewset(retrieve_owner=parent_provider_from_lookup)
class ProviderCHGViewSet(CHGViewSet):
    ...


@document_host_config_host_group_viewset(object_type="hostprovider")
@audit_host_config_host_group_viewset(retrieve_owner=parent_provider_from_lookup)
class ProviderHostCHGViewSet(HostCHGViewSet):
    ...


@document_config_viewset(object_type="hostprovider config group", operation_id_variant="HostProviderConfigGroup")
@audit_config_config_host_group_viewset(retrieve_owner=parent_provider_from_lookup)
class ProviderConfigCHGViewSet(ConfigLogViewSet):
    ...


@document_action_viewset(object_type="hostprovider")
@audit_action_viewset(retrieve_owner=parent_provider_from_lookup)
class ProviderActionViewSet(ActionViewSet):
    ...


@document_config_viewset(object_type="hostprovider")
@audit_config_viewset(type_in_name="Provider", retrieve_owner=parent_provider_from_lookup)
class ProviderConfigViewSet(ConfigLogViewSet):
    ...


@document_upgrade_viewset(object_type="hostprovider")
@audit_upgrade_viewset(retrieve_owner=parent_provider_from_lookup)
class ProviderUpgradeViewSet(UpgradeViewSet):
    ...
