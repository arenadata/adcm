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

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from guardian.mixins import PermissionListMixin
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.reverse import reverse

from api.base_view import GenericUIView, DetailView, PaginatedView
from api.utils import get_object_for_user, check_custom_perm, SuperuserPermissionListMixin
from cm import config
from cm.errors import AdcmEx
from cm.job import get_log, restart_task, cancel_task
from cm.models import JobLog, TaskLog, LogStorage
from rbac.viewsets import DjangoOnlyObjectPermissions
from . import serializers


class JobList(PermissionListMixin, PaginatedView):
    """
    get:
    List all jobs
    """

    queryset = JobLog.objects.order_by('-id')
    serializer_class = serializers.JobListSerializer
    serializer_class_ui = serializers.JobSerializer
    filterset_fields = ('action_id', 'task_id', 'pid', 'status', 'start_date', 'finish_date')
    ordering_fields = ('status', 'start_date', 'finish_date')
    permission_classes = (permissions.DjangoModelPermissions,)
    permission_required = ['cm.view_joblog']


class JobDetail(PermissionListMixin, GenericUIView):
    queryset = JobLog.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = ['cm.view_joblog']
    serializer_class = serializers.JobSerializer

    def get(self, request, *args, **kwargs):
        """
        Show job
        """
        job = get_object_for_user(request.user, 'cm.view_joblog', JobLog, id=kwargs['job_id'])
        job.log_dir = os.path.join(config.RUN_DIR, f'{job.id}')
        logs = get_log(job)
        for lg in logs:
            log_id = lg['id']
            lg['url'] = reverse(
                'log-storage', kwargs={'job_id': job.id, 'log_id': log_id}, request=request
            )
            lg['download_url'] = reverse(
                'download-log', kwargs={'job_id': job.id, 'log_id': log_id}, request=request
            )

        job.log_files = logs
        serializer = self.get_serializer(job, data=request.data)
        serializer.is_valid()
        return Response(serializer.data)


class LogStorageListView(PermissionListMixin, PaginatedView):
    queryset = LogStorage.objects.all()
    permission_required = ['cm.view_logstorage']
    serializer_class = serializers.LogStorageListSerializer
    filterset_fields = ('name', 'type', 'format')
    ordering_fields = ('id', 'name')

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if 'job_id' not in self.kwargs:
            return queryset
        return queryset.filter(job_id=self.kwargs['job_id'])


class LogStorageView(PermissionListMixin, GenericUIView):
    queryset = LogStorage.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = ['cm.view_logstorage']
    serializer_class = serializers.LogStorageSerializer

    def get(self, request, *args, **kwargs):
        job = get_object_for_user(request.user, 'cm.view_joblog', JobLog, id=kwargs['job_id'])
        try:
            log_storage = self.get_queryset().get(id=kwargs['log_id'], job=job)
        except LogStorage.DoesNotExist:
            raise AdcmEx(
                'LOG_NOT_FOUND', f'log {kwargs["log_id"]} not found for job {kwargs["job_id"]}'
            ) from None
        serializer = self.get_serializer(log_storage)
        return Response(serializer.data)


def download_log_file(request, job_id, log_id):
    job = JobLog.obj.get(id=job_id)
    log_storage = LogStorage.obj.get(id=log_id, job=job)

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


class LogFile(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = LogStorage.objects.all()
    serializer_class = serializers.LogSerializer

    def get(self, request, job_id, tag, level, log_type):
        """
        Show log file
        """
        if tag == 'ansible':
            _type = f'std{level}'
        else:
            _type = 'check'
            tag = 'ansible'

        ls = LogStorage.obj.get(job_id=job_id, name=tag, type=_type, format=log_type)
        serializer = self.get_serializer(ls)
        return Response(serializer.data)


class Task(SuperuserPermissionListMixin, PaginatedView):
    """
    get:
    List all tasks
    """

    queryset = TaskLog.objects.order_by('-id')
    superuser_queryset = TaskLog.objects.filter(
        object_type=ContentType.objects.get(app_label='cm', model='adcm')
    )
    permission_required = ['cm.view_tasklog']
    serializer_class = serializers.TaskListSerializer
    serializer_class_ui = serializers.TaskSerializer
    filterset_fields = ('action_id', 'pid', 'status', 'start_date', 'finish_date')
    ordering_fields = ('status', 'start_date', 'finish_date')


class TaskDetail(PermissionListMixin, DetailView):
    """
    get:
    Show task
    """

    queryset = TaskLog.objects.all()
    permission_required = ['cm.view_tasklog']
    serializer_class = serializers.TaskSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'task_id'
    error_code = 'TASK_NOT_FOUND'


class TaskReStart(GenericUIView):
    queryset = TaskLog.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.TaskSerializer

    def put(self, request, *args, **kwargs):
        task = get_object_for_user(request.user, 'cm.view_tasklog', TaskLog, id=kwargs['task_id'])
        check_custom_perm(request.user, 'change', TaskLog, task)
        restart_task(task)
        return Response(status=status.HTTP_200_OK)


class TaskCancel(GenericUIView):
    queryset = TaskLog.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.TaskSerializer

    def put(self, request, *args, **kwargs):
        task = get_object_for_user(request.user, 'cm.view_tasklog', TaskLog, id=kwargs['task_id'])
        check_custom_perm(request.user, 'change', TaskLog, task)
        cancel_task(task)
        return Response(status=status.HTTP_200_OK)
