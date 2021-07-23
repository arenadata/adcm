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

import cm
from cm.errors import AdcmEx
from cm.models import Cluster, Host, HostProvider, Prototype, Action
from api.api_views import hlink, check_obj, filter_actions, CommonAPIURL, ObjectURL
from api.action.serializers import ActionShort
from api.concern.serializers import ConcernItemSerializer


class HostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    cluster_id = serializers.IntegerField(read_only=True)
    prototype_id = serializers.IntegerField(help_text='id of host type')
    provider_id = serializers.IntegerField()
    fqdn = serializers.CharField(help_text='fully qualified domain name')
    description = serializers.CharField(required=False)
    state = serializers.CharField(read_only=True)
    url = ObjectURL(read_only=True, view_name='host-details')

    def get_issue(self, obj):
        return cm.issue.aggregate_issues(obj)

    def validate_prototype_id(self, prototype_id):
        return check_obj(Prototype, {'id': prototype_id, 'type': 'host'})

    def validate_provider_id(self, provider_id):
        return check_obj(HostProvider, provider_id)

    def validate_fqdn(self, name):
        return cm.stack.validate_name(name, 'Host name')

    def create(self, validated_data):
        try:
            return cm.api.add_host(
                validated_data.get('prototype_id'),
                validated_data.get('provider_id'),
                validated_data.get('fqdn'),
                validated_data.get('description', ''),
            )
        except IntegrityError:
            raise AdcmEx("HOST_CONFLICT", "duplicate host") from None


class HostDetailSerializer(HostSerializer):
    # stack = serializers.JSONField(read_only=True)
    issue = serializers.SerializerMethodField()
    bundle_id = serializers.IntegerField(read_only=True)
    status = serializers.SerializerMethodField()
    config = CommonAPIURL(view_name='object-config')
    action = CommonAPIURL(view_name='object-action')
    prototype = hlink('host-type-details', 'prototype_id', 'prototype_id')
    concern = ConcernItemSerializer(many=True, read_only=True)

    def get_issue(self, obj):
        return cm.issue.aggregate_issues(obj)

    def get_status(self, obj):
        return cm.status_api.get_host_status(obj.id)


class ClusterHostSerializer(HostSerializer):
    host_id = serializers.IntegerField(source='id')
    prototype_id = serializers.IntegerField(read_only=True)
    provider_id = serializers.IntegerField(read_only=True)
    fqdn = serializers.CharField(read_only=True)

    def create(self, validated_data):
        cluster = check_obj(Cluster, self.context.get('cluster_id'))
        host = check_obj(Host, validated_data.get('id'))
        cm.api.add_host_to_cluster(cluster, host)
        return host


class ProvideHostSerializer(HostSerializer):
    prototype_id = serializers.IntegerField(read_only=True)
    provider_id = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        provider = check_obj(HostProvider, self.context.get('provider_id'))
        proto = Prototype.obj.get(bundle=provider.prototype.bundle, type='host')
        try:
            return cm.api.add_host(
                proto, provider, validated_data.get('fqdn'), validated_data.get('description', '')
            )
        except IntegrityError:
            raise AdcmEx("HOST_CONFLICT", "duplicate host") from None


class HostUISerializer(HostDetailSerializer):
    actions = serializers.SerializerMethodField()
    cluster_name = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()

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
