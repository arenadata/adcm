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

from api_v2.rbac.role.filters import RoleFilter
from api_v2.rbac.role.serializers import RoleSerializer
from api_v2.views import CamelCaseModelViewSet
from cm.errors import raise_adcm_ex
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rbac.models import Role
from rbac.services.role import role_create, role_update
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.permissions import DjangoModelPermissionsAudit


class RoleViewSet(PermissionListMixin, CamelCaseModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Role.objects.prefetch_related("child", "category").order_by("display_name")
    serializer_class = RoleSerializer
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ["rbac.view_role"]
    filterset_class = RoleFilter
    ordering_fields = ("id", "name", "display_name", "built_in", "type")

    def get_queryset(self, *args, **kwargs):
        return get_objects_for_user(**self.get_get_objects_for_user_kwargs(Role.objects.all()))

    def create(self, request, *args, **kwargs):
        children_roles = Role.objects.filter(id__in=[ids["id"] for ids in request.data["children"]])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["child"] = children_roles
        role_create(**serializer.validated_data)
        return Response(data=serializer.data, status=HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if instance.built_in:
            raise_adcm_ex(code="ROLE_UPDATE_ERROR", msg=f"Can't modify role {instance.name} as it is auto created")

        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        children_roles = Role.objects.filter(id__in=[ids["id"] for ids in request.data["children"]])
        serializer.validated_data["child"] = children_roles
        role = role_update(instance, partial, **serializer.validated_data)
        return Response(self.get_serializer(role).data, status=HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.built_in:
            raise_adcm_ex(code="ROLE_DELETE_ERROR")
        return super().destroy(request, *args, **kwargs)
