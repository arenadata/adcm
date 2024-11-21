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

from cm.models import (
    LogStorage,
)
from django_filters.rest_framework.filters import (
    CharFilter,
    OrderingFilter,
)
from django_filters.rest_framework.filterset import FilterSet


class LogFilter(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    type = CharFilter(field_name="type", lookup_expr="icontains")
    format = CharFilter(field_name="format", lookup_expr="icontains")

    ordering = OrderingFilter(
        fields={"id": "id", "name": "name", "type": "type", "format": "format"},
        field_labels={
            "id": "ID",
            "name": "Name",
            "type": "Type",
            "format": "Format",
        },
        label="ordering",
    )

    class Meta:
        model = LogStorage
        fields = ["id", "ordering", "name", "type", "format"]
