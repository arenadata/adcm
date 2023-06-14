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
from cm.models import Host, HostComponent, HostProvider, MaintenanceMode
from cm.status_api import get_host_status
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    SerializerMethodField,
)


class HostProviderSerializer(ModelSerializer):
    class Meta:
        model = HostProvider
        fields = ["id", "name", "display_name"]


class HostComponentSerializer(ModelSerializer):
    name = CharField(source="component.name")
    display_name = CharField(source="component.display_name")

    class Meta:
        model = HostComponent
        fields = ["id", "name", "display_name"]


class HostSerializer(ModelSerializer):
    status = SerializerMethodField()
    provider = HostProviderSerializer()
    components = HostComponentSerializer(source="hostcomponent_set", many=True)
    concerns = ConcernSerializer(many=True)

    class Meta:
        model = Host
        fields = [
            "id",
            "fqdn",
            "state",
            "status",
            "provider",
            "components",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
        ]

    @staticmethod
    def get_status(host: Host) -> int:
        return get_host_status(host=host)


class HostMappingSerializer(ModelSerializer):
    class Meta:
        model = Host
        fields = ["id", "name", "is_maintenance_mode_available", "maintenance_mode"]


class HostChangeMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

    class Meta:
        model = Host
        fields = ["maintenance_mode"]


class HostShortSerializer(ModelSerializer):
    class Meta:
        model = Host
        fields = ["id", "fqdn"]


class HostGroupConfigSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(queryset=Host.objects.all())

    class Meta:
        model = Host
        fields = ["id", "name"]
        extra_kwargs = {"name": {"read_only": True}}
