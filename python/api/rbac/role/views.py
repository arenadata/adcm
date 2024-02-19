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

from adcm.permissions import DjangoModelPermissionsAudit
from audit.utils import audit
from cm.models import ProductCategory
from django.db.models import Prefetch, Q
from django_filters import rest_framework as filters
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rbac.models import Role, RoleTypes
from rbac.services.role import role_create, role_update
from rest_flex_fields import is_expanded
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)
from rest_framework.viewsets import ModelViewSet

from api.rbac.role.serializers import RoleSerializer


class _CategoryFilter(filters.CharFilter):
    def filter(self, qs, value):
        if value:
            qs = qs.filter(Q(category__value=value) | Q(any_category=True))
        return qs


class RoleFilter(filters.FilterSet):
    category = _CategoryFilter()

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "display_name",
            "built_in",
            "type",
            "child",
        )


class RoleViewSet(PermissionListMixin, ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ["rbac.view_role"]
    filterset_class = RoleFilter
    ordering_fields = ("id", "name", "display_name", "built_in", "type")
    search_fields = ("name", "display_name")
    schema = AutoSchema()

    def get_queryset(self, *args, **kwargs):  # noqa: ARG002
        queryset = get_objects_for_user(**self.get_get_objects_for_user_kwargs(Role.objects.all()))
        if is_expanded(self.request, "child"):
            return queryset.prefetch_related(
                Prefetch("child", queryset=queryset.exclude(type=RoleTypes.HIDDEN)),
            )
        return queryset

    @audit
    def create(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            role = role_create(**serializer.validated_data)

            return Response(self.get_serializer(role).data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @audit
    def update(self, request, *args, **kwargs):  # noqa: ARG002
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if instance.built_in:
            return Response(status=HTTP_409_CONFLICT)

        serializer = self.get_serializer(data=request.data, partial=partial)

        if serializer.is_valid(raise_exception=True):
            role = role_update(instance, partial, **serializer.validated_data)

            return Response(self.get_serializer(role).data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @audit
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.built_in:
            return Response(status=HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)

    @action(methods=["get"], detail=False)
    def category(self, request):  # noqa: ARG002
        return Response(sorted(b.value for b in ProductCategory.objects.all()))
