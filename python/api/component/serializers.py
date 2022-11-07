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

# pylint: disable=redefined-builtin

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

from adcm.serializers import EmptySerializer
from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.serializers import StringListSerializer
from api.utils import CommonAPIURL, ObjectURL, filter_actions
from cm.adcm_config import get_main_info
from cm.models import Action, MaintenanceMode, ServiceComponent
from cm.status_api import get_component_status


class ComponentSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    cluster_id = IntegerField(read_only=True)
    service_id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    display_name = CharField(read_only=True)
    description = CharField(read_only=True)
    state = CharField(read_only=True)
    prototype_id = IntegerField(required=True, help_text="id of component prototype")
    url = ObjectURL(read_only=True, view_name="component-details")
    maintenance_mode = CharField(read_only=True)
    is_maintenance_mode_available = BooleanField(read_only=True)


class ComponentUISerializer(ComponentSerializer):
    action = CommonAPIURL(read_only=True, view_name="object-action")
    version = SerializerMethodField()
    status = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)

    @staticmethod
    def get_version(obj: ServiceComponent) -> str:
        return obj.prototype.version

    @staticmethod
    def get_status(obj: ServiceComponent) -> int:
        return get_component_status(obj)


class ComponentShortSerializer(ComponentSerializer):
    constraint = JSONField(read_only=True)
    requires = JSONField(read_only=True)
    bound_to = JSONField(read_only=True)
    bundle_id = IntegerField(read_only=True)
    prototype = HyperlinkedIdentityField(
        view_name="component-prototype-detail",
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
    action = CommonAPIURL(read_only=True, view_name="object-action")
    config = CommonAPIURL(read_only=True, view_name="object-config")
    prototype = HyperlinkedIdentityField(
        view_name="component-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name="group-config-list")

    @staticmethod
    def get_status(obj: ServiceComponent) -> int:
        return get_component_status(obj)


class StatusSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField(read_only=True)
    status = SerializerMethodField()

    @staticmethod
    def get_status(obj: ServiceComponent) -> int:
        return get_component_status(obj)


class ComponentDetailUISerializer(ComponentDetailSerializer):
    actions = SerializerMethodField()
    version = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["component_id"] = obj.id
        actions = filter_actions(obj, act_set)
        acts = ActionShort(actions, many=True, context=self.context)

        return acts.data

    @staticmethod
    def get_version(obj: ServiceComponent) -> str:
        return obj.prototype.version

    @staticmethod
    def get_main_info(obj: ServiceComponent) -> str | None:
        return get_main_info(obj)


class ComponentChangeMaintenanceModeSerializer(ModelSerializer):
    maintenance_mode = ChoiceField(choices=(MaintenanceMode.ON, MaintenanceMode.OFF))

    class Meta:
        model = ServiceComponent
        fields = ("maintenance_mode",)


class ComponentAuditSerializer(ModelSerializer):
    class Meta:
        model = ServiceComponent
        fields = ("maintenance_mode",)
