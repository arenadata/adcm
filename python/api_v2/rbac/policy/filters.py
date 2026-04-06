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

from cm.models import Cluster, Host, Provider, Service
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet
from django_filters.rest_framework import CharFilter, NumberFilter, OrderingFilter

from api_v2.filters import AdvancedFilterSet


class PolicyFilter(
    AdvancedFilterSet,
    char_fields=("name",),
    number_fields=("id",),
):
    id = NumberFilter(field_name="id", label="Filter by id.")
    name = CharFilter(
        label="Case insensitive and partial filter by policy name.", field_name="name", lookup_expr="icontains"
    )
    group_name = CharFilter(
        label="Filter by group name.",
        field_name="group__name",
        lookup_expr="exact",
    )
    group_display_name = CharFilter(
        label="Filter by group display name.",
        field_name="group__display_name",
        lookup_expr="exact",
    )
    role_name = CharFilter(
        label="Filter by role name.",
        field_name="role__name",
        lookup_expr="exact",
    )
    role_display_name = CharFilter(
        label="Filter by role display name.",
        field_name="role__display_name",
        lookup_expr="exact",
    )
    object_name = CharFilter(label="Filter by object name.", method="filter_by_object_name")
    object_display_name = CharFilter(label="Filter by object display name.", method="filter_by_object_display_name")
    ordering = OrderingFilter(
        fields={
            "name": "name",
            "role__name": "roleName",
            "role__display_name": "roleDisplayName",
        },
        field_labels={
            "name": "Name",
            "role__name": "Role Name",
            "role__display_name": "Role Display Name",
        },
        label="ordering",
    )

    def filter_by_object_name(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        # `Cluster`, `Provider` and `Host` don't have any real `display_name` fields.
        #  Therefore, the name fields are duplicated for these objects.
        model_name_map = {
            Cluster: "name",
            Provider: "name",
            Host: "fqdn",
            Service: "prototype__name",
        }

        return self._filter_by_object(queryset=queryset, value=value, model_map=model_name_map)

    def filter_by_object_display_name(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        model_display_name_map = {
            Cluster: "name",
            Provider: "name",
            Host: "fqdn",
            Service: "prototype__display_name",
        }

        return self._filter_by_object(queryset=queryset, value=value, model_map=model_display_name_map)

    def _filter_by_object(
        self, queryset: QuerySet, value: str, model_map: dict[type[Cluster | Provider | Host | Service], str]
    ) -> QuerySet:
        query = Q()
        for model, field in model_map.items():
            content_type = ContentType.objects.get_for_model(model)
            model_query = Q()
            name_filter_field = f"{field}__icontains"
            model_query |= Q(**{name_filter_field: value})
            object_ids = model.objects.filter(model_query).values_list("id", flat=True)
            query |= Q(object__content_type=content_type, object__object_id__in=object_ids)
        return queryset.filter(query).distinct()
