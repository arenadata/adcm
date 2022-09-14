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

from django.db.utils import IntegrityError
from rest_framework import serializers
from rest_framework.reverse import reverse

from api.action.serializers import ActionShort
from api.cluster.serializers import BindSerializer
from api.component.serializers import ComponentUISerializer
from api.concern.serializers import ConcernItemSerializer, ConcernItemUISerializer
from api.group_config.serializers import GroupConfigsHyperlinkedIdentityField
from api.serializers import StringListSerializer
from api.utils import CommonAPIURL, ObjectURL, check_obj, filter_actions
from cm import status_api
from cm.adcm_config import get_main_info
from cm.api import add_service_to_cluster, bind, multi_bind
from cm.errors import AdcmEx
from cm.models import Action, Cluster, Prototype, ServiceComponent


class ServiceSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    cluster_id = serializers.IntegerField(required=True)
    name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    prototype_id = serializers.IntegerField(required=True, help_text='id of service prototype')
    url = ObjectURL(read_only=True, view_name='service-details')

    def validate_prototype_id(self, prototype_id):
        check_obj(Prototype, {'id': prototype_id, 'type': 'service'}, 'PROTOTYPE_NOT_FOUND')
        return prototype_id

    def create(self, validated_data):
        try:
            cluster = check_obj(Cluster, validated_data['cluster_id'])
            prototype = check_obj(Prototype, validated_data['prototype_id'])
            return add_service_to_cluster(cluster, prototype)
        except IntegrityError:
            raise AdcmEx('SERVICE_CONFLICT') from None


class ServiceUISerializer(ServiceSerializer):
    action = CommonAPIURL(read_only=True, view_name='object-action')
    actions = serializers.SerializerMethodField()
    name = serializers.CharField(read_only=True)
    version = serializers.SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    locked = serializers.BooleanField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['service_id'] = obj.id
        actions = filter_actions(obj, act_set)
        acts = ActionShort(actions, many=True, context=self.context)
        return acts.data

    def get_version(self, obj):
        return obj.prototype.version

    def get_status(self, obj):
        return status_api.get_service_status(obj)


class ClusterServiceSerializer(ServiceSerializer):
    cluster_id = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        try:
            cluster = check_obj(Cluster, self.context.get('cluster_id'))
            prototype = check_obj(Prototype, validated_data['prototype_id'])
            return add_service_to_cluster(cluster, prototype)
        except IntegrityError:
            raise AdcmEx('SERVICE_CONFLICT') from None


class ServiceDetailSerializer(ServiceSerializer):
    prototype_id = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True)
    bundle_id = serializers.IntegerField(read_only=True)
    status = serializers.SerializerMethodField()
    monitoring = serializers.CharField(read_only=True)
    action = CommonAPIURL(read_only=True, view_name='object-action')
    config = CommonAPIURL(read_only=True, view_name='object-config')
    component = ObjectURL(read_only=True, view_name='component')
    imports = ObjectURL(read_only=True, view_name='service-import')
    bind = ObjectURL(read_only=True, view_name='service-bind')
    prototype = serializers.HyperlinkedIdentityField(
        view_name='service-type-details',
        lookup_field='prototype_id',
        lookup_url_kwarg='prototype_id',
    )

    multi_state = StringListSerializer(read_only=True)
    concerns = ConcernItemSerializer(many=True, read_only=True)
    locked = serializers.BooleanField(read_only=True)
    group_config = GroupConfigsHyperlinkedIdentityField(view_name='group-config-list')

    def get_status(self, obj):
        return status_api.get_service_status(obj)


class ServiceDetailUISerializer(ServiceDetailSerializer):
    actions = serializers.SerializerMethodField()
    components = serializers.SerializerMethodField()
    name = serializers.CharField(read_only=True)
    version = serializers.SerializerMethodField()
    concerns = ConcernItemUISerializer(many=True, read_only=True)
    main_info = serializers.SerializerMethodField()

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['service_id'] = obj.id
        actions = filter_actions(obj, act_set)
        acts = ActionShort(actions, many=True, context=self.context)
        return acts.data

    def get_components(self, obj):
        comps = ServiceComponent.objects.filter(service=obj, cluster=obj.cluster)
        return ComponentUISerializer(comps, many=True, context=self.context).data

    def get_version(self, obj):
        return obj.prototype.version

    def get_main_info(self, obj):
        return get_main_info(obj)


class ImportPostSerializer(serializers.Serializer):
    bind = serializers.JSONField()

    def create(self, validated_data):
        binds = validated_data.get('bind')
        service = self.context.get('service')
        cluster = self.context.get('cluster')
        return multi_bind(cluster, service, binds)


class ServiceBindUrlFiels(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        kwargs = {'service_id': obj.service.id, 'bind_id': obj.id}
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class ServiceBindSerializer(BindSerializer):
    url = ServiceBindUrlFiels(read_only=True, view_name='service-bind-details')


class ServiceBindPostSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    export_cluster_id = serializers.IntegerField()
    export_service_id = serializers.IntegerField(required=False)
    export_cluster_name = serializers.CharField(read_only=True)
    export_service_name = serializers.CharField(read_only=True)
    export_cluster_prototype_name = serializers.CharField(read_only=True)

    def create(self, validated_data):
        export_cluster = check_obj(Cluster, validated_data.get('export_cluster_id'))
        return bind(
            validated_data.get('cluster'),
            validated_data.get('service'),
            export_cluster,
            validated_data.get('export_service_id'),
        )


class StatusSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return status_api.get_service_status(obj)
