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

import cm.api
import cm.job
import cm.status_api
from cm.api import safe_api
from cm.logger import log   # pylint: disable=unused-import
from cm.errors import AdcmApiEx, AdcmEx
from cm.models import Action, Cluster, Host, Prototype, ServiceComponent

from api.serializers import (
    check_obj, filter_actions, get_upgradable_func, hlink, UrlField, ClusterActionShort,
    ClusterHostActionShort, ServiceActionShort
)
from api.config.serializers import ConfigURL


def get_cluster_id(obj):
    if hasattr(obj.obj_ref, 'clusterobject'):
        return obj.obj_ref.clusterobject.cluster.id
    else:
        return obj.obj_ref.cluster.id


class ClusterBundleSerializer(serializers.Serializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {'prototype_id': obj.id}

    service = MyUrlField(read_only=True, view_name='service-type-details')
    service_id = serializers.IntegerField(read_only=True, source='id')
    description = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)


class ClusterSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    prototype_id = serializers.IntegerField(help_text='id of cluster type')
    name = serializers.CharField(help_text='cluster name')
    description = serializers.CharField(help_text='cluster description', required=False)
    state = serializers.CharField(read_only=True)
    url = hlink('cluster-details', 'id', 'cluster_id')

    def validate_prototype_id(self, prototype_id):
        cluster = check_obj(
            Prototype, {'id': prototype_id, 'type': 'cluster'}, "PROTOTYPE_NOT_FOUND"
        )
        return cluster

    def create(self, validated_data):
        try:
            return cm.api.add_cluster(
                validated_data.get('prototype_id'),
                validated_data.get('name'),
                validated_data.get('description', ''),
            )
        except Prototype.DoesNotExist:
            raise AdcmApiEx('PROTOTYPE_NOT_FOUND') from None
        except IntegrityError:
            raise AdcmApiEx("CLUSTER_CONFLICT") from None
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        try:
            instance.save()
        except IntegrityError:
            msg = 'cluster with name "{}" already exists'.format(instance.name)
            raise AdcmApiEx("CLUSTER_CONFLICT", msg) from None
        return instance


class ClusterDetailSerializer(ClusterSerializer):
    # stack = serializers.JSONField(read_only=True)
    issue = serializers.SerializerMethodField()
    bundle_id = serializers.IntegerField(read_only=True)
    edition = serializers.CharField(read_only=True)
    license = serializers.CharField(read_only=True)
    action = hlink('cluster-action', 'id', 'cluster_id')
    service = hlink('cluster-service', 'id', 'cluster_id')
    host = hlink('cluster-host', 'id', 'cluster_id')
    hostcomponent = hlink('host-component', 'id', 'cluster_id')
    status = serializers.SerializerMethodField()
    status_url = hlink('cluster-status', 'id', 'cluster_id')
    config = ConfigURL(view_name='config')
    serviceprototype = hlink('cluster-service-prototype', 'id', 'cluster_id')
    upgrade = hlink('cluster-upgrade', 'id', 'cluster_id')
    imports = hlink('cluster-import', 'id', 'cluster_id')
    bind = hlink('cluster-bind', 'id', 'cluster_id')
    prototype = hlink('cluster-type-details', 'prototype_id', 'prototype_id')

    def get_issue(self, obj):
        return cm.issue.get_issue(obj)

    def get_status(self, obj):
        return cm.status_api.get_cluster_status(obj.id)


class ClusterUISerializer(ClusterDetailSerializer):
    actions = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    upgradable = serializers.SerializerMethodField()
    get_upgradable = get_upgradable_func

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['cluster_id'] = obj.id
        actions = ClusterActionShort(filter_actions(obj, act_set), many=True, context=self.context)
        return actions.data

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_prototype_name(self, obj):
        return obj.prototype.name

    def get_prototype_display_name(self, obj):
        return obj.prototype.display_name


class ClusterHostUrlField(UrlField):
    def get_kwargs(self, obj):
        return {'cluster_id': obj.cluster.id, 'host_id': obj.id}


class ClusterHostSerializer(serializers.Serializer):
    state = serializers.CharField(read_only=True)
    # stack = serializers.JSONField(read_only=True)
    cluster_id = serializers.IntegerField(read_only=True)
    fqdn = serializers.CharField(read_only=True)
    id = serializers.IntegerField(help_text='host id', read_only=True)
    host_id = serializers.IntegerField(source='id')
    prototype_id = serializers.IntegerField(read_only=True)
    provider_id = serializers.IntegerField(read_only=True)
    url = ClusterHostUrlField(read_only=True, view_name='cluster-host-details')


