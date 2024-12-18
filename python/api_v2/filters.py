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

from cm.models import ADCMEntityStatus, Cluster, Component, Host, Service
from cm.services.status.client import retrieve_status_map
from django.db.models import Q, QuerySet
from django_filters import BaseInFilter, CharFilter, NumberFilter
from django_filters.filterset import BaseFilterSet, FilterSetMetaclass


def _filter_status(queryset: QuerySet, value: str, query: Q) -> QuerySet:
    if value == ADCMEntityStatus.UP:
        return queryset.filter(query)

    return queryset.exclude(query)


def filter_cluster_status(queryset: QuerySet, value: Collection[str] | str) -> QuerySet:
    status_map = retrieve_status_map()
    clusters_up = {cluster_id for cluster_id, status_info in status_map.clusters.items() if status_info.status == 0}

    cluster_up_condition = Q(pk__in=clusters_up)

    return _filter_status(queryset=queryset, value=value, query=cluster_up_condition)


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

    return _filter_status(queryset=queryset, value=value, query=service_up_condition)


def filter_component_status(queryset: QuerySet, value: Collection[str] | str) -> QuerySet:
    status_map = retrieve_status_map()

    components_up = set()

    for cluster_info in status_map.clusters.values():
        for service_info in chain.from_iterable(cluster_info.services.values()):
            for component_id, component_info in chain.from_iterable(service_info.components.items()):
                if component_info.status == 0:
                    components_up.add(component_id)

    component_up_condition = Q(pk__in=components_up) | Q(service__prototype__monitoring="passive")

    return _filter_status(queryset=queryset, value=value, query=component_up_condition)


def filter_host_status(queryset: QuerySet, value: Collection[str] | str) -> QuerySet:
    status_map = retrieve_status_map()

    hosts_up = {host_id for host_id, status_info in status_map.hosts.items() if status_info.status == 0}
    host_up_condition = Q(pk__in=hosts_up)

    return _filter_status(queryset=queryset, value=value, query=host_up_condition)


FILTER_MAP = {
    Cluster: filter_cluster_status,
    Service: filter_service_status,
    Component: filter_component_status,
    Host: filter_host_status,
}


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


def _reverse_status(status: str):
    if status.lower() == ADCMEntityStatus.UP:
        return ADCMEntityStatus.DOWN

    return ADCMEntityStatus.UP


def _prepare_case_sensitive_values(value: Collection[str] | str) -> set[str]:
    return {value} if isinstance(value, str) else set(value)


def _prepare_case_insensitive_values(value: Collection[str] | str) -> set[str]:
    return {value.lower()} if isinstance(value, str) else {v.lower() for v in value}


