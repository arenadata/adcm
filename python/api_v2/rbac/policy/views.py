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

from api_v2.rbac.policy.filters import PolicyFilter
from api_v2.rbac.policy.serializers import PolicyCreateSerializer, PolicySerializer
from api_v2.views import CamelCaseModelViewSet
from cm.errors import AdcmEx, raise_adcm_ex
from django_filters.rest_framework.backends import DjangoFilterBackend
from guardian.mixins import PermissionListMixin
from rbac.models import Policy
from rbac.services.policy import policy_create, policy_update
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from adcm.permissions import VIEW_POLICY_PERMISSION, CustomModelPermissionsByMethod


class PolicyViewSet(PermissionListMixin, CamelCaseModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Policy.objects.select_related("role").prefetch_related("group", "object")
    filter_backends = (DjangoFilterBackend,)
    filterset_class = PolicyFilter
    permission_classes = (CustomModelPermissionsByMethod,)
    method_permissions_map = {
        "patch": [(VIEW_POLICY_PERMISSION, NotFound)],
        "delete": [(VIEW_POLICY_PERMISSION, NotFound)],
    }
    permission_required = [VIEW_POLICY_PERMISSION]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self) -> type[PolicySerializer | PolicyCreateSerializer]:
        if self.action in ("create", "update", "partial_update"):
            return PolicyCreateSerializer

        return PolicySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = policy_create(**serializer.validated_data)
        return Response(data=PolicySerializer(policy).data, status=HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        policy = self.get_object()

        if policy.built_in:
            raise AdcmEx(code="POLICY_CREATE_ERROR")

        serializer = self.get_serializer(policy, data=request.data, partial=kwargs.pop("partial", False))
        serializer.is_valid(raise_exception=True)
        policy = policy_update(policy, **serializer.validated_data)
        return Response(data=PolicySerializer(policy).data)

    def destroy(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.built_in:
            return raise_adcm_ex(code="POLICY_DELETE_ERROR")

        return super().destroy(request, *args, **kwargs)
