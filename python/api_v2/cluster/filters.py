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

from cm.models import ADCMEntityStatus, Cluster
from cm.status_api import get_cluster_status
from django.db.models import QuerySet
from django_filters.rest_framework import CharFilter, ChoiceFilter, FilterSet


class ClusterFilter(FilterSet):
    status = ChoiceFilter(label="Cluster status", choices=ADCMEntityStatus.choices, method="filter_status")
    prototype_name = CharFilter(label="Cluster prototype name", method="filter_prototype_name")

    class Meta:
        model = Cluster
        fields = ("name", "status", "prototype_name")

    @staticmethod
    def filter_status(queryset: QuerySet, name: str, value: str) -> QuerySet:  # pylint: disable=unused-argument
        if value == ADCMEntityStatus.UP:
            exclude_pks = {cluster.pk for cluster in queryset if get_cluster_status(cluster=cluster) != 0}
        else:
            exclude_pks = {cluster.pk for cluster in queryset if get_cluster_status(cluster=cluster) == 0}

        return queryset.exclude(pk__in=exclude_pks)

    @staticmethod
    def filter_prototype_name(queryset: QuerySet, name: str, value: str) -> QuerySet:  # pylint: disable=unused-argument
        return queryset.filter(prototype__name=value)