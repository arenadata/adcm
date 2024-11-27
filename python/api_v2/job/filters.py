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
    JobLog,
    JobStatus,
)
from django_filters.rest_framework.filters import (
    ChoiceFilter,
    OrderingFilter,
)
from django_filters.rest_framework.filterset import FilterSet


class JobFilter(FilterSet):
    status = ChoiceFilter(field_name="status", choices=JobStatus.choices, label="Job status")

    ordering = OrderingFilter(
        fields={"id": "id", "finish_date": "endTime", "status": "status", "start_date": "startTime"},
        field_labels={
            "id": "ID",
            "status": "Status",
            "start_date": "Start time",
            "finish_date": "End time",
        },
        label="ordering",
    )

    class Meta:
        model = JobLog
        fields = ["id", "status", "ordering", "start_date", "finish_date"]
