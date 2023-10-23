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

from api_v2.cluster.serializers import ClusterRelatedSerializer
from api_v2.concern.serializers import ConcernSerializer
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from cm.adcm_config.config import get_main_info
from cm.errors import AdcmEx
from cm.models import ClusterObject, MaintenanceMode, ServiceComponent
from cm.status_api import get_obj_status
from rest_framework.serializers import (
    ChoiceField,
    IntegerField,
    ModelSerializer,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer


class ServiceRetrieveSerializer(ModelSerializer):
    prototype = PrototypeRelatedSerializer(read_only=True)
    cluster = ClusterRelatedSerializer(read_only=True)
    status = SerializerMethodField()
    concerns = ConcernSerializer(read_only=True, many=True)
    main_info = SerializerMethodField()

    class Meta:
        model = ClusterObject
        fields = [
            "id",
            "name",
            "display_name",
            "prototype",
            "cluster",
            "status",
            "state",
            "multi_state",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "main_info",
            "multi_state",
        ]

    def get_status(self, instance: ClusterObject) -> str:
        return get_obj_status(obj=instance)

    def get_main_info(self, instance: ClusterObject) -> str | None:
        return get_main_info(obj=instance)


class ServiceRelatedSerializer(ModelSerializer):
    class Meta:
        model = ClusterObject
        fields = ["id", "name", "display_name"]


class ServiceCreateSerializer(EmptySerializer):
    prototype_id = IntegerField()

    def validate_prototype_id(self, value: int) -> int:
        if ClusterObject.objects.filter(prototype__pk=value, cluster=self.context["cluster"]).exists():
            raise AdcmEx("SERVICE_CONFLICT")

        return value


class ServiceMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

    class Meta:
        model = ClusterObject
        fields = ["maintenance_mode"]


class ServiceNameSerializer(ModelSerializer):
    prototype = PrototypeRelatedSerializer(read_only=True)

    class Meta:
        model = ClusterObject
        fields = ["id", "name", "display_name", "state", "prototype"]


class RelatedComponentsStatusesSerializer(ModelSerializer):
    status = SerializerMethodField()

    @staticmethod
    def get_status(instance: ClusterObject) -> str:
        return get_obj_status(obj=instance)

    class Meta:
        model = ServiceComponent
        fields = ["id", "name", "display_name", "status"]


class ServiceStatusSerializer(ModelSerializer):
    components = RelatedComponentsStatusesSerializer(many=True, source="servicecomponent_set")

    class Meta:
        model = ClusterObject
        fields = ["components"]
