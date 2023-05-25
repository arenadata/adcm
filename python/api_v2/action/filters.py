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
from django.db.models import QuerySet
from django_filters.rest_framework import CharFilter, FilterSet


class ActionFilter(FilterSet):
    name = CharFilter(label="Action name", method="filter_name")

    class Meta:
        model = Action
        fields = ["name"]

    @staticmethod
    def filter_name(queryset: QuerySet, name: str, value: str) -> QuerySet:  # pylint: disable=unused-argument
        return queryset.filter(name=value)
