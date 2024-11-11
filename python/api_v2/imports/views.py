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
    CHANGE_IMPORT_PERM,
    VIEW_CLUSTER_BIND,
    VIEW_CLUSTER_PERM,
    VIEW_IMPORT_PERM,
    VIEW_SERVICE_PERM,
    check_custom_perm,
    get_object_for_user,
)
from api_v2.api_schema import DefaultParams, ErrorSerializer
from api_v2.generic.imports.serializers import ImportPostSerializer, ImportSerializer
from api_v2.generic.imports.utils import cook_data_for_multibind, get_imports
from api_v2.views import ADCMGenericViewSet
from audit.utils import audit
from cm.api import multi_bind
from cm.models import Cluster, PrototypeImport, Service
from django.db.transaction import atomic
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class ImportViewSet(ListModelMixin, CreateModelMixin, ADCMGenericViewSet):
    queryset = PrototypeImport.objects.all()
    permission_classes = [IsAuthenticated]
    ordering = ["id"]
    filter_backends = []
    serializer_class = ImportPostSerializer

    def get_object_and_check_perm(self, request) -> Cluster | Service:
        if "cluster_pk" in self.kwargs and "service_pk" in self.kwargs:
            kwargs_get = {"perms": VIEW_SERVICE_PERM, "klass": Service, "id": self.kwargs["service_pk"]}
            kwargs_check = {
                "action_type": VIEW_IMPORT_PERM,
                "model": Service.__name__.lower(),
            }
        else:
            kwargs_get = {"perms": VIEW_CLUSTER_PERM, "klass": Cluster, "id": self.kwargs["cluster_pk"]}
            kwargs_check = {
                "action_type": VIEW_IMPORT_PERM,
                "model": Cluster.__name__.lower(),
            }

        if self.action in {"list", "retrieve"}:
            kwargs_check.update({"second_perm": VIEW_CLUSTER_BIND})

        obj = get_object_for_user(user=request.user, **kwargs_get)

        check_custom_perm(user=request.user, obj=obj, **kwargs_check)

        if self.action == "create":
            check_custom_perm(
                user=request.user, action_type=CHANGE_IMPORT_PERM, model=obj.__class__.__name__.lower(), obj=obj
            )

        return obj

    def list(self, request: Request, *args, **kwargs) -> Response:  # noqa: ARG002
        obj = self.get_object_and_check_perm(request=request)
        return self.get_paginated_response(data=self.paginate_queryset(queryset=get_imports(obj=obj)))

    @audit
    @atomic
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        obj = self.get_object_and_check_perm(request=request)
        serializer = self.get_serializer(data=request.data, many=True, context={"request": request, "cluster": obj})
        serializer.is_valid(raise_exception=True)

        bind_data = cook_data_for_multibind(validated_data=serializer.validated_data, obj=obj)

        if isinstance(obj, Service):
            multi_bind(cluster=obj.cluster, service=obj, bind_list=bind_data)
            return Response(get_imports(obj=obj), status=HTTP_201_CREATED)

        multi_bind(cluster=obj, service=None, bind_list=bind_data)
        return Response(get_imports(obj=obj), status=HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        operation_id="getClusterImports",
        description="Get information about cluster imports.",
        summary="GET cluster imports",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
        ],
        responses={
            HTTP_200_OK: ImportSerializer(many=True),
            HTTP_403_FORBIDDEN: ErrorSerializer,
        },
    ),
    create=extend_schema(
        operation_id="postClusterImports",
        description="Import data.",
        summary="POST cluster imports",
        responses={
            HTTP_201_CREATED: ImportPostSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
)
class ClusterImportViewSet(ImportViewSet):
    pass


@extend_schema_view(
    list=extend_schema(
        operation_id="getServiceImports",
        description="Get information about service imports.",
        summary="GET service imports",
        parameters=[
            DefaultParams.LIMIT,
            DefaultParams.OFFSET,
        ],
        responses={
            HTTP_200_OK: ImportSerializer(many=True),
            HTTP_403_FORBIDDEN: ErrorSerializer,
        },
    ),
    create=extend_schema(
        operation_id="postServiceImports",
        description="Import data.",
        summary="POST service imports",
        responses={
            HTTP_201_CREATED: ImportPostSerializer,
            **{
                err_code: ErrorSerializer
                for err_code in (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)
            },
        },
    ),
)
class ServiceImportViewSet(ImportViewSet):
    pass