class AdvancedFilterSetMetaclass(FilterSetMetaclass):
    def __new__(cls, *args, **kwargs):
        name, bases, attrs = args
        char_fields: tuple[str | tuple[str, str], ...] = kwargs.get("char_fields", ())
        number_fields: tuple[str | tuple[str, str], ...] = kwargs.get("number_fields", ())

        for filter_name, field_name in _prepare_filter_fields(fields=char_fields):
            if filter_name == "status":
                attrs[f"{filter_name}__eq"] = CharFilter(
                    field_name=field_name,
                    label=f"{filter_name}__eq",
                    method="advanced_case_sensitive_filter_by_status",
                )
                attrs[f"{filter_name}__in"] = CharInFilter(
                    field_name=field_name,
                    label=f"{filter_name}__in",
                    method="advanced_case_sensitive_filter_by_status",
                )
                attrs[f"{filter_name}__ieq"] = CharFilter(
                    field_name=field_name,
                    label=f"{filter_name}__ieq",
                    method="advanced_case_insensitive_filter_by_status",
                )
                attrs[f"{filter_name}__iin"] = CharInFilter(
                    field_name=field_name,
                    label=f"{filter_name}__iin",
                    method="advanced_case_insensitive_filter_by_status",
                )
                attrs[f"{filter_name}__ne"] = CharFilter(
                    field_name=field_name,
                    label=f"{filter_name}__ne",
                    method="advanced_case_sensitive_reverse_filter_by_status",
                )
                attrs[f"{filter_name}__exclude"] = CharInFilter(
                    field_name=field_name,
                    label=f"{filter_name}__exclude",
                    method="advanced_case_sensitive_reverse_filter_by_status",
                )
                attrs[f"{filter_name}__ine"] = CharFilter(
                    field_name=field_name,
                    label=f"{filter_name}__ine",
                    method="advanced_case_insensitive_reverse_filter_by_status",
                )
                attrs[f"{filter_name}__iexclude"] = CharInFilter(
                    field_name=field_name,
                    label=f"{filter_name}__iexclude",
                    method="advanced_case_insensitive_reverse_filter_by_status",
                )

                continue

            attrs[f"{filter_name}__eq"] = CharFilter(
                field_name=field_name, lookup_expr="exact", label=f"{filter_name}__eq"
            )
            attrs[f"{filter_name}__ieq"] = CharFilter(
                field_name=field_name, lookup_expr="iexact", label=f"{filter_name}__ieq"
            )
            attrs[f"{filter_name}__ne"] = CharFilter(
                field_name=field_name, lookup_expr="ne", label=f"{filter_name}__ne"
            )
            attrs[f"{filter_name}__ine"] = CharFilter(
                field_name=field_name, lookup_expr="ine", label=f"{filter_name}__ine"
            )
            attrs[f"{filter_name}__contains"] = CharFilter(
                field_name=field_name, lookup_expr="contains", label=f"{filter_name}__contains"
            )
            attrs[f"{filter_name}__icontains"] = CharFilter(
                field_name=field_name, lookup_expr="icontains", label=f"{filter_name}__icontains"
            )
            attrs[f"{filter_name}__in"] = CharInFilter(
                field_name=field_name, lookup_expr="in", label=f"{filter_name}__in"
            )
            attrs[f"{filter_name}__iin"] = CharInFilter(
                field_name=field_name, lookup_expr="lower__in", label=f"{filter_name}__iin"
            )
            attrs[f"{filter_name}__exclude"] = CharInFilter(
                field_name=field_name,
                lookup_expr="in",
                label=f"{filter_name}__exclude",
                exclude=True,
            )
            attrs[f"{filter_name}__iexclude"] = CharInFilter(
                field_name=field_name,
                lookup_expr="lower__in",
                label=f"{filter_name}__iexclude",
                exclude=True,
            )

        for filter_name, field_name in _prepare_filter_fields(fields=number_fields):
            attrs[f"{filter_name}__eq"] = NumberFilter(
                field_name=field_name, lookup_expr="exact", label=f"{filter_name}__eq"
            )
            attrs[f"{filter_name}__ne"] = NumberFilter(
                field_name=field_name, lookup_expr="ne", label=f"{filter_name}__ne"
            )
            attrs[f"{filter_name}__in"] = NumberInFilter(
                field_name=field_name, lookup_expr="in", label=f"{filter_name}__in"
            )
            attrs[f"{filter_name}__exclude"] = NumberInFilter(
                field_name=field_name,
                lookup_expr="in",
                label=f"{filter_name}__exclude",
                exclude=True,
            )

        return super().__new__(cls, name=name, bases=bases, attrs=attrs)


class AdvancedFilterSet(BaseFilterSet, metaclass=AdvancedFilterSetMetaclass):
    # Filter fields must be declared during class initialization, so we need to use a metaclass

    def advanced_case_sensitive_filter_by_status(
        self, queryset: QuerySet, __: str, value: Collection[str] | str
    ) -> QuerySet:
        values = _prepare_case_sensitive_values(value)
        valid_values = {ADCMEntityStatus.UP, ADCMEntityStatus.DOWN}.intersection(values)

        match len(valid_values):
            case 1:
                func = FILTER_MAP[queryset.model]
                return func(queryset=queryset, value=valid_values.pop())
            case 0:
                return queryset.none()
            case 2:
                return queryset

    def advanced_case_insensitive_filter_by_status(
        self, queryset: QuerySet, __: str, value: Collection[str] | str
    ) -> QuerySet:
        values = _prepare_case_insensitive_values(value)
        valid_values = {ADCMEntityStatus.UP, ADCMEntityStatus.DOWN}.intersection(values)

        match len(valid_values):
            case 1:
                func = FILTER_MAP[queryset.model]
                return func(queryset=queryset, value=valid_values.pop())
            case 0:
                return queryset.none()
            case 2:
                return queryset

    def advanced_case_sensitive_reverse_filter_by_status(
        self, queryset: QuerySet, __: str, value: Collection[str] | str
    ) -> QuerySet:
        values = _prepare_case_sensitive_values(value)
        valid_values = {ADCMEntityStatus.UP, ADCMEntityStatus.DOWN}.intersection(values)

        match len(valid_values):
            case 1:
                func = FILTER_MAP[queryset.model]
                return func(queryset=queryset, value=_reverse_status(valid_values.pop()))
            case 0:
                return queryset
            case 2:
                return queryset.none()

    def advanced_case_insensitive_reverse_filter_by_status(
        self, queryset: QuerySet, __: str, value: Collection[str] | str
    ) -> QuerySet:
        values = _prepare_case_insensitive_values(value)
        valid_values = {ADCMEntityStatus.UP, ADCMEntityStatus.DOWN}.intersection(values)

        match len(valid_values):
            case 1:
                func = FILTER_MAP[queryset.model]
                return func(queryset=queryset, value=_reverse_status(valid_values.pop()))
            case 0:
                return queryset
            case 2:
                return queryset.none()
