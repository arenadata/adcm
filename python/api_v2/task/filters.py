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


from cm.models import ActionHostGroup, Cluster, Component, Host, JobStatus, Provider, Service, TaskLog
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import QuerySet
from django_filters import NumberFilter
from django_filters.rest_framework.filters import (
    CharFilter,
    ChoiceFilter,
    OrderingFilter,
)

from api_v2.filters import AdvancedFilterSet


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

    job_name = CharFilter(label="Job name", field_name="action__display_name", lookup_expr="icontains")
    object_name = CharFilter(label="Object name", method="filter_object_name")
    status = ChoiceFilter(field_name="status", choices=JobStatus.choices, label="Task status")
    ordering = OrderingFilter(
        fields={
            "id": "id",
            "action__name": "name",
            "start_date": "startTime",
            "finish_date": "endTime",
        },
        field_labels={
            "id": "ID",
            "action__name": "Name",
            "start_date": "Start time",
            "finish_date": "End time",
        },
        label="ordering",
    )

    def filter_object_name(self, queryset: QuerySet[TaskLog], _: str, value: str) -> QuerySet:
        model_names = {m._meta.model_name for m in (Cluster, Service, Component, Provider, Host, ActionHostGroup)}
        ct_selector_map = {
            ct_id: model_name if model_name != "actionhostgroup" else "action_host_group"
            for ct_id, model_name in ContentType.objects.filter(app_label="cm", model__in=model_names).values_list(
                "id", "model"
            )
        }

        # ideally, we want to use jsonb_path_exists here
        # params substitution takes place in single-quoted argument of jsonb_path_exists,
        # therefore it must be double-quoted, but django querying functionality can't handle this case
        # Example:
        # WHERE object_type_id = {ct_id} AND
        #       jsonb_path_exists(selector, '$ ? ($.{field}.name like_regex %s flag "i" )')
        where_clause = " OR ".join(
            f"(object_type_id = {ct_id} AND COALESCE(selector ->> '{field}', '{{}}')::jsonb ->> 'name' ILIKE %s)"
            for ct_id, field in ct_selector_map.items()
        )
        with connection.cursor() as cursor:
            cursor.execute(
                sql=f"SELECT id FROM {TaskLog._meta.db_table} WHERE {where_clause}",  # noqa:S608. Not an injection
                params=[f"%{value}%"] * len(ct_selector_map),
            )

            return queryset.filter(id__in=[row[0] for row in cursor.fetchall()])

    def advanced_filter_by_target_type(self, queryset: QuerySet, name: str, value: str) -> QuerySet[TaskLog]:
        if value == "action_host_group":
            value = "actionhostgroup"

        return queryset.filter(**{f"{name}__exact": value})

    class Meta:
        model = TaskLog
        fields = ["id"]
