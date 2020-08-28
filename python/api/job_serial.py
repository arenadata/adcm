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

import cm.config as config
import cm.job
import cm.stack
import cm.status_api
from api.serializers import hlink, DataField, get_job_action, get_job_objects
from cm.models import Action, SubAction


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
