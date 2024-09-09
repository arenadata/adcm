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

from abc import ABC, abstractmethod

from adcm.permissions import (
    CHANGE_IMPORT_PERM,
    VIEW_CLUSTER_BIND,
    check_custom_perm,
    get_object_for_user,
)
from cm.api import multi_bind
from cm.models import Cluster, ClusterObject, PrototypeImport
from django.db.transaction import atomic
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
)

from api_v2.generic.imports.serializers import ImportPostSerializer
from api_v2.generic.imports.utils import cook_data_for_multibind, get_imports
from api_v2.views import ADCMGenericViewSet


class ImportViewSet(ADCMGenericViewSet, ABC):
    queryset = PrototypeImport.objects.all()
    ordering = ["id"]
    filter_backends = []
    serializer_class = ImportPostSerializer

    @abstractmethod
    def detect_get_check_kwargs(self) -> tuple[dict, dict]:
        ...

    @abstractmethod
    def detect_cluster_service_bind_arguments(
        self, obj: Cluster | ClusterObject
    ) -> tuple[Cluster, ClusterObject | None]:
        ...

    def get_object_and_check_perm(self, request) -> Cluster | ClusterObject:
        kwargs_get, kwargs_check = self.detect_get_check_kwargs()

        if self.action == "list":
            kwargs_check.update({"second_perm": VIEW_CLUSTER_BIND})

        obj = get_object_for_user(user=request.user, **kwargs_get)

        check_custom_perm(user=request.user, obj=obj, **kwargs_check)

        if self.action == "create":
            check_custom_perm(
                user=request.user, action_type=CHANGE_IMPORT_PERM, model=obj.__class__.__name__.lower(), obj=obj
            )

        return obj

    def list(self, request: Request, *_, **__) -> Response:
        obj = self.get_object_and_check_perm(request=request)
        return self.get_paginated_response(data=self.paginate_queryset(queryset=get_imports(obj=obj)))

    @atomic
    def create(self, request, *_, **__):
        obj = self.get_object_and_check_perm(request=request)
        serializer = self.get_serializer(data=request.data, many=True, context={"request": request, "cluster": obj})
        serializer.is_valid(raise_exception=True)

        cluster, service = self.detect_cluster_service_bind_arguments(obj)
        multi_bind(
            cluster=cluster,
            service=service,
            bind_list=cook_data_for_multibind(validated_data=serializer.validated_data, obj=obj),
        )
        return Response(get_imports(obj=obj), status=HTTP_201_CREATED)
