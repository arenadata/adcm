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

from api.utils import CommonAPIURL, get_api_url_kwargs
from cm.adcm_config.config import get_default, restore_cluster_config, ui_config
from cm.adcm_config.utils import group_is_activatable
from cm.api import update_obj_config
from cm.errors import AdcmEx, raise_adcm_ex
from cm.models import ConfigLog, PrototypeConfig
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    BooleanField,
    CharField,
    DateTimeField,
    HyperlinkedIdentityField,
    IntegerField,
    JSONField,
    SerializerMethodField,
)
from rest_framework.status import HTTP_400_BAD_REQUEST

from adcm.serializers import EmptySerializer


class ConfigVersionURL(HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, _format):
        kwargs = get_api_url_kwargs(self.context.get("object"), request)
        kwargs["version"] = obj.id
        return reverse(view_name, kwargs=kwargs, request=request, format=_format)


class HistoryCurrentPreviousConfigSerializer(EmptySerializer):
    history = CommonAPIURL(read_only=True, view_name="v1:config-history")
    current = CommonAPIURL(read_only=True, view_name="v1:config-current")
    previous = CommonAPIURL(read_only=True, view_name="v1:config-previous")


class ConfigObjectConfigSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    date = DateTimeField(read_only=True)
    description = CharField(required=False, allow_blank=True)
    config = JSONField()
    attr = JSONField(required=False)


class ObjectConfigUpdateSerializer(ConfigObjectConfigSerializer):
    def validate(self, attrs: dict) -> dict:
        if not isinstance(attrs["config"], dict):
            return attrs

        auth_policy = attrs["config"].get("auth_policy")
        if not auth_policy:
            return attrs

        max_password_length = auth_policy.get("max_password_length")
        if not max_password_length:
            return attrs

        min_password_length = auth_policy.get("min_password_length")
        if not min_password_length:
            return attrs

        if min_password_length > max_password_length:
            raise_adcm_ex(
                code="CONFIG_VALUE_ERROR",
                msg='"min_password_length" must be less or equal than "max_password_length"',
            )

        return attrs

    def update(self, instance: ConfigLog, validated_data: dict) -> ConfigLog:
        conf = validated_data.get("config")
        attr = validated_data.get("attr", {})
        desc = validated_data.get("description", "")

        if not isinstance(conf, dict) or not isinstance(attr, dict):
            message = "Fields `config` and `attr` should be objects when specified"
            raise AdcmEx(code="INVALID_CONFIG_UPDATE", http_code=HTTP_400_BAD_REQUEST, msg=message)

        config_log = update_obj_config(instance.obj_ref, conf, attr, desc)

        if validated_data.get("ui"):
            config_log.config = ui_config(validated_data.get("obj"), config_log)

        return config_log


class ObjectConfigRestoreSerializer(ConfigObjectConfigSerializer):
    config = JSONField(read_only=True)

    def update(self, instance, validated_data):
        return restore_cluster_config(
            instance.obj_ref,
            instance.id,
            validated_data.get("description", instance.description),
        )


class ConfigHistorySerializer(FlexFieldsSerializerMixin, ConfigObjectConfigSerializer):
    url = ConfigVersionURL(read_only=True, view_name="v1:config-history-version")


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
