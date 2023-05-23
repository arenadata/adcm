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

from cm.models import Prototype, ServiceComponent
from rest_framework.serializers import CharField, ModelSerializer, SerializerMethodField

from adcm.utils import get_requires


class ServiceComponentSerializer(ModelSerializer):
    service_name = CharField(source="service.name")
    service_display_name = CharField(source="service.display_name")
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
            "service_id",
            "service_name",
            "service_display_name",
            "depend_on",
        ]

    @staticmethod
    def get_depend_on(prototype: Prototype) -> list[dict[str, list[dict[str, Any]] | Any]] | None:
        return get_requires(prototype=prototype)
