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
from api_v2.rbac.role.serializers import RoleCreateUpdateSerializer, RoleSerializer
from api_v2.views import CamelCaseModelViewSet
from cm.errors import raise_adcm_ex
from cm.models import ProductCategory
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rbac.models import Role
from rbac.services.role import role_create, role_update
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.permissions import DjangoModelPermissionsAudit


class RoleViewSet(PermissionListMixin, CamelCaseModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Role.objects.prefetch_related("child", "category").order_by("display_name")
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ["rbac.view_role"]
    filterset_class = RoleFilter

    def get_queryset(self, *args, **kwargs):
        return get_objects_for_user(**self.get_get_objects_for_user_kwargs(Role.objects.all()))

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RoleCreateUpdateSerializer

        return RoleSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = role_create(**serializer.validated_data)

        return Response(data=RoleSerializer(instance=role).data, status=HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if instance.built_in:
            raise_adcm_ex(code="ROLE_UPDATE_ERROR", msg=f"Can't modify role {instance.name} as it is auto created")

        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        role = role_update(role=instance, partial=partial, **serializer.validated_data)

        return Response(data=RoleSerializer(instance=role).data, status=HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.built_in:
            raise_adcm_ex(code="ROLE_DELETE_ERROR", msg="It is forbidden to remove the built-in role.")

        return super().destroy(request, *args, **kwargs)

    @action(methods=["get"], detail=False)
    def categories(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        return Response(data=sorted(category.value for category in ProductCategory.objects.all()), status=HTTP_200_OK)
