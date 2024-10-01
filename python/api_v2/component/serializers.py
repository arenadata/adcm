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

from cm.adcm_config.config import get_main_info
from cm.models import Component, Host, HostComponent, MaintenanceMode
from drf_spectacular.utils import extend_schema_field
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    IntegerField,
    ModelSerializer,
    SerializerMethodField,
)

from api_v2.cluster.serializers import ClusterRelatedSerializer
from api_v2.concern.serializers import ConcernSerializer
from api_v2.host.serializers import HostShortSerializer
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from api_v2.serializers import WithStatusSerializer
from api_v2.service.serializers import ServiceRelatedSerializer


class ComponentSerializer(WithStatusSerializer):
    hosts = SerializerMethodField()
    prototype = PrototypeRelatedSerializer(read_only=True)
    cluster = ClusterRelatedSerializer(read_only=True)
    service = ServiceRelatedSerializer(read_only=True)
    concerns = ConcernSerializer(read_only=True, many=True)
    main_info = SerializerMethodField()

    class Meta:
        model = Component
        fields = [
            "id",
            "name",
            "display_name",
            "status",
            "state",
            "multi_state",
            "hosts",
            "prototype",
            "cluster",
            "service",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "main_info",
        ]

    @extend_schema_field(field=HostShortSerializer(many=True))
    def get_hosts(self, instance: Component) -> HostShortSerializer:
        host_pks = set()
        for host_component in HostComponent.objects.filter(component=instance).select_related("host"):
            host_pks.add(host_component.host_id)

        return HostShortSerializer(instance=Host.objects.filter(pk__in=host_pks), many=True).data

    def get_main_info(self, instance: Component) -> str | None:
        return get_main_info(obj=instance)


class ComponentMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

    class Meta:
        model = Component
        fields = ["maintenance_mode"]


class RelatedHostComponentsStatusSerializer(WithStatusSerializer):
    id = IntegerField(source="host.id")
    name = CharField(source="host.name")

    class Meta:
        model = HostComponent
        fields = ["id", "name", "status"]


class ComponentStatusSerializer(ModelSerializer):
    host_components = RelatedHostComponentsStatusSerializer(many=True, source="hostcomponent_set")

    class Meta:
        model = Component
        fields = ["host_components"]


class HostComponentSerializer(WithStatusSerializer):
    concerns = ConcernSerializer(read_only=True, many=True)
    cluster = ClusterRelatedSerializer(read_only=True)
    service = ServiceRelatedSerializer(read_only=True)
    prototype = PrototypeRelatedSerializer(read_only=True)

    class Meta:
        model = Component
        fields = [
            "id",
            "name",
            "display_name",
            "status",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "cluster",
            "service",
            "prototype",
        ]


class ComponentAuditSerializer(ModelSerializer):
    class Meta:
        model = Component
        fields = ["maintenance_mode"]
