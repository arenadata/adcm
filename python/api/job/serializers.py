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

from rest_framework import serializers
from rest_framework.reverse import reverse

from adcm.serializers import EmptySerializer
from api.concern.serializers import ConcernItemSerializer
from api.utils import hlink
from cm.ansible_plugin import get_check_log
from cm.config import RUN_DIR, Job
from cm.errors import AdcmEx
from cm.job import start_task
from cm.models import ClusterObject, Host, JobLog, ServiceComponent, get_object_cluster


def get_object_name(obj):
    if hasattr(obj, 'name'):
        return obj.name
    elif hasattr(obj, 'fqdn'):
        return obj.fqdn
    else:
        return obj.prototype.display_name


def get_job_objects(task):
    if not task.task_object:
        return None

    def cook_obj(_obj_type, obj_id, name):
        return {'type': _obj_type, 'id': obj_id, 'name': name}

    obj = task.task_object
    obj_type = obj.prototype.type
    resp = [cook_obj(obj_type, obj.id, get_object_name(obj))]
    if obj_type == 'service':
        resp.append(cook_obj('cluster', obj.cluster.id, get_object_name(obj.cluster)))
    elif obj_type == 'component':
        resp.append(cook_obj('cluster', obj.cluster.id, get_object_name(obj.cluster)))
        resp.append(cook_obj('service', obj.service.id, get_object_name(obj.service)))
    elif obj_type == 'host':
        if task.action:
            if task.action.host_action:
                cluster = get_object_cluster(obj)
                if cluster:
                    resp.append(cook_obj('cluster', cluster.id, get_object_name(cluster)))
                    if task.action.prototype.type == 'service':
                        service = ClusterObject.obj.get(
                            cluster=cluster, prototype=task.action.prototype
                        )
                        resp.append(cook_obj('service', service.id, get_object_name(service)))
                    elif task.action.prototype.type == 'component':
                        service = ClusterObject.obj.get(
                            cluster=cluster, prototype=task.action.prototype.parent
                        )
                        component = ServiceComponent.obj.get(
                            cluster=cluster, service=service, prototype=task.action.prototype
                        )
                        resp.append(cook_obj('service', service.id, get_object_name(service)))
                        resp.append(cook_obj('component', component.id, get_object_name(component)))
            else:
                resp.append(cook_obj('provider', obj.provider.id, get_object_name(obj.provider)))

    return resp


def get_task_selector(obj, action):
    if not obj:
        return None

    selector = {obj.prototype.type: obj.id}
    if obj.prototype.type == 'service':
        selector['cluster'] = obj.cluster.id

    if obj.prototype.type == 'component':
        selector['cluster'] = obj.cluster.id
        selector['service'] = obj.service.id

    if action and isinstance(obj, Host) and action.host_action:
        cluster = get_object_cluster(obj)
        if cluster:
            selector['cluster'] = cluster.id
            if action.prototype.type == 'component':
                service = ClusterObject.obj.get(cluster=cluster, prototype=action.prototype.parent)
                component = ServiceComponent.obj.get(
                    cluster=cluster, service=service, prototype=action.prototype
                )
                selector['service'] = service.id
                selector['component'] = component.id
            elif action.prototype.type == 'service':
                service = ClusterObject.obj.get(cluster=cluster, prototype=action.prototype)
                selector['service'] = service.id

    return selector


def get_job_display_name(self, obj):
    if obj.sub_action:
        return obj.sub_action.display_name
    elif obj.action:
        return obj.action.display_name
    else:
        return None


def get_action_url(self, obj):
    if not obj.action_id:
        return None

    return reverse(
        'action-details', kwargs={'action_id': obj.action_id}, request=self.context['request']
    )


class DataField(serializers.CharField):
    def to_representation(self, value):
        return value


class JobAction(EmptySerializer):
    name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    prototype_id = serializers.IntegerField(read_only=True)
    prototype_name = serializers.CharField(read_only=True)
    prototype_type = serializers.CharField(read_only=True)
    prototype_version = serializers.CharField(read_only=True)


