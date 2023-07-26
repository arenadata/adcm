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

from typing import Sequence

from cm.errors import AdcmEx
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request


class BaseOrderingFilter(OrderingFilter):
    ordering_param = "sortColumn"
    direction_param = "sortDirection"
    allowed_sort_column_names = {"id"}
    column_names_map = {}  # {<request_field>: <model_field>}

    def get_ordering(self, request, queryset, view) -> Sequence[str] | None:
        ordering = super().get_ordering(request=request, queryset=queryset, view=view)

        if ordering is None:
            return ordering

        if set(ordering).difference(self.allowed_sort_column_names):
            allowed_repr = ", ".join(self.allowed_sort_column_names)
            raise AdcmEx(code="INVALID_ORDERING", msg=f"Allowed sortColumn: {allowed_repr}")

        if self.column_names_map:
            ordering = [self.column_names_map.get(column, column) for column in ordering]

        sort_direction = self._get_sort_direction(request=request)
        if sort_direction:
            ordering = [f"{sort_direction}{column}" for column in ordering]

        return ordering

    def _get_sort_direction(self, request: Request) -> str | None:
        sort_direction: str | None = request.query_params.get(self.direction_param)

        if sort_direction is None:
            return sort_direction

        match sort_direction.lower():
            case "desc":
                sort_direction = "-"
            case "asc":
                sort_direction = ""
            case _:
                raise AdcmEx(code="INVALID_ORDERING", msg='Allowed sortDirection: "ASC", "DESC"')

        return sort_direction
