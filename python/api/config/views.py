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

from rest_framework import status, permissions
from rest_framework.response import Response

from api.api_views import ListView, GenericAPIPermView, create, update, check_obj

from cm.adcm_config import ui_config
from cm.models import get_model_by_type, ConfigLog, ObjectConfig

from . import serializers


def get_config_version(objconf, version):
    if version == 'previous':
        ver = objconf.previous
    elif version == 'current':
        ver = objconf.current
    else:
        ver = version
    cl = ConfigLog.obj.get(obj_ref=objconf, id=ver)
    return cl


def type_to_model(object_type):
    if object_type == 'provider':
        object_type = 'hostprovider'
    if object_type == 'service':
        object_type = 'clusterobject'
    if object_type == 'component':
        object_type = 'servicecomponent'
    return object_type


def get_obj(object_type, object_id):
    model = get_model_by_type(object_type)
    obj = model.obj.get(id=object_id)
    oc = check_obj(ObjectConfig, {type_to_model(object_type): obj}, 'CONFIG_NOT_FOUND')
    cl = ConfigLog.obj.get(obj_ref=oc, id=oc.current)
    return obj, oc, cl


def get_object_type_id_version(**kwargs):
    object_type = kwargs.get('object_type')
    object_id = kwargs.get(f'{object_type}_id')
    version = kwargs.get('version')
    return object_type, object_id, version


def get_queryset(self):
    return get_model_by_type(self.object_type).objects.all()


def has_config_perm(user, action_type, object_type, obj):
    model = type_to_model(object_type)
    if user.has_perm(f'cm.{action_type}_configlog'):
        return True
    if user.has_perm(f'cm.{action_type}_config_of_{model}', obj):
        return True
    return False


def check_config_perm(self, action_type, object_type, obj):
    if not has_config_perm(self.request.user, action_type, object_type, obj):
        self.permission_denied(
            self.request,
            message='You do not have permission to perform this action',
            code=status.HTTP_403_FORBIDDEN,
        )


class ConfigView(ListView):
    serializer_class = serializers.HistoryCurrentPreviousConfigSerializer
    permission_classes = (permissions.IsAuthenticated,)
    check_config_perm = check_config_perm
    get_queryset = get_queryset
    object_type = None

    def get(self, request, *args, **kwargs):
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, _, _ = get_obj(object_type, object_id)
        self.check_config_perm('view', object_type, obj)
        serializer = self.serializer_class(
            self.get_queryset().get(id=obj.id), context={'request': request, 'object': obj}
        )
        return Response(serializer.data)


class ConfigHistoryView(ListView):
    serializer_class = serializers.ConfigHistorySerializer
    update_serializer = serializers.ObjectConfigUpdateSerializer
    permission_classes = (permissions.IsAuthenticated,)
    check_config_perm = check_config_perm
    get_queryset = get_queryset
    object_type = None

    def get(self, request, *args, **kwargs):
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, _, _ = get_obj(object_type, object_id)
        self.check_config_perm('view', object_type, obj)
        cl = ConfigLog.objects.filter(obj_ref=obj.config).order_by('-id')
        serializer = self.serializer_class(
            cl, many=True, context={'request': request, 'object': obj}
        )
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, _, cl = get_obj(object_type, object_id)
        self.check_config_perm('change', object_type, obj)
        serializer = self.update_serializer(
            cl, data=request.data, context={'request': request, 'object': obj}
        )
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class ConfigVersionView(ListView):
    serializer_class = serializers.ObjectConfigSerializer
    permission_classes = (permissions.IsAuthenticated,)
    check_config_perm = check_config_perm
    get_queryset = get_queryset
    object_type = None

    def get(self, request, *args, **kwargs):
        object_type, object_id, version = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, oc, _ = get_obj(object_type, object_id)
        self.check_config_perm('view', object_type, obj)
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = ui_config(obj, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class ConfigHistoryRestoreView(GenericAPIPermView):
    serializer_class = serializers.ObjectConfigRestoreSerializer
    permission_classes = (permissions.IsAuthenticated,)
    check_config_perm = check_config_perm
    get_queryset = get_queryset
    object_type = None

    def patch(self, request, *args, **kwargs):
        object_type, object_id, version = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, oc, _ = get_obj(object_type, object_id)
        self.check_config_perm('change', object_type, obj)
        cl = get_config_version(oc, version)
        serializer = self.serializer_class(cl, data=request.data, context={'request': request})
        return update(serializer)