class JobShort(EmptySerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    display_name = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    finish_date = serializers.DateTimeField(read_only=True)
    url = hlink('job-details', 'id', 'job_id')

    get_display_name = get_job_display_name


class TaskListSerializer(EmptySerializer):
    id = serializers.IntegerField(read_only=True)
    pid = serializers.IntegerField(read_only=True)
    object_id = serializers.IntegerField(read_only=True)
    action_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    finish_date = serializers.DateTimeField(read_only=True)
    url = hlink('task-details', 'id', 'task_id')


class TaskSerializer(TaskListSerializer):
    selector = serializers.SerializerMethodField()
    config = serializers.JSONField(required=False)
    attr = serializers.JSONField(required=False)
    hc = serializers.JSONField(required=False)
    hosts = serializers.JSONField(required=False)
    verbose = serializers.BooleanField(required=False)
    action_url = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    objects = serializers.SerializerMethodField()
    jobs = serializers.SerializerMethodField()
    restart = hlink('task-restart', 'id', 'task_id')
    terminatable = serializers.SerializerMethodField()
    cancel = hlink('task-cancel', 'id', 'task_id')
    object_type = serializers.SerializerMethodField()
    lock = ConcernItemSerializer(read_only=True)

    get_action_url = get_action_url

    @staticmethod
    def get_selector(obj):
        return get_task_selector(obj.task_object, obj.action)

    @staticmethod
    def get_terminatable(obj):
        if obj.action:
            allow_to_terminate = obj.action.allow_to_terminate
        else:
            allow_to_terminate = False

        if allow_to_terminate and obj.status in [Job.CREATED, Job.RUNNING]:
            return True

        return False

    def get_jobs(self, obj):
        return JobShort(obj.joblog_set, many=True, context=self.context).data

    def get_action(self, obj):
        return JobAction(obj.action, context=self.context).data

    @staticmethod
    def get_objects(obj):
        return get_job_objects(obj)

    @staticmethod
    def get_object_type(obj):
        if obj.action:
            return obj.action.prototype.type

        return None


class RunTaskSerializer(TaskSerializer):
    def create(self, validated_data):
        obj = start_task(
            validated_data.get('action'),
            validated_data.get('task_object'),
            validated_data.get('config', {}),
            validated_data.get('attr', {}),
            validated_data.get('hc', []),
            validated_data.get('hosts', []),
            validated_data.get('verbose', False),
        )
        obj.jobs = JobLog.objects.filter(task_id=obj.id)

        return obj


class JobListSerializer(EmptySerializer):
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
    selector = serializers.SerializerMethodField()
    log_dir = serializers.CharField(read_only=True)
    log_files = DataField(read_only=True)
    action_url = serializers.SerializerMethodField()
    task_url = hlink('task-details', 'task_id', 'task_id')

    get_display_name = get_job_display_name
    get_action_url = get_action_url

    @staticmethod
    def get_selector(obj):
        return get_task_selector(obj.task.task_object, obj.action)

    def get_action(self, obj):
        return JobAction(obj.action, context=self.context).data

    @staticmethod
    def get_objects(obj):
        return get_job_objects(obj.task)


class LogStorageSerializer(EmptySerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    format = serializers.CharField(read_only=True)
    content = serializers.SerializerMethodField()

    @staticmethod
    def _get_ansible_content(obj):
        path_file = os.path.join(RUN_DIR, f'{obj.job.id}', f'{obj.name}-{obj.type}.{obj.format}')
        try:
            with open(path_file, 'r', encoding='utf_8') as f:
                content = f.read()
        except FileNotFoundError:
            msg = f'File "{obj.name}-{obj.type}.{obj.format}" not found'

            raise AdcmEx('LOG_NOT_FOUND', msg) from None

        return content

    def get_content(self, obj):
        content = obj.body

        if obj.type in ['stdout', 'stderr']:
            if content is None:
                content = self._get_ansible_content(obj)
        elif obj.type == 'check':
            if content is None:
                content = get_check_log(obj.job_id)
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
            request=self.context['request'],
        )


class LogSerializer(EmptySerializer):
    tag = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    @staticmethod
    def get_tag(obj):
        if obj.type == 'check':
            return obj.type

        return obj.name

    @staticmethod
    def get_level(obj):
        if obj.type == 'check':
            return 'out'

        return obj.type[3:]

    @staticmethod
    def get_type(obj):
        return obj.format

    @staticmethod
    def get_content(obj):
        content = obj.body

        if obj.type in ['stdout', 'stderr']:
            if content is None:
                path_file = os.path.join(
                    RUN_DIR, f'{obj.job.id}', f'{obj.name}-{obj.type}.{obj.format}'
                )
                with open(path_file, 'r', encoding='utf_8') as f:
                    content = f.read()
        elif obj.type == 'check':
            if content is None:
                content = get_check_log(obj.job_id)

            if isinstance(content, str):
                content = json.loads(content)

        return content
