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

from cm.models import Provider
from django_filters.rest_framework import CharFilter, FilterSet, OrderingFilter


class ProviderFilter(FilterSet):
    name = CharFilter(field_name="name", label="Hostprovider name", lookup_expr="icontains")
    prototype_display_name = CharFilter(
        field_name="prototype__display_name", label="Hostprovider prototype display name"
    )
    state = CharFilter(field_name="state", label="Hostprovider state")
    ordering = OrderingFilter(fields={"name": "name"}, field_labels={"name": "Name"}, label="ordering")

    class Meta:
        model = Provider
        fields = ["name", "state", "prototype_display_name", "ordering"]
