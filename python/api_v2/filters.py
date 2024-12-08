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

from itertools import chain
from typing import Collection, Generator

from cm.models import ADCMEntityStatus
from cm.services.status.client import retrieve_status_map
from django.db.models import Q, QuerySet
from django_filters import BaseInFilter, CharFilter, NumberFilter
from django_filters.filterset import BaseFilterSet, FilterSetMetaclass


def filter_service_status(queryset: QuerySet, value: str) -> QuerySet:
    status_map = retrieve_status_map()
    services_up = {
        service_id
        for service_id, service_info in chain.from_iterable(
            cluster_info.services.items() for cluster_info in status_map.clusters.values()
        )
        if service_info.status == 0
    }
    service_up_condition = Q(pk__in=services_up) | Q(prototype__monitoring="passive")

    if value == ADCMEntityStatus.UP:
        return queryset.filter(service_up_condition)

    return queryset.exclude(service_up_condition)


class CharInFilter(BaseInFilter, CharFilter):
    ...


class NumberInFilter(BaseInFilter, NumberFilter):
    ...


def _prepare_filter_fields(fields: tuple[str | tuple[str, ...], ...]) -> Generator[tuple[str, str], None, None]:
    for field in fields:
        if isinstance(field, tuple):
            filter_name, field_name = field
        else:
            filter_name, field_name = field, field

        yield filter_name, field_name


class AdvancedFilterSetMetaclass(FilterSetMetaclass):
    def __new__(cls, *args, **kwargs):
        name, bases, attrs = args
        char_fields: tuple[str | tuple[str, str], ...] = kwargs.get("char_fields", ())
        number_fields: tuple[str | tuple[str, str], ...] = kwargs.get("number_fields", ())

        for filter_name, field_name in _prepare_filter_fields(fields=char_fields):
            attrs[f"{filter_name}__eq"] = CharFilter(field_name=field_name, lookup_expr="exact")
            attrs[f"{filter_name}__ieq"] = CharFilter(field_name=field_name, lookup_expr="iexact")
            attrs[f"{filter_name}__ne"] = CharFilter(field_name=field_name, lookup_expr="ne")
            attrs[f"{filter_name}__ine"] = CharFilter(field_name=field_name, lookup_expr="ine")
            attrs[f"{filter_name}__contains"] = CharFilter(field_name=field_name, lookup_expr="contains")
            attrs[f"{filter_name}__icontains"] = CharFilter(field_name=field_name, lookup_expr="icontains")
            attrs[f"{filter_name}__in"] = CharInFilter(field_name=field_name, lookup_expr="in")
            attrs[f"{filter_name}__iin"] = CharInFilter(field_name=field_name, lookup_expr="lower__in")
            attrs[f"{filter_name}__exclude"] = CharInFilter(field_name=field_name, method="filter_exclude")
            attrs[f"{filter_name}__iexclude"] = CharInFilter(field_name=field_name, method="filter_iexclude")

        for filter_name, field_name in _prepare_filter_fields(fields=number_fields):
            attrs[f"{filter_name}__eq"] = NumberFilter(field_name=field_name, lookup_expr="exact")
            attrs[f"{filter_name}__ne"] = NumberFilter(field_name=field_name, lookup_expr="ne")
            attrs[f"{filter_name}__in"] = NumberInFilter(field_name=field_name, lookup_expr="in")
            attrs[f"{filter_name}__exclude"] = NumberInFilter(field_name=field_name, method="filter_exclude")

        return super().__new__(cls, name=name, bases=bases, attrs=attrs)


class AdvancedFilterSet(BaseFilterSet, metaclass=AdvancedFilterSetMetaclass):
    # Filter fields must be declared during class initialization, so we need to use a metaclass

    def filter_exclude(self, queryset: QuerySet, field_name: str, value: Collection) -> QuerySet:
        return queryset.exclude(**{f"{field_name}__in": value})

    def filter_iexclude(self, queryset: QuerySet, field_name: str, value: Collection) -> QuerySet:
        return queryset.exclude(**{f"{field_name}__lower__in": value})
