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
    Cluster,
    Component,
    Host,
    JobStatus,
    Provider,
    Service,
    TaskLog,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django_filters.rest_framework.filters import (
    CharFilter,
    ChoiceFilter,
    OrderingFilter,
)
from django_filters.rest_framework.filterset import FilterSet


class TaskFilter(FilterSet):
    job_name = CharFilter(label="Job name", field_name="action__display_name", lookup_expr="icontains")
    object_name = CharFilter(label="Object name", method="filter_object_name")
    status = ChoiceFilter(field_name="status", choices=JobStatus.choices, label="Task status")
    ordering = OrderingFilter(
        fields={"id": "id", "action__prototype__name": "name", "start_date": "startTime", "finish_date": "endTime"},
        field_labels={
            "id": "ID",
            "action__prototype__name": "Name",
            "start_date": "Start time",
            "finish_date": "End time",
        },
        label="ordering",
    )

    def filter_object_name(self, queryset: QuerySet, _: str, value: str) -> QuerySet:
        clusters = Cluster.objects.filter(name__icontains=value).values_list("id")
        services = Service.objects.filter(prototype__display_name__icontains=value).values_list("id")
        components = Component.objects.filter(prototype__display_name__icontains=value).values_list("id")
        providers = Provider.objects.filter(name__icontains=value).values_list("id")
        hosts = Host.objects.filter(fqdn__icontains=value).values_list("id")

        return (
            queryset.filter(object_type=ContentType.objects.get_for_model(Cluster), object_id__in=clusters)
            | queryset.filter(object_type=ContentType.objects.get_for_model(Service), object_id__in=services)
            | queryset.filter(object_type=ContentType.objects.get_for_model(Component), object_id__in=components)
            | queryset.filter(object_type=ContentType.objects.get_for_model(Provider), object_id__in=providers)
            | queryset.filter(object_type=ContentType.objects.get_for_model(Host), object_id__in=hosts)
        )

    class Meta:
        model = TaskLog
        fields = ["id", "job_name", "object_name", "status", "ordering"]
