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

from adcm.serializers import EmptySerializer
from cm.adcm_config.config import get_main_info
from cm.models import Component, MaintenanceMode, Service
from rest_framework.serializers import (
    ChoiceField,
    IntegerField,
    ModelSerializer,
    SerializerMethodField,
)

from api_v2.cluster.serializers import ClusterRelatedSerializer
from api_v2.concern.serializers import ConcernSerializer
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from api_v2.serializers import WithStatusSerializer


class ServiceRetrieveSerializer(WithStatusSerializer):
    prototype = PrototypeRelatedSerializer(read_only=True)
    cluster = ClusterRelatedSerializer(read_only=True)
    concerns = ConcernSerializer(read_only=True, many=True)
    main_info = SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
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

    def get_main_info(self, instance: Service) -> str | None:
        return get_main_info(obj=instance)


class ServiceRelatedSerializer(ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "display_name"]


class ServiceCreateSerializer(EmptySerializer):
    prototype_id = IntegerField()


class ServiceMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

    class Meta:
        model = Service
        fields = ["maintenance_mode"]


class RelatedComponentsStatusesSerializer(WithStatusSerializer):
    class Meta:
        model = Component
        fields = ["id", "name", "display_name", "status"]


class ServiceStatusSerializer(ModelSerializer):
    components = RelatedComponentsStatusesSerializer(many=True)

    class Meta:
        model = Service
        fields = ["components"]


class ServiceAuditSerializer(ModelSerializer):
    class Meta:
        model = Service
        fields = ["maintenance_mode"]
