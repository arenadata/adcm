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

from audit.utils import audit
from guardian.mixins import PermissionListMixin
from rbac.endpoints.policy.serializers import PolicySerializer
from rbac.models import Policy
from rbac.services.policy import policy_create, policy_update
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import DjangoModelPermissionsAudit


class PolicyViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ["rbac.view_policy"]
    filterset_fields = ("id", "name", "built_in", "role", "group")
    ordering_fields = ("id", "name", "built_in", "role")

    @audit
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = policy_create(**serializer.validated_data)
        return Response(data=self.get_serializer(policy).data, status=HTTP_201_CREATED)

    @audit
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        policy = self.get_object()

        if policy.built_in:
            return Response(status=HTTP_409_CONFLICT)

        serializer = self.get_serializer(policy, data=request.data, partial=partial)
        if serializer.is_valid(raise_exception=True):
            policy = policy_update(policy, **serializer.validated_data)

            return Response(data=self.get_serializer(policy).data)
        else:
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)

    @audit
    def destroy(self, request, *args, **kwargs):
        policy = self.get_object()
        if policy.built_in:
            return Response(status=HTTP_409_CONFLICT)

        return super().destroy(request, *args, **kwargs)
