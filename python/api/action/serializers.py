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

from rest_framework import serializers
from rest_framework.reverse import reverse

import cm.job
import cm.adcm_config
from cm.errors import AdcmEx, AdcmApiEx
from cm.models import PrototypeConfig, Action, SubAction, JobLog
from api.serializers import ConfigSerializerUI, TaskSerializer


class ActionURL(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        action_obj = self.context.get('object')
        kwargs = {
            'object_type': obj.prototype.type,
            f'{obj.prototype.type}_id': action_obj.id,
        }
        if isinstance(obj, Action):
            kwargs['action_id'] = obj.id
        if obj.prototype.type == 'component':
            kwargs['service_id'] = action_obj.service.id
            kwargs['cluster_id'] = action_obj.cluster.id
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class ActionSerializer(serializers.Serializer):
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
    url = ActionURL(read_only=True, view_name='object-action-details')


class SubActionSerializer(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField(required=False)
    script = serializers.CharField()
    script_type = serializers.CharField()
    state_on_fail = serializers.CharField(required=False)
    params = serializers.JSONField(required=False)


class ActionDetailSerializer(ActionSerializer):
    state_available = serializers.JSONField()
    params = serializers.JSONField(required=False)
    log_files = serializers.JSONField(required=False)
    config = serializers.SerializerMethodField()
    subs = serializers.SerializerMethodField()
    run = ActionURL(read_only=True, view_name='run-task')

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
