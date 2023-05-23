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

from typing import Dict

from audit.models import AuditLog, AuditSession
from django.db.models import QuerySet


def filter_objects_within_time_range(queryset: QuerySet, query_params: Dict) -> QuerySet:
    time_from = query_params.get("time_from", None)
    time_to = query_params.get("time_to", None)
    time_range_parameters = {
        AuditLog.__name__: AuditLog.operation_time.field.attname,
        AuditSession.__name__: AuditSession.login_time.field.attname,
    }
    lookup = f"{time_range_parameters[queryset.model.__name__]}"
    if time_from:
        queryset = queryset.filter(**{f"{lookup}__gte": time_from})
    if time_to:
        queryset = queryset.filter(**{f"{lookup}__lte": time_to})
    return queryset
