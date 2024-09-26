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
from cm.models import MAINTENANCE_MODE_BOTH_CASES_CHOICES, Action, Component
from cm.status_api import get_component_status
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    HyperlinkedIdentityField,
    IntegerField,
    JSONField,
    ModelSerializer,
    SerializerMethodField,
)

from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.serializers import StringListSerializer
from api.utils import CommonAPIURL, ObjectURL, filter_actions


class ComponentSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    cluster_id = IntegerField(read_only=True)
    service_id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    display_name = CharField(read_only=True)
    description = CharField(read_only=True)
    state = CharField(read_only=True)
    prototype_id = IntegerField(required=True, help_text="id of component prototype")
    url = ObjectURL(read_only=True, view_name="v1:component-details")
    maintenance_mode = CharField(read_only=True)
    is_maintenance_mode_available = BooleanField(read_only=True)

    def to_representation(self, instance: Component) -> dict:
        data = super().to_representation(instance=instance)
        data["maintenance_mode"] = data["maintenance_mode"].upper()

        return data


class ComponentUISerializer(ComponentSerializer):
    action = CommonAPIURL(read_only=True, view_name="v1:object-action")
    version = SerializerMethodField()
    status = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    hostcomponent = HyperlinkedIdentityField(
        view_name="v1:host-component", lookup_field="cluster_id", lookup_url_kwarg="cluster_id"
    )

    @staticmethod
    def get_version(obj: Component) -> str:
        return obj.prototype.version

    @staticmethod
    def get_status(obj: Component) -> int:
        return get_component_status(obj)


class ComponentShortSerializer(ComponentSerializer):
    constraint = JSONField(read_only=True)
    requires = JSONField(read_only=True)
    bound_to = JSONField(read_only=True)
    bundle_id = IntegerField(read_only=True)
    prototype = HyperlinkedIdentityField(
        view_name="v1:component-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )


class ComponentDetailSerializer(ComponentSerializer):
    constraint = JSONField(read_only=True)
    requires = JSONField(read_only=True)
    bound_to = JSONField(read_only=True)
    bundle_id = IntegerField(read_only=True)
    monitoring = CharField(read_only=True)
    status = SerializerMethodField()
    action = CommonAPIURL(read_only=True, view_name="v1:object-action")
    config = CommonAPIURL(read_only=True, view_name="v1:object-config")
    prototype = HyperlinkedIdentityField(
        view_name="v1:component-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name="v1:group-config-list")

    @staticmethod
    def get_status(obj: Component) -> int:
        return get_component_status(obj)


class ComponentStatusSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    status = SerializerMethodField()

    @staticmethod
    def get_status(obj: Component) -> int:
        return get_component_status(obj)


class ComponentDetailUISerializer(ComponentDetailSerializer):
    actions = SerializerMethodField()
    version = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()
    hostcomponent = HyperlinkedIdentityField(
        view_name="v1:host-component", lookup_field="cluster_id", lookup_url_kwarg="cluster_id"
    )

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["component_id"] = obj.id
        actions = filter_actions(obj, act_set)
        acts = ActionShort(actions, many=True, context=self.context)

        return acts.data

    @staticmethod
    def get_version(obj: Component) -> str:
        return obj.prototype.version

    @staticmethod
    def get_main_info(obj: Component) -> str | None:
        return get_main_info(obj)


class ComponentChangeMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=MAINTENANCE_MODE_BOTH_CASES_CHOICES)

    class Meta:
        model = Component
        fields = ("maintenance_mode",)

    @staticmethod
    def validate_maintenance_mode(value: str) -> str:
        return value.lower()

    def to_representation(self, instance: Component) -> dict:
        data = super().to_representation(instance=instance)
        data["maintenance_mode"] = data["maintenance_mode"].upper()

        return data


class ComponentAuditSerializer(ModelSerializer):
    class Meta:
        model = Component
        fields = ("maintenance_mode",)

    def to_representation(self, instance: Component) -> dict:
        data = super().to_representation(instance=instance)
        data["maintenance_mode"] = data["maintenance_mode"].upper()

        return data
