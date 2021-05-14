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

from rest_framework.response import Response

import cm.config as config
from cm.models import JobLog, TaskLog
from api.serializers import EmptySerializer
from api.api_views import GenericAPIPermView
from . import serializers


class Stats(GenericAPIPermView):
    queryset = JobLog.objects.all()
    serializer_class = serializers.StatsSerializer

    def get(self, request):
        """
        Statistics
        """
        obj = JobLog(id=1)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)


class JobStats(GenericAPIPermView):
    queryset = JobLog.objects.all()
    serializer_class = EmptySerializer

    def get(self, request, job_id):
        """
        Show jobs stats
        """
        jobs = self.get_queryset().filter(id__gt=job_id)
        data = {
            config.Job.FAILED: jobs.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: jobs.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: jobs.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)


class TaskStats(GenericAPIPermView):
    queryset = TaskLog.objects.all()
    serializer_class = EmptySerializer

    def get(self, request, task_id):
        """
        Show tasks stats
        """
        tasks = self.get_queryset().filter(id__gt=task_id)
        data = {
            config.Job.FAILED: tasks.filter(status=config.Job.FAILED).count(),
            config.Job.SUCCESS: tasks.filter(status=config.Job.SUCCESS).count(),
            config.Job.RUNNING: tasks.filter(status=config.Job.RUNNING).count(),
        }
        return Response(data)
