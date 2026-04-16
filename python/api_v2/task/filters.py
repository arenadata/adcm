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


from cm.models import JobStatus, TaskLog
from django.db.models import Case, F, FloatField, Func, QuerySet, Value, When
from django.db.models.lookups import IsNull
from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework.filters import (
    CharFilter,
    ChoiceFilter,
    NumberFilter,
    OrderingFilter,
)

from api_v2.filters import AdvancedFilterSet


class Epoch(Func):
    template = "EXTRACT(epoch FROM %(expressions)s)::FLOAT"
    output_field = FloatField()


def _add_target_name_field_to_queryset(queryset: QuerySet) -> QuerySet:
    return queryset.annotate(
        target_name=Case(
            When(IsNull(F("selector__action_host_group__name"), False), then=F("selector__action_host_group__name")),
            When(IsNull(F("selector__host__name"), False), then=F("selector__host__name")),
            When(IsNull(F("selector__provider__name"), False), then=F("selector__provider__name")),
            When(IsNull(F("selector__component__name"), False), then=F("selector__component__name")),
            When(IsNull(F("selector__service__name"), False), then=F("selector__service__name")),
            When(IsNull(F("selector__cluster__name"), False), then=F("selector__cluster__name")),
            When(IsNull(F("selector__adcm__name"), False), then=F("selector__adcm__name")),
        )
    )


def _add_duration_time_field_to_queryset(queryset: QuerySet) -> QuerySet:
    # I cannot use the duration field name because it is already used in the model.
    return queryset.annotate(
        duration_time=Case(
            When(IsNull(F("start_date"), True), then=Value(None)),
            When(IsNull(F("finish_date"), True), then=Value(None)),
            default=Epoch(F("finish_date") - F("start_date")),
        )
    )


class TaskOrderingFilter(OrderingFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if "objectName" in value or "-objectName" in value:
            qs = _add_target_name_field_to_queryset(queryset=qs)

        if "duration" in value or "-duration" in value:
            qs = _add_duration_time_field_to_queryset(queryset=qs)

        ordering = [self.get_ordering_value(param) for param in value if param not in EMPTY_VALUES]
        return qs.order_by(*ordering)


class TaskFilter(
    AdvancedFilterSet,
    char_fields=(("name", "action__name"), ("display_name", "action__display_name"), "status"),
    number_fields=("id", ("action", "action__id")),
):
    # Advanced filters
    target_id__eq = NumberFilter(field_name="object_id", lookup_expr="exact", label="target_id__eq")
    target_type__eq = CharFilter(
        field_name="object_type__model", label="target_type__eq", method="advanced_filter_by_target_type"
    )
    owner_id__eq = NumberFilter(field_name="owner_id", lookup_expr="exact", label="owner_id__eq")
    owner_type__eq = CharFilter(field_name="owner_type", lookup_expr="exact", label="owner_type__eq")
    # ---
    # Deprecate filters, saved for backward compatibility.
    job_name = CharFilter(
        label="Case insensitive and partial filter by job name.",
        field_name="action__display_name",
        lookup_expr="icontains",
    )
    # ---
    id = NumberFilter(field_name="id", label="Filter by id.", lookup_expr="exact")
    name = CharFilter(
        label="Case insensitive and partial filter by task name.", field_name="name", lookup_expr="icontains"
    )
    display_name = CharFilter(
        label="Case insensitive and partial filter by task display name.",
        field_name="display_name",
        lookup_expr="icontains",
    )
    object_name = CharFilter(
        label="Case insensitive and partial filter by object name.", method="filter_by_object_name"
    )
    status = ChoiceFilter(field_name="status", choices=JobStatus.choices, label="Filter by status.")
    duration = NumberFilter(label="Filter by duration.", method="filter_by_duration")
    ordering = TaskOrderingFilter(
        fields={
            "id": "id",
            "name": "name",
            "display_name": "displayName",
            "start_date": "startTime",
            "finish_date": "endTime",
            "status": "status",
            "duration_time": "duration",
            "target_name": "objectName",
        },
        field_labels={
            "id": "ID",
            "name": "Name",
            "display_name": "Display name",
            "start_date": "Start time",
            "finish_date": "End time",
            "status": "Status",
            "duration": "Duration",
            "object_name": "Object name",
        },
        label="ordering",
    )

    def advanced_filter_by_target_type(self, queryset: QuerySet, name: str, value: str) -> QuerySet[TaskLog]:
        if value == "action_host_group":
            value = "actionhostgroup"

        return queryset.filter(**{f"{name}__exact": value})

    def filter_by_object_name(self, queryset: QuerySet[TaskLog], _: str, value: str) -> QuerySet[TaskLog]:
        return _add_target_name_field_to_queryset(queryset=queryset).filter(target_name__icontains=value)

    def filter_by_duration(self, queryset: QuerySet[TaskLog], _: str, value: str) -> QuerySet[TaskLog]:
        return _add_duration_time_field_to_queryset(queryset=queryset).filter(duration_time__exact=value)
