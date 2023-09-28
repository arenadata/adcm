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

from cm.models import ADCMEntityStatus, ClusterObject, ObjectType
from cm.status_api import get_service_status
from django.db.models import QuerySet
from django_filters.rest_framework import CharFilter, ChoiceFilter, FilterSet


class ServiceFilter(FilterSet):
    name = CharFilter(label="Service name", method="filter_name")
    status = ChoiceFilter(label="Service status", choices=ADCMEntityStatus.choices, method="filter_status")

    class Meta:
        model = ClusterObject
        fields = ["name", "status"]

    @staticmethod
    def filter_status(queryset: QuerySet, name: str, value: str) -> QuerySet:  # pylint: disable=unused-argument
        if value == ADCMEntityStatus.UP:
            exclude_pks = {service.pk for service in queryset if get_service_status(service=service) != 0}
        else:
            exclude_pks = {service.pk for service in queryset if get_service_status(service=service) == 0}

        return queryset.exclude(pk__in=exclude_pks)

    @staticmethod
    def filter_name(queryset: QuerySet, name: str, value: str) -> QuerySet:  # pylint: disable=unused-argument
        return queryset.filter(prototype__type=ObjectType.SERVICE, prototype__name__icontains=value)
