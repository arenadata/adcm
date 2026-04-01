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
from django_filters.rest_framework import CharFilter, OrderingFilter
from rbac.models import Policy

from api_v2.filters import AdvancedFilterSet


class PolicyFilter(
    AdvancedFilterSet,
    char_fields=("name",),
    number_fields=("id",),
):
    name = CharFilter(label="Name", field_name="name", lookup_expr="icontains")
    group_name = CharFilter(
        label="Case insensitive and partial filter by group display name.",
        field_name="group__display_name",
        lookup_expr="icontains",
    )
    role_name = CharFilter(
        label="Case insensitive and partial filter by role display name.",
        field_name="role__display_name",
        lookup_expr="icontains",
    )
    object_name = CharFilter(label="Case insensitive and partial filter by object name.", method="filter_object_name")
    ordering = OrderingFilter(
        fields={
            "name": "name",
            "role__name": "roleName",
        },
        field_labels={"name": "Name", "role__name": "Role"},
        label="ordering",
    )

    class Meta:
        model = Policy
        fields = ["id"]

    def filter_object_name(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002, ARG004
        model_name_map = {
            Cluster: "name",
            Provider: "name",
            Host: "fqdn",
            Service: "prototype__display_name",
        }

        query = Q()
        for model, field in model_name_map.items():
            content_type = ContentType.objects.get_for_model(model)
            model_query = Q()
            name_filter_field = f"{field}__icontains"
            model_query |= Q(**{name_filter_field: value})
            object_ids = model.objects.filter(model_query).values_list("id", flat=True)
            query |= Q(object__content_type=content_type, object__object_id__in=object_ids)
        return queryset.filter(query).distinct()
