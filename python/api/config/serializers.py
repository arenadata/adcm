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

from api.utils import CommonAPIURL, get_api_url_kwargs
from cm.adcm_config import (
    get_default,
    group_is_activatable,
    restore_cluster_config,
    ui_config,
)
from cm.api import update_obj_config
from rest_framework import serializers
from rest_framework.reverse import reverse


class ConfigVersionURL(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, _format):
        kwargs = get_api_url_kwargs(self.context.get('object'), request)
        kwargs['version'] = obj.id
        return reverse(view_name, kwargs=kwargs, request=request, format=_format)


class HistoryCurrentPreviousConfigSerializer(serializers.Serializer):
    history = CommonAPIURL(read_only=True, view_name='config-history')
    current = CommonAPIURL(read_only=True, view_name='config-current')
    previous = CommonAPIURL(read_only=True, view_name='config-previous')

    def update(self, instance, validated_data):
        pass  # Class must implement all abstract methods

    def create(self, validated_data):
        pass  # Class must implement all abstract methods


class ObjectConfigSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    date = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(required=False, allow_blank=True)
    config = serializers.JSONField()
    attr = serializers.JSONField(required=False)

    def update(self, instance, validated_data):
        pass  # Class must implement all abstract methods

    def create(self, validated_data):
        pass  # Class must implement all abstract methods


class ObjectConfigUpdateSerializer(ObjectConfigSerializer):
    def update(self, instance, validated_data):
        conf = validated_data.get('config')
        attr = validated_data.get('attr', {})
        desc = validated_data.get('description', '')
        cl = update_obj_config(instance.obj_ref, conf, attr, desc)
        if validated_data.get('ui'):
            cl.config = ui_config(validated_data.get('obj'), cl)
        return cl


class ObjectConfigRestoreSerializer(ObjectConfigSerializer):
    config = serializers.JSONField(read_only=True)

    def update(self, instance, validated_data):
        return restore_cluster_config(
            instance.obj_ref, instance.id, validated_data.get('description', instance.description)
        )


class ConfigHistorySerializer(ObjectConfigSerializer):
    url = ConfigVersionURL(read_only=True, view_name='config-history-version')


class ConfigSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    display_name = serializers.CharField(required=False)
    subname = serializers.CharField()
    default = serializers.SerializerMethodField(method_name="get_default_field")
    value = serializers.SerializerMethodField()
    type = serializers.CharField()
    limits = serializers.JSONField(required=False)
    ui_options = serializers.JSONField(required=False)
    required = serializers.BooleanField()

    def update(self, instance, validated_data):
        pass  # Class must implement all abstract methods

    def create(self, validated_data):
        pass  # Class must implement all abstract methods

    @staticmethod
    def get_default_field(obj):
        return get_default(obj)

    def get_value(self, obj):  # pylint: disable=arguments-renamed
        proto = self.context.get('prototype', None)
        return get_default(obj, proto)


class ConfigSerializerUI(ConfigSerializer):
    activatable = serializers.SerializerMethodField()

    @staticmethod
    def get_activatable(obj):
        return bool(group_is_activatable(obj))
