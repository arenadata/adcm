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

from api_v2.imports.serializers import ImportPostSerializer
from api_v2.imports.utils import cook_data_for_multibind, get_imports
from api_v2.views import CamelCaseGenericViewSet
from cm.api import multi_bind
from cm.models import Cluster, ClusterObject, PrototypeImport
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from adcm.permissions import (
    CHANGE_IMPORT_PERM,
    VIEW_CLUSTER_BIND,
    VIEW_CLUSTER_PERM,
    VIEW_IMPORT_PERM,
    VIEW_SERVICE_PERM,
    check_custom_perm,
    get_object_for_user,
)


class ImportViewSet(ListModelMixin, CreateModelMixin, CamelCaseGenericViewSet):  # pylint: disable=too-many-ancestors
    queryset = PrototypeImport.objects.all()
    permission_classes = [IsAuthenticated]
    ordering = ["id"]
    filter_backends = []
    serializer_class = ImportPostSerializer

    def get_object_and_check_perm(self, request) -> Cluster | ClusterObject:
        if "cluster_pk" in self.kwargs and "service_pk" in self.kwargs:
            kwargs_get = {"perms": VIEW_SERVICE_PERM, "klass": ClusterObject, "id": self.kwargs["service_pk"]}
            kwargs_check = {
                "action_type": VIEW_IMPORT_PERM,
                "model": ClusterObject.__name__.lower(),
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

    def list(self, request: Request, *args, **kwargs) -> Response:
        obj = self.get_object_and_check_perm(request=request)
        return self.get_paginated_response(data=self.paginate_queryset(queryset=get_imports(obj=obj)))

    def create(self, request, *args, **kwargs):
        obj = self.get_object_and_check_perm(request=request)
        serializer = self.get_serializer(data=request.data, many=True, context={"request": request, "cluster": obj})
        serializer.is_valid(raise_exception=True)

        bind_data = cook_data_for_multibind(validated_data=serializer.validated_data, obj=obj)

        if isinstance(obj, ClusterObject):
            multi_bind(cluster=obj.cluster, service=obj, bind_list=bind_data)
            return Response(get_imports(obj=obj), status=HTTP_201_CREATED)

        multi_bind(cluster=obj, service=None, bind_list=bind_data)
        return Response(get_imports(obj=obj), status=HTTP_201_CREATED)
