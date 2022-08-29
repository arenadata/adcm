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

from rest_framework import serializers

from api.concern.serializers import ConcernItemSerializer
from api.serializers import StringListSerializer
from api.utils import CommonAPIURL, hlink
from cm.adcm_config import get_main_info


class AdcmSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    prototype_id = serializers.IntegerField()
    state = serializers.CharField(read_only=True)
    url = hlink('adcm-details', 'id', 'adcm_id')


class AdcmDetailSerializer(AdcmSerializer):
    prototype_version = serializers.SerializerMethodField()
    bundle_id = serializers.IntegerField(read_only=True)
    config = CommonAPIURL(view_name='object-config')
    action = CommonAPIURL(view_name='object-action')
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = serializers.BooleanField(read_only=True)

    def get_prototype_version(self, obj):
        return obj.prototype.version


class AdcmDetailUISerializer(AdcmDetailSerializer):
    main_info = serializers.SerializerMethodField()

    def get_main_info(self, obj):
        return get_main_info(obj)
