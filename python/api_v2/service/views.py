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
from adcm.permissions import (
    ADD_SERVICE_PERM,
    CHANGE_MM_PERM,
    VIEW_CLUSTER_PERM,
    VIEW_SERVICE_PERM,
    ChangeMMPermissions,
    check_custom_perm,
    get_object_for_user,
)
from adcm.utils import delete_service_from_api, get_maintenance_mode_response
from audit.utils import audit
from cm.api import update_mm_objects
from cm.models import Cluster, ClusterObject
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from api_v2.config.utils import ConfigSchemaMixin
from api_v2.service.filters import ServiceFilter
from api_v2.service.permissions import ServicePermissions
from api_v2.service.serializers import (
    ServiceCreateSerializer,
    ServiceMaintenanceModeSerializer,
    ServiceRetrieveSerializer,
    ServiceStatusSerializer,
)
from api_v2.service.utils import (
    bulk_add_services_to_cluster,
    validate_service_prototypes,
)
from api_v2.views import CamelCaseGenericViewSet


class ServiceViewSet(
    PermissionListMixin,
    ConfigSchemaMixin,
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    CamelCaseGenericViewSet,
):
    queryset = ClusterObject.objects.select_related("cluster").order_by("pk")
    serializer_class = ServiceRetrieveSerializer
    filterset_class = ServiceFilter
    filter_backends = (DjangoFilterBackend,)
    permission_required = [VIEW_SERVICE_PERM]
    permission_classes = [ServicePermissions]
    audit_model_hint = ClusterObject

    def get_queryset(self, *args, **kwargs):
        cluster = get_object_for_user(
            user=self.request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, id=self.kwargs["cluster_pk"]
        )

        return super().get_queryset(*args, **kwargs).filter(cluster=cluster)

    def get_serializer_class(self):
        match self.action:
            case "create":
                return ServiceCreateSerializer
            case "maintenance_mode":
                return ServiceMaintenanceModeSerializer

        return self.serializer_class

    @audit
    def create(self, request: Request, *args, **kwargs):  # noqa: ARG002
        cluster = get_object_for_user(
            user=request.user, perms=VIEW_CLUSTER_PERM, klass=Cluster, pk=kwargs["cluster_pk"]
        )
        check_custom_perm(user=request.user, action_type=ADD_SERVICE_PERM, model=Cluster.__name__.lower(), obj=cluster)

        multiple_services = isinstance(request.data, list)
        serializer = self.get_serializer(
            data=request.data, many=multiple_services, context={"cluster": cluster, **self.get_serializer_context()}
        )
        serializer.is_valid(raise_exception=True)

        service_prototypes, error = validate_service_prototypes(
            cluster=cluster, data=serializer.validated_data if multiple_services else [serializer.validated_data]
        )
        if error is not None:
            raise error
        added_services = bulk_add_services_to_cluster(cluster=cluster, prototypes=service_prototypes)

        if multiple_services:
            return Response(
                status=HTTP_201_CREATED, data=ServiceRetrieveSerializer(instance=added_services, many=True).data
            )

        return Response(status=HTTP_201_CREATED, data=ServiceRetrieveSerializer(instance=added_services[0]).data)

    @audit
    def destroy(self, request: Request, *args, **kwargs):  # noqa: ARG002
        instance = self.get_object()
        return delete_service_from_api(service=instance)

    @audit
    @update_mm_objects
    @action(methods=["post"], detail=True, url_path="maintenance-mode", permission_classes=[ChangeMMPermissions])
    def maintenance_mode(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        service = get_object_for_user(user=request.user, perms=VIEW_SERVICE_PERM, klass=ClusterObject, pk=kwargs["pk"])
        check_custom_perm(
            user=request.user, action_type=CHANGE_MM_PERM, model=service.__class__.__name__.lower(), obj=service
        )

        serializer = self.get_serializer_class()(instance=service, data=request.data)
        serializer.is_valid(raise_exception=True)

        response: Response = get_maintenance_mode_response(obj=self.get_object(), serializer=serializer)
        if response.status_code == HTTP_200_OK:
            response.data = serializer.data

        return response

    @action(methods=["get"], detail=True, url_path="statuses")
    def statuses(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG001, ARG002
        service = get_object_for_user(user=request.user, perms=VIEW_SERVICE_PERM, klass=ClusterObject, id=kwargs["pk"])

        return Response(data=ServiceStatusSerializer(instance=service).data)
