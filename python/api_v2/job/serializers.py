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

from api_v2.task.serializers import JobListSerializer, TaskRetrieveByJobSerializer
from cm.models import JobLog
from rest_framework.fields import DateTimeField, DurationField


class JobRetrieveSerializer(JobListSerializer):
    parent_task = TaskRetrieveByJobSerializer(source="task", allow_null=True)
    start_time = DateTimeField(source="start_date")
    end_time = DateTimeField(source="finish_date")
    duration = DurationField()

    class Meta:
        model = JobLog
        fields = (
            "id",
            "name",
            "display_name",
            "parent_task",
            "status",
            "start_time",
            "end_time",
            "duration",
            "task_id",
            "is_terminatable",
        )
