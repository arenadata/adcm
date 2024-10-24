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

from cm.models import ActionHostGroup
from django_filters.rest_framework import CharFilter, FilterSet, OrderingFilter


class ActionHostGroupFilter(FilterSet):
    name = CharFilter(field_name="name", label="Name", lookup_expr="icontains")
    has_host = CharFilter(field_name="hosts", label="Group Has Host", lookup_expr="fqdn__icontains", distinct=True)
    description = CharFilter(field_name="description", label="Description", lookup_expr="icontains")

    ordering = OrderingFilter(
        fields={
            "id": "id",
            "name": "name",
            "description": "description",
        },
        field_labels={
            "id": "ID",
            "name": "Name",
            "description": "Description",
        },
        label="ordering",
    )

    class Meta:
        model = ActionHostGroup
        fields = ["name", "has_host", "description"]
