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
from cm.api import add_host_provider
from cm.errors import AdcmEx
from cm.models import Action, Prototype, Provider, Upgrade
from cm.upgrade import do_upgrade, get_upgrade
from django.db import IntegrityError
from rest_framework.serializers import (
    BooleanField,
    CharField,
    HyperlinkedIdentityField,
    IntegerField,
    JSONField,
    SerializerMethodField,
)

from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.config_host_group.serializers import CHGsHyperlinkedIdentityField
from api.serializers import DoUpgradeSerializer, StringListSerializer
from api.utils import CommonAPIURL, ObjectURL, check_obj, filter_actions


class ProviderSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField()
    prototype_id = IntegerField()
    description = CharField(required=False)
    state = CharField(read_only=True)
    before_upgrade = JSONField(read_only=True)
    url = HyperlinkedIdentityField(view_name="v1:provider-details", lookup_field="id", lookup_url_kwarg="provider_id")

    @staticmethod
    def validate_prototype_id(prototype_id):
        return check_obj(Prototype, {"id": prototype_id, "type": "provider"}, "PROTOTYPE_NOT_FOUND")

    def create(self, validated_data):
        try:
            return add_host_provider(
                validated_data.get("prototype_id"),
                validated_data.get("name"),
                validated_data.get("description", ""),
            )
        except IntegrityError:
            raise AdcmEx("PROVIDER_CONFLICT") from None


class ProviderDetailSerializer(ProviderSerializer):
    edition = CharField(read_only=True)
    license = CharField(read_only=True)
    bundle_id = IntegerField(read_only=True)
    prototype = HyperlinkedIdentityField(
        view_name="v1:provider-prototype-detail",
        lookup_field="pk",
        lookup_url_kwarg="prototype_pk",
    )
    config = CommonAPIURL(view_name="v1:object-config")
    action = CommonAPIURL(view_name="v1:object-action")
    upgrade = HyperlinkedIdentityField(
        view_name="v1:provider-upgrade", lookup_field="id", lookup_url_kwarg="provider_id"
    )
    host = ObjectURL(read_only=True, view_name="v1:host")
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    group_config = CHGsHyperlinkedIdentityField(view_name="v1:group-config-list")


class ProviderUISerializer(ProviderSerializer):
    edition = CharField(read_only=True)
    locked = BooleanField(read_only=True)
    action = CommonAPIURL(view_name="v1:object-action")
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgrade = HyperlinkedIdentityField(
        view_name="v1:provider-upgrade", lookup_field="id", lookup_url_kwarg="provider_id"
    )
    upgradable = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)

    @staticmethod
    def get_upgradable(obj: Provider) -> bool:
        return bool(get_upgrade(obj))

    @staticmethod
    def get_prototype_version(obj: Provider) -> str:
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj: Provider) -> str:
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj: Provider) -> str | None:
        return obj.prototype.display_name


class ProviderDetailUISerializer(ProviderDetailSerializer):
    actions = SerializerMethodField()
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgradable = SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context["object"] = obj
        self.context["provider_id"] = obj.id
        actions = ActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

    @staticmethod
    def get_upgradable(obj: Provider) -> bool:
        return bool(get_upgrade(obj))

    @staticmethod
    def get_prototype_version(obj: Provider) -> str:
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj: Provider) -> str:
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj: Provider) -> str | None:
        return obj.prototype.display_name

    @staticmethod
    def get_main_info(obj: Provider) -> str | None:
        return get_main_info(obj)


class DoProviderUpgradeSerializer(DoUpgradeSerializer):
    def create(self, validated_data):
        upgrade = check_obj(Upgrade, validated_data.get("upgrade_id"), "UPGRADE_NOT_FOUND")
        config = validated_data.get("config", {})
        attr = validated_data.get("attr", {})
        return do_upgrade(validated_data.get("obj"), upgrade, config, attr, [])