class ClusterHostDetailSerializer(ClusterHostSerializer):
    issue = serializers.SerializerMethodField()
    action = ClusterHostUrlField(read_only=True, view_name='cluster-host-action')
    cluster_url = hlink('cluster-details', 'cluster_id', 'cluster_id')
    status = serializers.SerializerMethodField()
    monitoring = serializers.CharField(read_only=True)
    host_url = hlink('host-details', 'id', 'host_id')
    config = ConfigURL(view_name='config')

    def get_issue(self, obj):
        return cm.issue.get_issue(obj)

    def get_status(self, obj):
        return cm.status_api.get_host_status(obj.id)


class ClusterHostAddSerializer(ClusterHostDetailSerializer):
    host_id = serializers.IntegerField(source='id')

    def create(self, validated_data):
        cluster = check_obj(Cluster, validated_data.get('cluster_id'), "CLUSTER_NOT_FOUND")
        host = check_obj(Host, validated_data.get('id'), "HOST_NOT_FOUND")
        try:
            cm.api.add_host_to_cluster(cluster, host)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e
        return host


class ClusterHostUISerializer(ClusterHostDetailSerializer):
    actions = serializers.SerializerMethodField()
    upgradable = serializers.SerializerMethodField()
    prototype_version = serializers.SerializerMethodField()
    prototype_name = serializers.SerializerMethodField()
    prototype_display_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()
    get_upgradable = get_upgradable_func

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['host_id'] = obj.id
        actions = ClusterHostActionShort(
            filter_actions(obj, act_set), many=True, context=self.context
        )
        return actions.data

    def get_prototype_version(self, obj):
        return obj.prototype.version

    def get_prototype_name(self, obj):
        return obj.prototype.name

    def get_prototype_display_name(self, obj):
        return obj.prototype.display_name

    def get_provider_version(self, obj):
        if obj.provider:
            return obj.provider.prototype.version
        return None

    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.name
        return None


class StatusSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    component_id = serializers.IntegerField(read_only=True)
    service_id = serializers.IntegerField(read_only=True)
    state = serializers.CharField(read_only=True, required=False)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['component'] = instance.component.component.name
        data['component_display_name'] = instance.component.component.display_name
        data['host'] = instance.host.fqdn
        data['service_name'] = instance.service.prototype.name
        data['service_display_name'] = instance.service.prototype.display_name
        data['service_version'] = instance.service.prototype.version
        data['monitoring'] = instance.component.component.monitoring
        status = cm.status_api.get_hc_status(instance.host_id, instance.component_id)
        data['status'] = status
        return data


