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
from rest_framework import serializers

from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.serializers import StringListSerializer
from api.utils import hlink, check_obj, filter_actions, CommonAPIURL, ObjectURL
from cm.adcm_config import get_main_info
from cm.api import add_host
from cm.errors import AdcmEx
from cm.models import HostProvider, Prototype, Action, MaintenanceModeType
from cm.stack import validate_name
from cm.status_api import get_host_status

from cm.issue import update_hierarchy_issues, update_issue_after_deleting


class HostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    cluster_id = serializers.IntegerField(read_only=True)
    prototype_id = serializers.IntegerField(help_text='id of host type')
    provider_id = serializers.IntegerField()
    fqdn = serializers.CharField(help_text='fully qualified domain name')
    description = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(read_only=True)
    maintenance_mode = serializers.ChoiceField(choices=MaintenanceModeType.choices, read_only=True)
    url = ObjectURL(read_only=True, view_name='host-details')

    def validate_prototype_id(self, prototype_id):
        return check_obj(Prototype, {'id': prototype_id, 'type': 'host'})

    def validate_provider_id(self, provider_id):
        return check_obj(HostProvider, provider_id)

    def validate_fqdn(self, name):
        return validate_name(name, 'Host name')

    def create(self, validated_data):
        try:
            return add_host(
                validated_data.get('prototype_id'),
                validated_data.get('provider_id'),
                validated_data.get('fqdn'),
                validated_data.get('description', ''),
            )
        except IntegrityError:
            raise AdcmEx("HOST_CONFLICT", "duplicate host") from None


class HostDetailSerializer(HostSerializer):
    bundle_id = serializers.IntegerField(read_only=True)
    status = serializers.SerializerMethodField()
    config = CommonAPIURL(view_name='object-config')
    action = CommonAPIURL(view_name='object-action')
    prototype = hlink('host-type-details', 'prototype_id', 'prototype_id')
    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = serializers.BooleanField(read_only=True)

    def get_status(self, obj):
        return get_host_status(obj)


class HostUpdateSerializer(HostDetailSerializer):
    maintenance_mode = serializers.ChoiceField(choices=MaintenanceModeType.choices)

    def update(self, instance, validated_data):
        instance.maintenance_mode = validated_data.get(
            'maintenance_mode', instance.maintenance_mode
        )
        instance.save()
        update_hierarchy_issues(instance.cluster)
        update_hierarchy_issues(instance.provider)
        update_issue_after_deleting()
        return instance


class ClusterHostSerializer(HostSerializer):
    host_id = serializers.IntegerField(source='id')
    prototype_id = serializers.IntegerField(read_only=True)
    provider_id = serializers.IntegerField(read_only=True)
    fqdn = serializers.CharField(read_only=True)


class ProvideHostSerializer(HostSerializer):
    prototype_id = serializers.IntegerField(read_only=True)
    provider_id = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        provider = check_obj(HostProvider, self.context.get('provider_id'))
        proto = Prototype.obj.get(bundle=provider.prototype.bundle, type='host')
        try:
            return add_host(
                proto, provider, validated_data.get('fqdn'), validated_data.get('description', '')
            )
        except IntegrityError:
            raise AdcmEx("HOST_CONFLICT", "duplicate host") from None


class StatusSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    fqdn = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return get_host_status(obj)


class HostUISerializer(HostSerializer):
    cluster_name = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    def get_cluster_name(self, obj):
        if obj.cluster:
            return obj.cluster.name
        return None

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_prototype_name(self, obj):
        return obj.prototype.name

    def get_prototype_display_name(self, obj):
        return obj.prototype.display_name

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.name
        return None

    def get_status(self, obj):
        return get_host_status(obj)


class HostDetailUISerializer(HostDetailSerializer):
    actions = serializers.SerializerMethodField()
    cluster_name = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = serializers.SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['host_id'] = obj.id
        actions = ActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

    def get_cluster_name(self, obj):
        if obj.cluster:
            return obj.cluster.name
        return None

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_prototype_name(self, obj):
        return obj.prototype.name

    def get_prototype_display_name(self, obj):
        return obj.prototype.display_name

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.name
        return None

    def get_main_info(self, obj):
        return get_main_info(obj)
