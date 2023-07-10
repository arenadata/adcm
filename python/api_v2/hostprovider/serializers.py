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

from api_v2.concern.serializers import ConcernSerializer
from cm.adcm_config.config import get_main_info
from cm.models import HostProvider
from cm.upgrade import get_upgrade
from rest_framework.serializers import CharField, ModelSerializer, SerializerMethodField


class HostProviderSerializer(ModelSerializer):
    type = CharField(source="prototype.type")
    state = CharField(read_only=True)
    prototype_display_name = CharField(source="prototype.display_name")
    prototype_name = CharField(source="prototype.name")
    description = CharField(required=False)
    prototype_version = CharField(source="prototype.version")
    is_upgradable = SerializerMethodField()
    main_info = SerializerMethodField()
    concerns = ConcernSerializer(read_only=True, many=True)

    class Meta:
        model = HostProvider
        fields = [
            "id",
            "name",
            "state",
            "multi_state",
            "type",
            "prototype_name",
            "prototype_display_name",
            "prototype_version",
            "description",
            "concerns",
            "is_upgradable",
            "main_info",
        ]

    @staticmethod
    def get_is_upgradable(host_provider: HostProvider) -> bool:
        return bool(get_upgrade(obj=host_provider))

    @staticmethod
    def get_main_info(host_provider: HostProvider) -> str | None:
        return get_main_info(obj=host_provider)


class HostProviderCreateSerializer(ModelSerializer):
    class Meta:
        model = HostProvider
        fields = ["prototype", "name", "description"]


class HostProviderSerializerForHosts(ModelSerializer):
    class Meta:
        model = HostProvider
        fields = ["id", "name", "display_name"]
