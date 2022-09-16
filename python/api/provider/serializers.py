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

from django.db import IntegrityError
from rest_framework.serializers import (
    BooleanField,
    CharField,
    IntegerField,
    JSONField,
    SerializerMethodField,
)

from adcm.serializers import EmptySerializer
from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.serializers import DoUpgradeSerializer, StringListSerializer
from api.utils import (
    CommonAPIURL,
    ObjectURL,
    check_obj,
    filter_actions,
    get_upgradable_func,
    hlink,
)
from cm.adcm_config import get_main_info
from cm.api import add_host_provider
from cm.errors import AdcmEx
from cm.models import Action, Prototype, Upgrade
from cm.upgrade import do_upgrade


class ProviderSerializer(EmptySerializer):
    id = IntegerField(read_only=True)
    name = CharField()
    prototype_id = IntegerField()
    description = CharField(required=False)
    state = CharField(read_only=True)
    before_upgrade = JSONField(read_only=True)
    url = hlink('provider-details', 'id', 'provider_id')

    @staticmethod
    def validate_prototype_id(prototype_id):
        proto = check_obj(
            Prototype, {'id': prototype_id, 'type': 'provider'}, "PROTOTYPE_NOT_FOUND"
        )
        return proto

    def create(self, validated_data):
        try:
            return add_host_provider(
                validated_data.get('prototype_id'),
                validated_data.get('name'),
                validated_data.get('description', ''),
            )
        except IntegrityError:
            raise AdcmEx("PROVIDER_CONFLICT") from None


class ProviderDetailSerializer(ProviderSerializer):
    edition = CharField(read_only=True)
    license = CharField(read_only=True)
    bundle_id = IntegerField(read_only=True)
    prototype = hlink('provider-type-details', 'prototype_id', 'prototype_id')
    config = CommonAPIURL(view_name='object-config')
    action = CommonAPIURL(view_name='object-action')
    upgrade = hlink('provider-upgrade', 'id', 'provider_id')
    host = ObjectURL(read_only=True, view_name='host')
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = BooleanField(read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name='group-config-list')


class ProviderUISerializer(ProviderSerializer):
    edition = CharField(read_only=True)
    locked = BooleanField(read_only=True)
    action = CommonAPIURL(view_name='object-action')
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgrade = hlink('provider-upgrade', 'id', 'provider_id')
    upgradable = SerializerMethodField()
    get_upgradable = get_upgradable_func
    concerns = ConcernItemUISerializer(many=True, read_only=True)

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_prototype_name(self, obj):
        return obj.prototype.name

    def get_prototype_display_name(self, obj):
        return obj.prototype.display_name


class ProviderDetailUISerializer(ProviderDetailSerializer):
    actions = SerializerMethodField()
    prototype_version = SerializerMethodField()
    prototype_name = SerializerMethodField()
    prototype_display_name = SerializerMethodField()
    upgradable = SerializerMethodField()
    get_upgradable = get_upgradable_func
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['provider_id'] = obj.id
        actions = ActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

    @staticmethod
    def get_prototype_version(obj):
        return obj.prototype.version

    @staticmethod
    def get_prototype_name(obj):
        return obj.prototype.name

    @staticmethod
    def get_prototype_display_name(obj):
        return obj.prototype.display_name

    @staticmethod
    def get_main_info(obj):
        return get_main_info(obj)


class DoProviderUpgradeSerializer(DoUpgradeSerializer):
    def create(self, validated_data):
        upgrade = check_obj(Upgrade, validated_data.get('upgrade_id'), 'UPGRADE_NOT_FOUND')
        config = validated_data.get('config', {})
        attr = validated_data.get('attr', {})
        return do_upgrade(validated_data.get('obj'), upgrade, config, attr, [])
