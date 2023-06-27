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

from cm.adcm_config.config import get_default
from cm.adcm_config.utils import group_is_activatable
from cm.models import ConfigLog, PrototypeConfig
from rest_framework.fields import BooleanField, CharField, JSONField
from rest_framework.serializers import (
    DateTimeField,
    ModelSerializer,
    SerializerMethodField,
    ValidationError,
)

from adcm.serializers import EmptySerializer


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
    class Meta:
        model = ConfigLog
        fields = ["id", "is_current", "creation_time", "config", "attr", "description"]

    def validate_config(self, value):
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


class ConfigSerializer(EmptySerializer):
    name = CharField()
    description = CharField(required=False)
    display_name = SerializerMethodField()
    subname = CharField()
    default = SerializerMethodField(method_name="get_default_field")
    value = SerializerMethodField()
    type = CharField()
    limits = JSONField(required=False)
    ui_options = JSONField(required=False)
    required = BooleanField()

    @staticmethod
    def get_display_name(obj: PrototypeConfig) -> str:
        if not obj.display_name:
            return obj.name

        return obj.display_name

    @staticmethod
    def get_default_field(obj: PrototypeConfig) -> Any:
        return get_default(obj)

    def get_value(self, obj: PrototypeConfig) -> Any:  # pylint: disable=arguments-renamed
        proto = self.context.get("prototype", None)
        return get_default(obj, proto)


class ConfigSerializerUI(ConfigSerializer):
    activatable = SerializerMethodField()

    @staticmethod
    def get_activatable(obj):
        return bool(group_is_activatable(obj))
