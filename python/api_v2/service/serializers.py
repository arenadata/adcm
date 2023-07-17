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
from api_v2.prototype.serializers import PrototypeRelatedSerializer
from cm.adcm_config.config import get_main_info
from cm.models import ClusterObject, MaintenanceMode
from cm.status_api import get_obj_status
from rest_framework.serializers import (
    ChoiceField,
    ModelSerializer,
    SerializerMethodField,
)


class ServiceRetrieveSerializer(ModelSerializer):
    prototype = PrototypeRelatedSerializer(read_only=True)
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
            "status",
            "state",
            "concerns",
            "is_maintenance_mode_available",
            "maintenance_mode",
            "main_info",
        ]

    def get_status(self, instance: ClusterObject) -> str:
        return get_obj_status(obj=instance)

    def get_main_info(self, instance: ClusterObject) -> str | None:
        return get_main_info(obj=instance)


class ServiceCreateSerializer(ModelSerializer):
    class Meta:
        model = ClusterObject
        fields = ["prototype"]


class ServiceMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON.value, MaintenanceMode.OFF.value))

    class Meta:
        model = ClusterObject
        fields = ["maintenance_mode"]
