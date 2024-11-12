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

from cm.models import Action
from django_filters import NumberFilter
from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    FilterSet,
    OrderingFilter,
)


class ActionFilter(FilterSet):
    name = CharFilter(label="Action Name", field_name="name", lookup_expr="icontains")
    display_name = CharFilter(label="Action Display Name", field_name="display_name", lookup_expr="icontains")
    description = CharFilter(label="Action Description", field_name="description", lookup_expr="icontains")
    is_host_own_action = BooleanFilter(
        label="Is Host Own Action", field_name="host_action", method="filter_is_host_own_action"
    )
    prototype_id = NumberFilter(field_name="prototype", label="Prototype ID")

    ordering = OrderingFilter(
        fields={
            "id": "id",
            "name": "name",
            "display_name": "displayName",
            "is_host_own_action": "isHostOwnAction",
            "description": "description",
        },
        field_labels={
            "id": "ID",
            "name": "Name",
            "display_name": "Display Name",
            "is_host_own_action": "Is Host Own Action",
            "description": "Description",
        },
        label="ordering",
    )

    class Meta:
        model = Action
        fields = ["id", "name", "display_name", "is_host_own_action", "prototype_id"]

    def filter_is_host_own_action(self, queryset, name, value):
        return queryset.filter(**{name: not value})
