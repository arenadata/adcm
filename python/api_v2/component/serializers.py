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

from typing import Any

from api_v2.concern.serializers import ConcernSerializer
from api_v2.host.serializers import HostShortSerializer
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from api_v2.service.serializers import ServiceNameSerializer
from cm.adcm_config.config import get_main_info
from cm.models import (
    ConcernItem,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
)
from cm.status_api import get_obj_status
from django.contrib.contenttypes.models import ContentType
from rest_framework.serializers import (
    ChoiceField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.utils import get_requires


class ComponentMappingSerializer(ModelSerializer):
    service = ServiceNameSerializer(read_only=True)
    depend_on = SerializerMethodField()

    class Meta:
        model = ServiceComponent
        fields = [
            "id",
            "name",
            "display_name",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "constraint",
            "depend_on",
            "service",
        ]

    @staticmethod
    def get_depend_on(prototype: Prototype) -> list[dict[str, list[dict[str, Any]] | Any]] | None:
        return get_requires(prototype=prototype)


class ComponentSerializer(ModelSerializer):
    status = SerializerMethodField()
    hosts = SerializerMethodField()
    prototype = PrototypeRelatedSerializer(read_only=True)
    concerns = SerializerMethodField()
    main_info = SerializerMethodField()

    class Meta:
        model = ServiceComponent
        fields = [
            "id",
            "name",
            "display_name",
            "status",
            "hosts",
            "prototype",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "main_info",
        ]

    def get_status(self, instance: ServiceComponent) -> str:
        return get_obj_status(obj=instance)

    def get_hosts(self, instance: ServiceComponent) -> HostShortSerializer:
        host_pks = set()
        for host_component in HostComponent.objects.filter(component=instance).select_related("host"):
            host_pks.add(host_component.host_id)

        return HostShortSerializer(instance=Host.objects.filter(pk__in=host_pks), many=True).data

    def get_concerns(self, instance: ServiceComponent) -> ConcernSerializer:
        return ConcernSerializer(
            instance=ConcernItem.objects.filter(
                owner_type=ContentType.objects.get_for_model(model=ServiceComponent), owner_id=instance.pk
            ),
            many=True,
        ).data

    def get_main_info(self, instance: ServiceComponent) -> str | None:
        return get_main_info(obj=instance)


class ComponentMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

    class Meta:
        model = ServiceComponent
        fields = ["maintenance_mode"]
