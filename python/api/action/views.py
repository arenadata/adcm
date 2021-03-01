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

from django.db import models
from rest_framework.response import Response

from api.api_views import (
    ListView, GenericAPIPermView, ActionFilter, create, check_obj, filter_actions
)
from api.job_serial import RunTaskSerializer
from cm.errors import AdcmApiEx
from cm.models import (
    ADCM, Cluster, HostProvider, Host, ClusterObject, ServiceComponent, Action, TaskLog,
    HostComponent
)
from . import serializers


def get_action_objects(object_type):
    if object_type == 'adcm':
        return ADCM.objects.all()
    if object_type == 'cluster':
        return Cluster.objects.all()
    elif object_type == 'provider':
        return HostProvider.objects.all()
    elif object_type == 'service':
        return ClusterObject.objects.all()
    elif object_type == 'component':
        return ServiceComponent.objects.all()
    elif object_type == 'host':
        return Host.objects.all()
    else:
        # This function should return a QuerySet, this is necessary for the correct
        # construction of the schema.
        return Cluster.objects.all()


def get_object_type_id(**kwargs):
    object_type = kwargs.get('object_type')
    object_id = kwargs.get(f'{object_type}_id')
    action_id = kwargs.get('action_id', None)
    return object_type, object_id, action_id


def get_obj(**kwargs):
    object_type, object_id, action_id = get_object_type_id(**kwargs)
    objects = get_action_objects(object_type)
    try:
        obj = objects.get(id=object_id)
    except models.ObjectDoesNotExist:
        errors = {
            'adcm': 'ADCM_NOT_FOUND',
            'cluster': 'CLUSTER_NOT_FOUND',
            'provider': 'PROVIDER_NOT_FOUND',
            'host': 'HOST_NOT_FOUND',
            'service': 'SERVICE_NOT_FOUND',
            'component': 'COMPONENT_NOT_FOUND',
        }
        raise AdcmApiEx(errors[object_type]) from None
    return obj, action_id


def get_selector(obj, action):
    selector = {obj.prototype.type: obj.id}
    if obj.prototype.type == 'service':
        selector['cluster'] = obj.cluster.id
    if obj.prototype.type == 'component':
        selector['cluster'] = obj.cluster.id
        selector['component'] = obj.service.id
    if isinstance(obj, Host) and action.host_action:
        try:
            hc = HostComponent.objects.get(host_id=obj.id)
            selector.update(
                {f'{action.prototype.type}': getattr(hc, f'{action.prototype.type}_id')})
            selector['cluster'] = hc.cluster_id
        except HostComponent.DoesNotExist:
            if obj.cluster is not None:
                selector['cluster'] = obj.cluster.id

    return selector


class ActionList(ListView):
    queryset = Action.objects.all()
    serializer_class = serializers.ActionSerializer
    serializer_class_ui = serializers.ActionDetailSerializer
    filterset_class = ActionFilter
    filterset_fields = ('name', 'button', 'button_is_null')

    def get(self, request, *args, **kwargs):
        """
        List all actions of a specified object
        """
        if kwargs['object_type'] == 'host':
            host, _ = get_obj(object_type='host', host_id=kwargs['host_id'])
            actions = filter_actions(host, self.filter_queryset(
                self.get_queryset().filter(prototype=host.prototype)
            ))
            objects = {'host': host}
            try:
                hc = HostComponent.objects.get(host_id=kwargs['host_id'])
                cluster, _ = get_obj(object_type='cluster', cluster_id=hc.cluster_id)
                service, _ = get_obj(object_type='service', service_id=hc.service_id)
                component, _ = get_obj(object_type='component', component_id=hc.component_id)
                for obj in [cluster, service, component]:
                    actions.extend(filter_actions(obj, self.filter_queryset(
                        self.get_queryset().filter(prototype=obj.prototype, host_action=True))))

                objects.update({'cluster': cluster, 'service': service, 'component': component})
            except HostComponent.DoesNotExist:
                if host.cluster is not None:
                    actions.extend(filter_actions(host.cluster, self.filter_queryset(
                        self.get_queryset().filter(
                            prototype=host.cluster.prototype, host_action=True))))
                    objects.update({'cluster': host.cluster})
        else:
            obj, _ = get_obj(**kwargs)
            actions = filter_actions(obj, self.filter_queryset(
                self.get_queryset().filter(prototype=obj.prototype, host_action=False)
            ))
            objects = {obj.prototype.type: obj}
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            actions, many=True, context={'request': request, 'objects': objects}
        )
        return Response(serializer.data)


class ActionDetail(GenericAPIPermView):
    queryset = Action.objects.all()
    serializer_class = serializers.ActionDetailSerializer

    def get(self, request, *args, **kwargs):
        """
        Show specified action
        """
        obj, action_id = get_obj(**kwargs)
        action = check_obj(Action, {'id': action_id}, 'ACTION_NOT_FOUND')
        objects = {action.prototype.type: obj}
        serializer = self.serializer_class(action, context={'request': request, 'objects': objects})
        return Response(serializer.data)


class RunTask(GenericAPIPermView):
    queryset = TaskLog.objects.all()
    serializer_class = RunTaskSerializer

    def post(self, request, *args, **kwargs):
        """
        Ran specified action
        """
        obj, action_id = get_obj(**kwargs)
        action = check_obj(Action, {'id': action_id}, 'ACTION_NOT_FOUND')
        selector = get_selector(obj, action)
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, action_id=action.id, selector=selector)
