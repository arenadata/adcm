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

from cm.models import ADCMEntityStatus
from cm.services.status.client import retrieve_status_map
from django.db.models import Q, QuerySet


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
