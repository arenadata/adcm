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

from api.serializers import (
    MultiHyperlinkedIdentityField,
    MultiHyperlinkedRelatedField,
    UIConfigField,
)
from cm.api import update_obj_config
from cm.errors import AdcmEx
from cm.models import ConfigLog, GroupConfig, Host, ObjectConfig
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.transaction import atomic
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework import serializers
from rest_framework.reverse import reverse


class HostFlexFieldsSerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Host
        fields = (
            "id",
            "cluster_id",
            "prototype_id",
            "provider_id",
            "fqdn",
            "state",
        )


def check_object_type(type_name):
    """Object type checking"""
    if type_name not in ["cluster", "service", "component", "provider"]:
        raise AdcmEx("GROUP_CONFIG_TYPE_ERROR")


def translate_model_name(model_name):
    """Translating model name to display model name"""
    if model_name == "clusterobject":
        return "service"
    elif model_name == "servicecomponent":
        return "component"
    elif model_name == "hostprovider":
        return "provider"
    else:
        return model_name


def revert_model_name(name):
    """Translating display model name to model name"""
    if name == "service":
        return "clusterobject"
    elif name == "component":
        return "servicecomponent"
    elif name == "provider":
        return "hostprovider"
    else:
        return name


class ObjectTypeField(serializers.Field):
    def to_representation(self, value):
        return translate_model_name(value.model)

    def to_internal_value(self, data):
        check_object_type(data)
        return ContentType.objects.get(app_label="cm", model=revert_model_name(data))


class GroupConfigsHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    """Return url for group_config for Cluster, Provider, Component or Service"""

    def get_url(self, obj, view_name, request, _format):  # pylint: disable=redefined-builtin
        url = reverse(viewname=view_name, request=request, format=_format)
        return f"{url}?object_id={obj.id}&object_type={obj.prototype.type}"


class GroupConfigSerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    object_type = ObjectTypeField()
    url = serializers.HyperlinkedIdentityField(view_name="v1:group-config-detail")
    hosts = serializers.HyperlinkedRelatedField(
        view_name="v1:group-config-host-list",
        read_only=True,
        lookup_url_kwarg="parent_lookup_group_config",
        source="*",
    )
    config = MultiHyperlinkedRelatedField(
        "v1:group-config-config-detail",
        "parent_lookup_group_config",
        lookup_field="config_id",
        lookup_url_kwarg="pk",
        source="*",
    )
    host_candidate = serializers.HyperlinkedRelatedField(
        view_name="v1:group-config-host-candidate-list",
        read_only=True,
        lookup_url_kwarg="parent_lookup_group_config",
        source="*",
    )

    class Meta:
        model = GroupConfig
        fields = (
            "id",
            "object_id",
            "object_type",
            "name",
            "description",
            "hosts",
            "config",
            "config_id",
            "host_candidate",
            "url",
        )
        expandable_fields = {
            "hosts": (HostFlexFieldsSerializer, {"many": True}),
            "host_candidate": (HostFlexFieldsSerializer, {"many": True}),
        }

    def validate(self, attrs):
        object_type = attrs.get("object_type")
        object_id = attrs.get("object_id")
        if object_type is not None and object_id is not None:
            obj_model = object_type.model_class()
            try:
                obj_model.objects.get(id=object_id)
            except obj_model.DoesNotExist:
                error_dict = {"object_id": [f'Invalid pk "{object_id}" - object does not exist.']}
                raise ValidationError(error_dict, "does_not_exist") from None
        return super().validate(attrs)


class GroupConfigHostSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Host.objects.all())
    url = MultiHyperlinkedIdentityField("v1:group-config-host-detail", "parent_lookup_group_config", "host_id")

    class Meta:
        model = Host
        fields = (
            "id",
            "cluster_id",
            "prototype_id",
            "provider_id",
            "fqdn",
            "description",
            "state",
            "maintenance_mode",
            "bundle_id",
            "locked",
            "url",
        )
        read_only_fields = (
            "state",
            "fqdn",
            "description",
            "prototype_id",
            "provider_id",
            "cluster_id",
            "maintenance_mode",
            "bundle_id",
            "locked",
        )

    def to_representation(self, instance: Host) -> dict:
        data = super().to_representation(instance=instance)
        data["maintenance_mode"] = data["maintenance_mode"].upper()

        return data


class GroupConfigHostCandidateSerializer(GroupConfigHostSerializer):
    """Serializer for host candidate"""

    url = MultiHyperlinkedIdentityField(
        "v1:group-config-host-candidate-detail", "parent_lookup_group_config", "host_id"
    )


class GroupConfigConfigSerializer(serializers.ModelSerializer):
    current = MultiHyperlinkedRelatedField(
        "v1:group-config-config-log-detail",
        "parent_lookup_obj_ref__group_config",
        "parent_lookup_obj_ref",
        lookup_field="current",
        lookup_url_kwarg="pk",
        source="*",
    )
    current_id = serializers.IntegerField(source="current")
    previous = MultiHyperlinkedRelatedField(
        "v1:group-config-config-log-detail",
        "parent_lookup_obj_ref__group_config",
        "parent_lookup_obj_ref",
        lookup_field="previous",
        lookup_url_kwarg="pk",
        source="*",
    )
    previous_id = serializers.IntegerField(source="previous")
    history = serializers.SerializerMethodField()
    url = MultiHyperlinkedIdentityField("v1:group-config-config-detail", "parent_lookup_group_config", "pk")

    class Meta:
        model = ObjectConfig
        fields = ("id", "current", "current_id", "previous", "previous_id", "history", "url")

    def get_history(self, obj):
        kwargs = {
            "parent_lookup_obj_ref__group_config": obj.group_config.id,
            "parent_lookup_obj_ref": obj.id,
        }
        return reverse(
            "group-config-config-log-list",
            kwargs=kwargs,
            request=self.context["request"],
            format=self.context["format"],
        )


class GroupConfigConfigLogSerializer(serializers.ModelSerializer):
    url = MultiHyperlinkedRelatedField(
        "v1:group-config-config-log-detail",
        "parent_lookup_obj_ref__group_config",
        "parent_lookup_obj_ref",
        source="*",
    )

    class Meta:
        model = ConfigLog
        fields = ("id", "date", "description", "config", "attr", "url")
        extra_kwargs = {"config": {"required": True}}

    @atomic
    def create(self, validated_data):
        object_config = self.context.get("obj_ref")
        config = validated_data.get("config")
        attr = validated_data.get("attr", {})
        description = validated_data.get("description", "")
        config_log = update_obj_config(object_config, config, attr, description)

        return config_log


class UIGroupConfigConfigLogSerializer(GroupConfigConfigLogSerializer):
    config = UIConfigField(source="*")

    class Meta:
        model = ConfigLog
        fields = ("id", "date", "description", "config", "attr", "url")
