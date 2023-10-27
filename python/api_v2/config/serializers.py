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

from cm.models import ADCM, ConfigLog
from rest_framework.serializers import (
    DateTimeField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
    ValidationError,
)


class ConfigLogListSerializer(ModelSerializer):
    is_current = SerializerMethodField()
    creation_time = DateTimeField(source="date", read_only=True)

    class Meta:
        model = ConfigLog
        fields = ["id", "is_current", "creation_time", "description"]

    @staticmethod
    def get_is_current(config_log: ConfigLog) -> bool:
        return config_log.id == config_log.obj_ref.current


class ConfigLogSerializer(ConfigLogListSerializer):
    adcm_meta = JSONField(source="attr")

    class Meta:
        model = ConfigLog
        fields = ["id", "is_current", "creation_time", "config", "adcm_meta", "description"]

    def validate_config(self, value):
        if isinstance(self.context["object_"], ADCM) and isinstance(value, dict):
            auth_policy = value.get("auth_policy")
            if not auth_policy:
                return value

            max_password_length = auth_policy.get("max_password_length")
            if not max_password_length:
                return value

            min_password_length = auth_policy.get("min_password_length")
            if not min_password_length:
                return value

            if min_password_length > max_password_length:
                raise ValidationError('"min_password_length" must be less or equal than "max_password_length"')

        return value
