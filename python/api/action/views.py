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

from rest_framework.response import Response

from api.api_views import (
    ListView,
    DetailViewRO,
    GenericAPIPermView,
    ActionFilter,
    create,
    check_obj,
    filter_actions,
)
from api.job.serializers import RunTaskSerializer
from cm.models import (
    Host,
    ClusterObject,
    ServiceComponent,
    Action,
    TaskLog,
    HostComponent,
    get_model_by_type,
)
from . import serializers


def get_object_type_id(**kwargs):
    object_type = kwargs.get('object_type')
    object_id = kwargs.get(f'{object_type}_id')
    action_id = kwargs.get('action_id', None)
    return object_type, object_id, action_id


def get_obj(**kwargs):
    object_type, object_id, action_id = get_object_type_id(**kwargs)
    model = get_model_by_type(object_type)
    obj = model.obj.get(id=object_id)
    return obj, action_id


def get_selector(obj, action):
    selector = {obj.prototype.type: obj.id}
    if obj.prototype.type == 'service':
        selector['cluster'] = obj.cluster.id
    if obj.prototype.type == 'component':
        selector['cluster'] = obj.cluster.id
        selector['service'] = obj.service.id
    if isinstance(obj, Host) and action.host_action:
        if action.prototype.type == 'component':
            component = ServiceComponent.obj.get(prototype=action.prototype)
            selector['component'] = component.id
        if action.prototype.type == 'service':
            service = ClusterObject.obj.get(prototype=action.prototype)
            selector['service'] = service.id
        if obj.cluster is not None:
            selector['cluster'] = obj.cluster.id
    return selector


class ActionList(ListView):
    queryset = Action.objects.all()
    serializer_class = serializers.ActionSerializer
    serializer_class_ui = serializers.ActionUISerializer
    filterset_class = ActionFilter
    filterset_fields = ('name', 'button', 'button_is_null')

    def get(self, request, *args, **kwargs):  # pylint: disable=too-many-locals
        """
        List all actions of a specified object
        """
        if kwargs['object_type'] == 'host':
            host, _ = get_obj(object_type='host', host_id=kwargs['host_id'])
            actions = set(
                filter_actions(
                    host, self.filter_queryset(self.get_queryset().filter(prototype=host.prototype))
                )
            )
            obj = host
            objects = {'host': host}
            hcs = HostComponent.objects.filter(host_id=kwargs['host_id'])
            if hcs:
                for hc in hcs:
                    cluster, _ = get_obj(object_type='cluster', cluster_id=hc.cluster_id)
                    service, _ = get_obj(object_type='service', service_id=hc.service_id)
                    component, _ = get_obj(object_type='component', component_id=hc.component_id)
                    for obj in [cluster, service, component]:
                        actions.update(
                            filter_actions(
                                obj,
                                self.filter_queryset(
                                    self.get_queryset().filter(
                                        prototype=obj.prototype, host_action=True
                                    )
                                ),
                            )
                        )
            else:
                if host.cluster is not None:
                    actions.update(
                        filter_actions(
                            host.cluster,
                            self.filter_queryset(
                                self.get_queryset().filter(
                                    prototype=host.cluster.prototype, host_action=True
                                )
                            ),
                        )
                    )
        else:
            obj, _ = get_obj(**kwargs)
            actions = filter_actions(
                obj,
                self.filter_queryset(
                    self.get_queryset().filter(prototype=obj.prototype, host_action=False)
                ),
            )
            objects = {obj.prototype.type: obj}
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            actions, many=True, context={'request': request, 'objects': objects, 'obj': obj}
        )
        return Response(serializer.data)


class ActionDetail(DetailViewRO):
    queryset = Action.objects.all()
    serializer_class = serializers.ActionDetailSerializer
    serializer_class_ui = serializers.ActionUISerializer

    def get(self, request, *args, **kwargs):
        """
        Show specified action
        """
        obj, action_id = get_obj(**kwargs)
        action = check_obj(Action, {'id': action_id}, 'ACTION_NOT_FOUND')
        if isinstance(obj, Host) and action.host_action:
            objects = {'host': obj}
        else:
            objects = {action.prototype.type: obj}
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            action, context={'request': request, 'objects': objects, 'obj': obj}
        )
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
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, action=action, task_object=obj)
