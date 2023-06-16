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
from cm.api import multi_bind
from cm.models import Cluster, ClusterObject
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import (
    CHANGE_IMPORT_PERM,
    VIEW_CLUSTER_BIND,
    VIEW_CLUSTER_PERM,
    VIEW_IMPORT_PERM,
    VIEW_SERVICE_PERM,
    check_custom_perm,
    get_object_for_user,
)


class ImportViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    ordering = ["id"]

    def get_serializer_class(self):
        if self.action == "create":
            return ImportPostSerializer

        return self.serializer_class

    def get_object_and_check_perm(self, request, **kwargs):
        raise NotImplementedError

    def list(self, request: Request, *args, **kwargs) -> Response:
        obj = self.get_object_and_check_perm(request=request, **kwargs)
        res = get_imports(obj=obj)

        return Response(data=res)

    def create(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        obj = self.get_object_and_check_perm(request=request, **kwargs)
        check_custom_perm(request.user, CHANGE_IMPORT_PERM, "cluster", obj)
        serializer = self.get_serializer(data=request.data, context={"request": request, "cluster": obj})
        if serializer.is_valid():
            bind_data = cook_data_for_multibind(validated_data=serializer.validated_data, obj=obj)

            if isinstance(obj, ClusterObject):
                multi_bind(cluster=obj.cluster, service=obj, bind_list=bind_data)
                return Response(get_imports(obj=obj), status=HTTP_200_OK)

            multi_bind(cluster=obj, service=None, bind_list=bind_data)
            return Response(get_imports(obj=obj), status=HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ClusterImportViewSet(ImportViewSet):
    def get_object_and_check_perm(self, request, **kwargs):
        cluster = get_object_for_user(request.user, VIEW_CLUSTER_PERM, Cluster, id=kwargs["cluster_pk"])
        check_custom_perm(request.user, VIEW_IMPORT_PERM, "cluster", cluster, VIEW_CLUSTER_BIND)
        return cluster


class ServiceImportViewSet(ImportViewSet):
    def get_object_and_check_perm(self, request, **kwargs):
        service = get_object_for_user(request.user, VIEW_SERVICE_PERM, ClusterObject, id=kwargs["clusterobject_pk"])
        check_custom_perm(request.user, VIEW_IMPORT_PERM, "clusterobject", service, VIEW_CLUSTER_BIND)
        return service
