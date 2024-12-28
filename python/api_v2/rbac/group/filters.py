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

from django_filters.rest_framework import (
    CharFilter,
    ChoiceFilter,
    OrderingFilter,
)
from rbac.models import OriginType

from api_v2.filters import AdvancedFilterSet


class GroupFilter(
    AdvancedFilterSet,
    char_fields=("name", "display_name", "type"),
    number_fields=("id",),
):
    display_name = CharFilter(lookup_expr="icontains")
    type = ChoiceFilter(choices=OriginType.choices)
    ordering = OrderingFilter(
        fields={"display_name": "displayName"},
        field_labels={"display_name": "Display name"},
    )
