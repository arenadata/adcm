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

import json
import os

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from rest_framework.reverse import reverse

import cm.job
import cm.stack
import cm.status_api
import cm.config as config
from cm.errors import AdcmEx, AdcmApiEx
from cm.models import (
    Action, SubAction, JobLog, HostProvider, Host, Cluster, ClusterObject, ServiceComponent
)

from api.api_views import hlink


def get_job_action(obj):
    try:
        act = Action.objects.get(id=obj.action_id)
        return {
            'name': act.name,
            'display_name': act.display_name,
            'prototype_id': act.prototype.id,
            'prototype_name': act.prototype.name,
            'prototype_version': act.prototype.version,
            'prototype_type': act.prototype.type,
        }
    except Action.DoesNotExist:
        return None


def get_job_objects(obj):
    resp = []
    selector = obj.selector
    for obj_type in selector:
        try:
            if obj_type == 'cluster':
                cluster = Cluster.objects.get(id=selector[obj_type])
                name = cluster.name
            elif obj_type == 'service':
                service = ClusterObject.objects.get(id=selector[obj_type])
                name = service.prototype.display_name
            elif obj_type == 'component':
                comp = ServiceComponent.objects.get(id=selector[obj_type])
                name = comp.prototype.display_name
            elif obj_type == 'provider':
                provider = HostProvider.objects.get(id=selector[obj_type])
                name = provider.name
            elif obj_type == 'host':
                host = Host.objects.get(id=selector[obj_type])
                name = host.fqdn
            else:
                name = ''
        except ObjectDoesNotExist:
            name = 'does not exist'
        resp.append({
            'type': obj_type,
            'id': selector[obj_type],
            'name': name,
        })
    return resp


def get_job_object_type(obj):
    try:
        action = Action.objects.get(id=obj.action_id)
        return action.prototype.type
    except Action.DoesNotExist:
        return None


class DataField(serializers.CharField):
    def to_representation(self, value):
        return value


class JobShort(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    finish_date = serializers.DateTimeField(read_only=True)
    url = hlink('job-details', 'id', 'job_id')


class TaskListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    pid = serializers.IntegerField(read_only=True)
    object_id = serializers.IntegerField(read_only=True)
    action_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    finish_date = serializers.DateTimeField(read_only=True)
    url = hlink('task-details', 'id', 'task_id')


class TaskSerializer(TaskListSerializer):
    selector = serializers.JSONField(read_only=True)
    config = serializers.JSONField(required=False)
    attr = serializers.JSONField(required=False)
    hc = serializers.JSONField(required=False)
    hosts = serializers.JSONField(required=False)
    action_url = serializers.HyperlinkedIdentityField(
        read_only=True,
        view_name='action-details',
        lookup_field='action_id',
        lookup_url_kwarg='action_id'
    )
    action = serializers.SerializerMethodField()
    objects = serializers.SerializerMethodField()
    jobs = serializers.SerializerMethodField()
    restart = hlink('task-restart', 'id', 'task_id')
    terminatable = serializers.SerializerMethodField()
    cancel = hlink('task-cancel', 'id', 'task_id')
    object_type = serializers.SerializerMethodField()

    def get_terminatable(self, obj):
        try:
            action = Action.objects.get(id=obj.action_id)
            allow_to_terminate = action.allow_to_terminate
        except Action.DoesNotExist:
            allow_to_terminate = False
        # pylint: disable=simplifiable-if-statement
        if allow_to_terminate and obj.status in [config.Job.CREATED, config.Job.RUNNING]:
            # pylint: enable=simplifiable-if-statement
            return True
        else:
            return False

    def get_jobs(self, obj):
        task_jobs = JobLog.objects.filter(task_id=obj.id)
        for job in task_jobs:
            if job.sub_action_id:
                try:
                    sub = SubAction.objects.get(id=job.sub_action_id)
                    job.display_name = sub.display_name
                    job.name = sub.name
                except SubAction.DoesNotExist:
                    job.display_name = None
                    job.name = None
            else:
                try:
                    action = Action.objects.get(id=job.action_id)
                    job.display_name = action.display_name
                    job.name = action.name
                except Action.DoesNotExist:
                    job.display_name = None
                    job.name = None
        jobs = JobShort(task_jobs, many=True, context=self.context)
        return jobs.data

    def get_action(self, obj):
        return get_job_action(obj)

    def get_objects(self, obj):
        return get_job_objects(obj)

    def get_object_type(self, obj):
        return get_job_object_type(obj)


class RunTaskSerializer(TaskSerializer):
    def create(self, validated_data):
        try:
            obj = cm.job.start_task(
                validated_data.get('action_id'),
                validated_data.get('selector'),
                validated_data.get('config', {}),
                validated_data.get('attr', {}),
                validated_data.get('hc', []),
                validated_data.get('hosts', [])
            )
            obj.jobs = JobLog.objects.filter(task_id=obj.id)
            return obj
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code, e.adds) from e


