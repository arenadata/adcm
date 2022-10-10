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

import cm.adcm_config
import cm.job
from api.config.serializers import ConfigSerializerUI
from api.utils import get_api_url_kwargs
from cm.models import PrototypeConfig, SubAction


class ActionDetailURL(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        kwargs = get_api_url_kwargs(self.context.get('object'), request)
        kwargs['action_id'] = obj.id
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class HostActionDetailURL(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        objects = self.context.get('objects')
        if obj.host_action and 'host' in objects:
            kwargs = get_api_url_kwargs(objects['host'], request)
        else:
            kwargs = get_api_url_kwargs(objects[obj.prototype.type], request)
        kwargs['action_id'] = obj.id
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
    host_action = serializers.BooleanField(read_only=True)
    start_impossible_reason = serializers.SerializerMethodField()

    def get_start_impossible_reason(self, action):
        if self.context.get("obj"):
            return action.get_start_impossible_reason(self.context["obj"])
        return None


class ActionSerializer(StackActionSerializer):
    url = HostActionDetailURL(read_only=True, view_name='object-action-details')


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
    state_unavailable = serializers.JSONField()
    multi_state_available = serializers.JSONField()
    multi_state_unavailable = serializers.JSONField()
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
    run = HostActionDetailURL(read_only=True, view_name='run-task')


class ActionUISerializer(ActionDetailSerializer):
    def get_config(self, obj):
        action_obj = self.context['obj']
        action_conf = PrototypeConfig.objects.filter(prototype=obj.prototype, action=obj).order_by(
            'id'
        )
        _, _, _, attr = cm.adcm_config.get_prototype_config(obj.prototype, obj)
        cm.adcm_config.get_action_variant(action_obj, action_conf)
        conf = ConfigSerializerUI(action_conf, many=True, context=self.context, read_only=True)
        return {'attr': attr, 'config': conf.data}
