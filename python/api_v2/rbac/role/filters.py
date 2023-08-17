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

from django_filters import CharFilter, OrderingFilter
from django_filters.rest_framework import FilterSet
from rbac.models import Role


class RoleFilter(FilterSet):
    display_name = CharFilter(field_name="display_name", label="Role name", lookup_expr="icontains")
    ordering = OrderingFilter(fields={"display_name": "display_name"}, field_labels={"display_name": "Display name"})

    class Meta:
        model = Role
        fields = ("display_name",)