class TaskPostSerializer(RunTaskSerializer):
    action_id = serializers.IntegerField()
    selector = serializers.JSONField()

    def validate_selector(self, selector):
        if not isinstance(selector, dict):
            raise AdcmApiEx('JSON_ERROR', 'selector should be a map')
        return selector


class JobListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    pid = serializers.IntegerField(read_only=True)
    task_id = serializers.IntegerField(read_only=True)
    action_id = serializers.IntegerField(read_only=True)
    sub_action_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    finish_date = serializers.DateTimeField(read_only=True)
    url = hlink('job-details', 'id', 'job_id')


class JobSerializer(JobListSerializer):
    action = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    objects = serializers.SerializerMethodField()
    selector = serializers.JSONField(required=False)
    log_dir = serializers.CharField(read_only=True)
    log_files = DataField(read_only=True)
    action_url = hlink('action-details', 'action_id', 'action_id')
    task_url = hlink('task-details', 'id', 'task_id')

    def get_action(self, obj):
        return get_job_action(obj)

    def get_display_name(self, obj):
        if obj.sub_action_id:
            try:
                sub = SubAction.objects.get(id=obj.sub_action_id)
                return sub.display_name
            except SubAction.DoesNotExist:
                return None
        else:
            try:
                action = Action.objects.get(id=obj.action_id)
                return action.display_name
            except Action.DoesNotExist:
                return None

    def get_objects(self, obj):
        return get_job_objects(obj)


class LogStorageSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    format = serializers.CharField(read_only=True)
    content = serializers.SerializerMethodField()

    def get_content(self, obj):
        content = obj.body

        if obj.type in ['stdout', 'stderr']:
            if content is None:
                path_file = os.path.join(
                    config.RUN_DIR, f'{obj.job.id}', f'{obj.name}-{obj.type}.{obj.format}')
                with open(path_file, 'r') as f:
                    content = f.read()
        elif obj.type == 'check':
            if content is None:
                content = cm.job.get_check_log(obj.job_id)
            if isinstance(content, str):
                content = json.loads(content)
        elif obj.type == 'custom':
            if obj.format == 'json' and isinstance(content, str):
                try:
                    custom_content = json.loads(content)
                    custom_content = json.dumps(custom_content, indent=4)
                    content = custom_content
                except json.JSONDecodeError:
                    pass

        return content


class LogStorageListSerializer(LogStorageSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return reverse(
            'log-storage',
            kwargs={'job_id': obj.job_id, 'log_id': obj.id},
            request=self.context['request'])


class LogSerializer(serializers.Serializer):
    tag = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    def get_tag(self, obj):
        if obj.type == 'check':
            return obj.type
        else:
            return obj.name

    def get_level(self, obj):
        if obj.type == 'check':
            return 'out'
        else:
            return obj.type[3:]

    def get_type(self, obj):
        return obj.format

    def get_content(self, obj):
        content = obj.body

        if obj.type in ['stdout', 'stderr']:
            if content is None:
                path_file = os.path.join(
                    config.RUN_DIR, f'{obj.job.id}', f'{obj.name}-{obj.type}.{obj.format}')
                with open(path_file, 'r') as f:
                    content = f.read()
        elif obj.type == 'check':
            if content is None:
                content = cm.job.get_check_log(obj.job_id)
            if isinstance(content, str):
                content = json.loads(content)
        return content