class HostComponentSerializer(serializers.Serializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {
                'cluster_id': obj.cluster.id,
                'hs_id': obj.id,
            }

    id = serializers.IntegerField(read_only=True)
    host_id = serializers.IntegerField(help_text='host id')
    host = serializers.CharField(read_only=True)
    service_id = serializers.IntegerField()
    component = serializers.CharField(help_text='component name')
    component_id = serializers.IntegerField(read_only=True, help_text='component id')
    state = serializers.CharField(read_only=True, required=False)
    url = MyUrlField(read_only=True, view_name='host-component-details')
    host_url = hlink('host-details', 'host_id', 'host_id')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['component'] = instance.component.prototype.name
        data['component_display_name'] = instance.component.prototype.display_name
        data['host'] = instance.host.fqdn
        data['service_name'] = instance.service.prototype.name
        data['service_display_name'] = instance.service.prototype.display_name
        data['service_version'] = instance.service.prototype.version
        return data


class HostComponentUISerializer(serializers.Serializer):
    hc = HostComponentSerializer(many=True, read_only=True)
    host = serializers.SerializerMethodField()
    component = serializers.SerializerMethodField()

    def get_host(self, obj):
        hosts = Host.objects.filter(cluster=self.context.get('cluster'))
        return ClusterHostSerializer(hosts, many=True, context=self.context).data

    def get_component(self, obj):
        comps = ServiceComponent.objects.filter(cluster=self.context.get('cluster'))
        return HCComponentSerializer(comps, many=True, context=self.context).data


class HostComponentSaveSerializer(serializers.Serializer):
    hc = serializers.JSONField()

    def validate_hc(self, hc):
        if not hc:
            raise AdcmApiEx('INVALID_INPUT', 'hc field is required')
        if not isinstance(hc, list):
            raise AdcmApiEx('INVALID_INPUT', 'hc field should be a list')
        for item in hc:
            for key in ('component_id', 'host_id', 'service_id'):
                if key not in item:
                    msg = '"{}" sub-field is required'
                    raise AdcmApiEx('INVALID_INPUT', msg.format(key))
        return hc

    def create(self, validated_data):
        hc = validated_data.get('hc')
        return safe_api(cm.api.add_hc, (self.context.get('cluster'), hc))


class ClusterServiceUrlField(UrlField):
    def get_kwargs(self, obj):
        return {'cluster_id': obj.cluster.id, 'service_id': obj.id}


class ClusterServiceSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    cluster_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    url = ClusterServiceUrlField(read_only=True, view_name='cluster-service-details')
    prototype_id = serializers.IntegerField(help_text='id of service prototype')

    def validate_prototype_id(self, prototype_id):
        service = check_obj(
            Prototype, {'id': prototype_id, 'type': 'service'}, "PROTOTYPE_NOT_FOUND"
        )
        return service

    def create(self, validated_data):
        try:
            return cm.api.add_service_to_cluster(
                self.context.get('cluster'),
                validated_data.get('prototype_id'),
            )
        except IntegrityError:
            raise AdcmApiEx('SERVICE_CONFLICT') from None
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class ClusterServiceDetailSerializer(ClusterServiceSerializer):
    prototype_id = serializers.IntegerField(read_only=True)
    # stack = serializers.JSONField(read_only=True)
    description = serializers.CharField(read_only=True)
    bundle_id = serializers.IntegerField(read_only=True)
    issue = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    monitoring = serializers.CharField(read_only=True)
    action = ClusterServiceUrlField(read_only=True, view_name='cluster-service-action')
    config = ConfigURL(view_name='config')
    component = ClusterServiceUrlField(read_only=True, view_name='cluster-service-component')
    imports = ClusterServiceUrlField(read_only=True, view_name='cluster-service-import')
    bind = ClusterServiceUrlField(read_only=True, view_name='cluster-service-bind')
    prototype = hlink('service-type-details', 'prototype_id', 'prototype_id')

    def get_issue(self, obj):
        return cm.issue.get_issue(obj)

    def get_status(self, obj):
        return cm.status_api.get_service_status(obj.cluster.id, obj.id)


class ClusterServiceUISerializer(ClusterServiceDetailSerializer):
    actions = serializers.SerializerMethodField()
    components = serializers.SerializerMethodField()
    name = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    action = ClusterServiceUrlField(read_only=True, view_name='cluster-service-action')
    config = ClusterServiceUrlField(read_only=True, view_name='cluster-service-config')

    def get_actions(self, obj):
        act_set = Action.objects.filter(prototype=obj.prototype)
        self.context['object'] = obj
        self.context['service_id'] = obj.id
        actions = filter_actions(obj, act_set)
        acts = ServiceActionShort(actions, many=True, context=self.context)
        return acts.data

    def get_components(self, obj):
        comps = ServiceComponent.objects.filter(service=obj, cluster=obj.cluster)
        return ServiceComponentDetailSerializer(comps, many=True, context=self.context).data


class ServiceComponentSerializer(serializers.Serializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {
                'cluster_id': obj.cluster.id,
                'service_id': obj.service.id,
                'component_id': obj.id,
            }

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    prototype_id = serializers.SerializerMethodField()
    display_name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    url = MyUrlField(read_only=True, view_name='cluster-service-component-details')

    def get_prototype_id(self, obj):
        return obj.prototype.id


class ServiceComponentDetailSerializer(ServiceComponentSerializer):
    constraint = serializers.JSONField(read_only=True)
    requires = serializers.JSONField(read_only=True)
    monitoring = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    config = ConfigURL(view_name='config')

    def get_status(self, obj):
        return cm.status_api.get_component_status(obj.id)


class HCComponentSerializer(ServiceComponentDetailSerializer):
    service_id = serializers.IntegerField(read_only=True)
    service_name = serializers.SerializerMethodField()
    service_display_name = serializers.SerializerMethodField()
    service_state = serializers.SerializerMethodField()
    requires = serializers.SerializerMethodField()

    def get_service_state(self, obj):
        return obj.service.state

    def get_service_name(self, obj):
        return obj.service.prototype.name

    def get_service_display_name(self, obj):
        return obj.service.prototype.display_name

    def get_requires(self, obj):
        if not obj.prototype.requires:
            return None
        comp_list = {}

        def process_requires(req_list):
            for c in req_list:
                comp = Prototype.objects.get(
                    type='component',
                    name=c['component'],
                    parent__name=c['service'],
                    parent__bundle_id=obj.prototype.bundle_id
                )
                if comp == obj.prototype:
                    return
                if comp.name not in comp_list:
                    comp_list[comp.name] = {
                        'components': {}, 'service': comp.parent
                    }
                if comp.name in comp_list[comp.name]['components']:
                    return
                comp_list[comp.parent.name]['components'][comp.name] = comp
                if comp.requires:
                    process_requires(comp.requires)

        # def check_hc(comp):
        #    return HostComponent.objects.filter(cluster=obj.cluster, component__component=comp)

        process_requires(obj.requires)
        out = []
        for service_name in comp_list:
            comp_out = []
            service = comp_list[service_name]['service']
            for comp_name in comp_list[service_name]['components']:
                comp = comp_list[service_name]['components'][comp_name]
                comp_out.append({
                    'prototype_id': comp.id,
                    'name': comp_name,
                    'display_name': comp.display_name,
                })
            if not comp_out:
                continue
            out.append({
                'prototype_id': service.id,
                'name': service_name,
                'display_name': service.display_name,
                'components': comp_out
            })
        return out


class BindSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    export_cluster_id = serializers.IntegerField(read_only=True, source='source_cluster_id')
    export_cluster_name = serializers.CharField(read_only=True, source='source_cluster')
    export_cluster_prototype_name = serializers.SerializerMethodField()
    export_service_id = serializers.SerializerMethodField()
    export_service_name = serializers.SerializerMethodField()
    import_service_id = serializers.SerializerMethodField()
    import_service_name = serializers.SerializerMethodField()

    def get_export_cluster_prototype_name(self, obj):
        return obj.source_cluster.prototype.name

    def get_export_service_name(self, obj):
        if obj.source_service:
            return obj.source_service.prototype.name
        return None

    def get_export_service_id(self, obj):
        if obj.source_service:
            return obj.source_service.id
        return None

    def get_import_service_id(self, obj):
        if obj.service:
            return obj.service.id
        return None

    def get_import_service_name(self, obj):
        if obj.service:
            return obj.service.prototype.name
        return None


class ServiceBindSerializer(BindSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {
                'bind_id': obj.id,
                'cluster_id': obj.cluster.id,
                'service_id': obj.service.id,
            }

    url = MyUrlField(read_only=True, view_name='cluster-service-bind-details')


class ClusterBindSerializer(BindSerializer):
    class MyUrlField(UrlField):
        def get_kwargs(self, obj):
            return {
                'bind_id': obj.id,
                'cluster_id': obj.cluster.id
            }

    url = MyUrlField(read_only=True, view_name='cluster-bind-details')


class DoBindSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    export_cluster_id = serializers.IntegerField()
    export_service_id = serializers.IntegerField(required=False)
    export_cluster_name = serializers.CharField(read_only=True)
    export_cluster_prototype_name = serializers.CharField(read_only=True)

    def create(self, validated_data):
        export_cluster = check_obj(
            Cluster, validated_data.get('export_cluster_id'), "CLUSTER_NOT_FOUND"
        )
        try:
            return cm.api.bind(
                validated_data.get('cluster'),
                None,
                export_cluster,
                validated_data.get('export_service_id', 0)
            )
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class DoServiceBindSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    export_cluster_id = serializers.IntegerField()
    export_service_id = serializers.IntegerField()
    export_cluster_name = serializers.CharField(read_only=True)
    export_service_name = serializers.CharField(read_only=True)
    export_cluster_prototype_name = serializers.CharField(read_only=True)

    def create(self, validated_data):
        export_cluster = check_obj(
            Cluster, validated_data.get('export_cluster_id'), "CLUSTER_NOT_FOUND"
        )
        try:
            return cm.api.bind(
                validated_data.get('cluster'),
                validated_data.get('service'),
                export_cluster,
                validated_data.get('export_service_id')
            )
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code) from e


class PostImportSerializer(serializers.Serializer):
    bind = serializers.JSONField()

    def create(self, validated_data):
        try:
            bind = validated_data.get('bind')
            cluster = self.context.get('cluster')
            service = self.context.get('service')
            return cm.api.multi_bind(cluster, service, bind)
        except AdcmEx as e:
            raise AdcmApiEx(e.code, e.msg, e.http_code, e.adds) from e
