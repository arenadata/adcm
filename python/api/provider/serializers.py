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

import cm
from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.serializers import StringListSerializer, UpgradeSerializer, UrlField
from api.utils import (
    CommonAPIURL,
    ObjectURL,
    check_obj,
    filter_actions,
    get_upgradable_func,
    hlink,
)
from cm.adcm_config import get_main_info
from cm.errors import AdcmEx
from cm.models import Action, Prototype
from django.db import IntegrityError
from rest_framework import serializers


class ProviderSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    prototype_id = serializers.IntegerField()
    description = serializers.CharField(required=False)
    state = serializers.CharField(read_only=True)
    before_upgrade = serializers.JSONField(read_only=True)
    url = hlink('provider-details', 'id', 'provider_id')

    @staticmethod
    def validate_prototype_id(prototype_id):
        proto = check_obj(
            Prototype, {'id': prototype_id, 'type': 'provider'}, "PROTOTYPE_NOT_FOUND"
        )
        return proto

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        try:
            return cm.api.add_host_provider(
                validated_data.get('prototype_id'),
                validated_data.get('name'),
                validated_data.get('description', ''),
            )
        except IntegrityError:
            raise AdcmEx("PROVIDER_CONFLICT") from None


class ProviderDetailSerializer(ProviderSerializer):
    edition = serializers.CharField(read_only=True)
    license = serializers.CharField(read_only=True)
    bundle_id = serializers.IntegerField(read_only=True)
    prototype = hlink('provider-type-details', 'prototype_id', 'prototype_id')
    config = CommonAPIURL(view_name='object-config')
    action = CommonAPIURL(view_name='object-action')
    upgrade = hlink('provider-upgrade', 'id', 'provider_id')
    host = ObjectURL(read_only=True, view_name='host')
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = serializers.BooleanField(read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name='group-config-list')


class ProviderUISerializer(ProviderDetailSerializer):
    actions = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    upgradable = serializers.SerializerMethodField()
    get_upgradable = get_upgradable_func
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = serializers.SerializerMethodField()

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


class UpgradeProviderSerializer(UpgradeSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {'provider_id': self.context['provider_id'], 'upgrade_id': obj.id}

    url = MyUrlField(read_only=True, view_name='provider-upgrade-details')
    do = MyUrlField(read_only=True, view_name='do-provider-upgrade')

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
