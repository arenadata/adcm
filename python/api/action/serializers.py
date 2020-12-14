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

# pylint: disable=redefined-builtin

from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from rest_framework.reverse import reverse

import cm.job
import cm.adcm_config
import cm.config as config
from cm.errors import AdcmEx, AdcmApiEx
from cm.models import PrototypeConfig, Action, SubAction, JobLog
from cm.models import HostProvider, Host, Cluster, ClusterObject, ServiceComponent
from api.api_views import hlink
from api.config.serializers import ConfigSerializerUI


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


class ActionURL(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {
            'object_type': obj.prototype.type,
            f'{obj.prototype.type}_id': obj.id,
        }
        if obj.prototype.type == 'service':
            if 'cluster' in request.path:
                kwargs['cluster_id'] = obj.cluster.id
        elif obj.prototype.type == 'host':
            if 'cluster' in request.path:
                kwargs['cluster_id'] = obj.cluster.id
        elif obj.prototype.type == 'component':
            kwargs['service_id'] = obj.service.id
            kwargs['cluster_id'] = obj.cluster.id
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class ActionDetailURL(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        action_obj = self.context.get('object')
        kwargs = {
            'object_type': obj.prototype.type,
            f'{obj.prototype.type}_id': action_obj.id,
            'action_id': obj.id
        }
        if obj.prototype.type == 'service':
            if 'cluster' in request.path:
                kwargs['cluster_id'] = action_obj.cluster.id
        elif obj.prototype.type == 'host':
            if 'cluster' in request.path:
                kwargs['cluster_id'] = action_obj.cluster.id
        elif obj.prototype.type == 'component':
            kwargs['service_id'] = action_obj.service.id
            kwargs['cluster_id'] = action_obj.cluster.id
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class StackActionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    prototype_id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()
    display_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    ui_options = serializers.JSONField(required=False)
    button = serializers.CharField(required=False)
    script = serializers.CharField()
    script_type = serializers.CharField()
    state_on_success = serializers.CharField()
    state_on_fail = serializers.CharField()
    hostcomponentmap = serializers.JSONField(required=False)
    allow_to_terminate = serializers.BooleanField(read_only=True)
    partial_execution = serializers.BooleanField(read_only=True)


class ActionSerializer(StackActionSerializer):
    url = ActionDetailURL(read_only=True, view_name='object-action-details')


class ActionShort(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField(required=False)
    button = serializers.CharField(required=False)
    config = serializers.SerializerMethodField()
    hostcomponentmap = serializers.JSONField(read_only=False)
    run = ActionDetailURL(read_only=True, view_name='run-task')

    def get_config(self, obj):
        context = self.context
        context['prototype'] = obj.prototype
        _, _, _, attr = cm.adcm_config.get_prototype_config(obj.prototype, obj)
        cm.adcm_config.get_action_variant(context.get('object'), obj.config)
        conf = ConfigSerializerUI(obj.config, many=True, context=context, read_only=True)
        return {'attr': attr, 'config': conf.data}


class SubActionSerializer(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField(required=False)
    script = serializers.CharField()
    script_type = serializers.CharField()
    state_on_fail = serializers.CharField(required=False)
    params = serializers.JSONField(required=False)


class StackActionDetailSerializer(StackActionSerializer):
    state_available = serializers.JSONField()
    params = serializers.JSONField(required=False)
    log_files = serializers.JSONField(required=False)
    config = serializers.SerializerMethodField()
    subs = serializers.SerializerMethodField()

    def get_config(self, obj):
        aconf = PrototypeConfig.objects.filter(prototype=obj.prototype, action=obj).order_by('id')
        context = self.context
        context['prototype'] = obj.prototype
        conf = ConfigSerializerUI(aconf, many=True, context=context, read_only=True)
        _, _, _, attr = cm.adcm_config.get_prototype_config(obj.prototype, obj)
        return {'attr': attr, 'config': conf.data}

    def get_subs(self, obj):
        sub_actions = SubAction.objects.filter(action=obj).order_by('id')
        subs = SubActionSerializer(sub_actions, many=True, context=self.context, read_only=True)
        return subs.data


class ActionDetailSerializer(StackActionDetailSerializer):
    run = ActionDetailURL(read_only=True, view_name='run-task')


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
