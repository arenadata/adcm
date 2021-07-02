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

from django.db.transaction import atomic
from rest_framework import serializers

from cm.adcm_config import ui_config
from cm.models import ConfigLog


class ConfigLogSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='config-log-detail')

    class Meta:
        model = ConfigLog
        fields = ('id', 'date', 'obj_ref', 'description', 'config', 'attr', 'url')

    @atomic
    def create(self, validated_data):
        instance = super().create(validated_data)
        object_config = instance.obj_ref
        object_config.current = instance.id
        object_config.save()
        return instance


class UIConfigLogSerializer(ConfigLogSerializer):
    config = serializers.SerializerMethodField()

    class Meta:
        model = ConfigLog
        fields = ('id', 'date', 'description', 'config', 'attr', 'url')

    def get_config(self, config_log):
        if hasattr(config_log.obj_ref, 'config_group'):
            obj = config_log.obj_ref.config_group.object
        elif hasattr(config_log.obj_ref, 'config_group_diff'):
            obj = config_log.obj_ref.config_group_diff.object
        elif hasattr(config_log.obj_ref, 'adcm'):
            obj = config_log.obj_ref.adcm
        elif hasattr(config_log.obj_ref, 'cluster'):
            obj = config_log.obj_ref.cluster
        elif hasattr(config_log.obj_ref, 'hostprovider'):
            obj = config_log.obj_ref.hostprovider
        elif hasattr(config_log.obj_ref, 'host'):
            obj = config_log.obj_ref.host
        elif hasattr(config_log.obj_ref, 'clusterobject'):
            obj = config_log.obj_ref.clusterobject
        elif hasattr(config_log.obj_ref, 'servicecomponent'):
            obj = config_log.obj_ref.servicecomponent
        return ui_config(obj, config_log)
