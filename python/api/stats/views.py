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

from api.base_view import GenericUIView
from api.stats.serializers import StatsSerializer
from cm.models import JobLog, JobStatus, TaskLog
from guardian.mixins import PermissionListMixin
from rest_framework import permissions
from rest_framework.response import Response


class JobStats(PermissionListMixin, GenericUIView):
    queryset = JobLog.objects.all()
    serializer_class = StatsSerializer
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = ["cm.view_joblog"]
    ordering = ["id"]

    def get(self, request, pk):  # pylint: disable=unused-argument
        jobs = self.get_queryset().filter(id__gt=pk)

        return Response(
            data={
                JobStatus.FAILED.value: jobs.filter(status=JobStatus.FAILED).count(),
                JobStatus.SUCCESS.value: jobs.filter(status=JobStatus.SUCCESS).count(),
                JobStatus.RUNNING.value: jobs.filter(status=JobStatus.RUNNING).count(),
                JobStatus.ABORTED.value: jobs.filter(status=JobStatus.ABORTED).count(),
                JobStatus.LOCKED.value: jobs.filter(status=JobStatus.LOCKED).count(),
                JobStatus.CREATED.value: jobs.filter(status=JobStatus.CREATED).count(),
            },
        )


class TaskStats(PermissionListMixin, GenericUIView):
    queryset = TaskLog.objects.all()
    serializer_class = StatsSerializer
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = ["cm.view_tasklog"]
    ordering = ["id"]

    def get(self, request, pk):  # pylint: disable=unused-argument
        tasks = self.get_queryset().filter(id__gt=pk)

        return Response(
            data={
                JobStatus.FAILED.value: tasks.filter(status=JobStatus.FAILED).count(),
                JobStatus.SUCCESS.value: tasks.filter(status=JobStatus.SUCCESS).count(),
                JobStatus.RUNNING.value: tasks.filter(status=JobStatus.RUNNING).count(),
                JobStatus.ABORTED.value: tasks.filter(status=JobStatus.ABORTED).count(),
                JobStatus.LOCKED.value: tasks.filter(status=JobStatus.LOCKED).count(),
                JobStatus.CREATED.value: tasks.filter(status=JobStatus.CREATED).count(),
            },
        )
