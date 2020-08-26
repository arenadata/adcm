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

import os
import re

from django.http import HttpResponse
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

import cm.config as config
from api.api_views import DetailViewRO, create, PageView
from api.job_serial import (
    JobSerializer, JobListSerializer, LogStorageSerializer, LogStorageListSerializer, LogSerializer
)
from api.serializers import TaskSerializer, TaskListSerializer, TaskPostSerializer
from api.serializers import check_obj
from cm.errors import AdcmEx, AdcmApiEx
from cm.job import get_log, restart_task, cancel_task
from cm.models import JobLog, TaskLog, LogStorage


class JobList(PageView):
    """
    get:
    List all jobs
    """
    queryset = JobLog.objects.order_by('-id')
    serializer_class = JobListSerializer
    serializer_class_ui = JobSerializer
    filterset_fields = ('action_id', 'task_id', 'pid', 'status', 'start_date', 'finish_date')
    ordering_fields = ('status', 'start_date', 'finish_date')


class JobDetail(GenericAPIView):
    queryset = JobLog.objects.all()
    serializer_class = JobSerializer

    def get(self, request, job_id):
        """
        Show job
        """
        job = check_obj(JobLog, job_id, 'JOB_NOT_FOUND')
        job.log_dir = os.path.join(config.RUN_DIR, f'{job_id}')
        logs = get_log(job)
        for lg in logs:
            log_id = lg['id']
            lg['url'] = reverse(
                'log-storage',
                kwargs={
                    'job_id': job.id,
                    'log_id': log_id
                },
                request=request)
            lg['download_url'] = reverse(
                'download-log',
                kwargs={
                    'job_id': job.id,
                    'log_id': log_id
                },
                request=request
            )

        job.log_files = logs
        serializer = self.serializer_class(job, data=request.data, context={'request': request})
        serializer.is_valid()
        return Response(serializer.data)


class LogStorageListView(PageView):
    queryset = LogStorage.objects.all()
    serializer_class = LogStorageListSerializer
    filterset_fields = ('name', 'type', 'format')
    ordering_fields = ('id', 'name')

    def get(self, request, job_id):  # pylint: disable=arguments-differ
        obj = self.filter_queryset(LogStorage.objects.filter(job_id=job_id))
        return self.get_page(obj, request)


class LogStorageView(GenericAPIView):
    queryset = LogStorage.objects.all()
    serializer_class = LogStorageSerializer

    def get(self, request, job_id, log_id):
        try:
            job = JobLog.objects.get(id=job_id)
            try:
                log_storage = LogStorage.objects.get(id=log_id, job=job)
            except LogStorage.DoesNotExist:
                raise AdcmApiEx(
                    'LOG_NOT_FOUND', f'log {log_id} not found for job {job_id}') from None
            serializer = self.serializer_class(log_storage, context={'request': request})
            return Response(serializer.data)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


def download_log_file(request, job_id, log_id):
    try:
        job = JobLog.objects.get(id=job_id)
        log_storage = LogStorage.objects.get(id=log_id, job=job)

        if log_storage.type in ['stdout', 'stderr']:
            filename = f'{job.id}-{log_storage.name}-{log_storage.type}.{log_storage.format}'
        else:
            filename = f'{job.id}-{log_storage.name}.{log_storage.format}'
        filename = re.sub(r'\s+', '_', filename)
        if log_storage.format == 'txt':
            mime_type = 'text/plain'
        else:
            mime_type = 'application/json'

        if log_storage.body is None:
            body = ''
            length = 0
        else:
            body = log_storage.body
            length = len(body)

        response = HttpResponse(body)
        response['Content-Type'] = mime_type
        response['Content-Length'] = length
        response['Content-Encoding'] = 'UTF-8'
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
    except AdcmEx as e:
        raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class LogFile(GenericAPIView):
    queryset = LogStorage.objects.all()
    serializer_class = LogSerializer

    def get(self, request, job_id, tag, level, log_type):
        """
        Show log file
        """
        if tag == 'ansible':
            _type = f'std{level}'
        else:
            _type = 'check'
            tag = 'ansible'

        ls = LogStorage.objects.get(job_id=job_id, name=tag, type=_type, format=log_type)
        try:
            serializer = self.serializer_class(ls, context={'request': request})
            return Response(serializer.data)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class Task(PageView):
    """
    get:
    List all tasks
    """
    queryset = TaskLog.objects.order_by('-id')
    serializer_class = TaskListSerializer
    serializer_class_ui = TaskSerializer
    post_serializer = TaskPostSerializer
    filterset_fields = ('action_id', 'pid', 'status', 'start_date', 'finish_date')
    ordering_fields = ('status', 'start_date', 'finish_date')

    def post(self, request):
        """
        Create and run new task
        Return handler to new task
        """
        serializer = self.post_serializer(data=request.data, context={'request': request})
        return create(serializer)


class TaskDetail(DetailViewRO):
    """
    get:
    Show task
    """
    queryset = TaskLog.objects.all()
    serializer_class = TaskSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'task_id'
    error_code = 'TASK_NOT_FOUND'

    def get_object(self):
        task = super().get_object()
        task.jobs = JobLog.objects.filter(task_id=task.id)
        return task


class TaskReStart(GenericAPIView):
    queryset = TaskLog.objects.all()
    serializer_class = TaskSerializer

    def put(self, request, task_id):
        task = check_obj(TaskLog, task_id, 'TASK_NOT_FOUND')
        try:
            restart_task(task)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e
        return Response(status=status.HTTP_200_OK)


class TaskCancel(GenericAPIView):
    queryset = TaskLog.objects.all()
    serializer_class = TaskSerializer

    def put(self, request, task_id):
        task = check_obj(TaskLog, task_id, 'TASK_NOT_FOUND')
        try:
            cancel_task(task)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e
        return Response(status=status.HTTP_200_OK)
