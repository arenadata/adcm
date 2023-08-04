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
from api_v2.views import CamelCaseReadOnlyModelViewSet
from cm.api import multi_bind
from cm.models import Cluster, ClusterObject, PrototypeImport
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from adcm.permissions import (
    CHANGE_IMPORT_PERM,
    VIEW_CLUSTER_BIND,
    VIEW_CLUSTER_PERM,
    VIEW_IMPORT_PERM,
    VIEW_SERVICE_PERM,
    check_custom_perm,
    get_object_for_user,
)


class ImportViewSet(CamelCaseReadOnlyModelViewSet):  # pylint: disable=too-many-ancestors
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
                "model": ClusterObject.__class__.__name__.lower(),
                "second_perm": VIEW_CLUSTER_BIND,
            }
        else:
            kwargs_get = {"perms": VIEW_CLUSTER_PERM, "klass": Cluster, "id": self.kwargs["cluster_pk"]}
            kwargs_check = {
                "action_type": VIEW_IMPORT_PERM,
                "model": Cluster.__class__.__name__.lower(),
                "second_perm": VIEW_CLUSTER_BIND,
            }

        obj = get_object_for_user(user=request.user, **kwargs_get)
        check_custom_perm(user=request.user, obj=obj, **kwargs_check)

        return obj

    def list(self, request: Request, *args, **kwargs) -> Response:
        obj = self.get_object_and_check_perm(request=request)

        return Response(data=get_imports(obj=obj))

    def create(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        obj = self.get_object_and_check_perm(request=request)
        check_custom_perm(request.user, CHANGE_IMPORT_PERM, "cluster", obj)
        serializer = self.get_serializer(data=request.data, many=True, context={"request": request, "cluster": obj})

        if serializer.is_valid():
            bind_data = cook_data_for_multibind(validated_data=serializer.validated_data, obj=obj)

            if isinstance(obj, ClusterObject):
                multi_bind(cluster=obj.cluster, service=obj, bind_list=bind_data)
                return Response(get_imports(obj=obj), status=HTTP_200_OK)

            multi_bind(cluster=obj, service=None, bind_list=bind_data)
            return Response(get_imports(obj=obj), status=HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
