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
from cm.errors import raise_adcm_ex
from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from guardian.mixins import PermissionListMixin
from rbac.endpoints.group.serializers import GroupSerializer
from rbac.models import Group
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet

from adcm.permissions import DjangoModelPermissionsAudit


class GroupFilterSet(FilterSet):
    name = CharFilter(field_name="display_name", label="name")

    class Meta:
        model = Group
        fields = ("id", "type")


class GroupOrderingFilter(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if not ordering:
            return queryset

        fix_ordering = []

        for field in ordering:
            if field == "-name":
                fix_ordering.append("-display_name")
                continue

            if field == "name":
                fix_ordering.append("display_name")
                continue

            fix_ordering.append(field)

        return queryset.order_by(*fix_ordering)


class GroupViewSet(PermissionListMixin, ModelViewSet):  # pylint: disable=too-many-ancestors
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (DjangoModelPermissionsAudit,)
    permission_required = ["rbac.view_group"]
    filter_backends = (DjangoFilterBackend, GroupOrderingFilter)
    filterset_class = GroupFilterSet
    ordering_fields = ("id", "name")
    search_fields = ("name", "description", "display_name")

    @audit
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @audit
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @audit
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.built_in:
            raise_adcm_ex("GROUP_DELETE_ERROR")

        return super().destroy(request, args, kwargs)
