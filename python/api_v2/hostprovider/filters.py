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

from cm.models import HostProvider
from django_filters.rest_framework import CharFilter, FilterSet, OrderingFilter


class HostProviderFilter(FilterSet):
    name = CharFilter(field_name="name", label="Hostprovider name", lookup_expr="icontains")
    prototype_display_name = CharFilter(
        field_name="prototype__display_name", label="Hostprovider prototype display name", lookup_expr="icontains"
    )
    state = CharFilter(field_name="state", label="Hostprovider state", lookup_expr="icontains")
    description = CharFilter(field_name="description", label="Hostprovider description", lookup_expr="icontains")
    ordering = OrderingFilter(
        fields={
            "id": "id",
            "name": "name",
            "prototype__display_name": "prototypeDisplayName",
            "state": "state",
            "description": "description",
        },
        field_labels={
            "id": "ID",
            "name": "Name",
            "prototype__display_name": "Prototype display name",
            "state": "State",
            "description": "Description",
        },
        label="ordering",
    )

    class Meta:
        model = HostProvider
        fields = ["id", "name", "state", "prototype_display_name", "description"]
