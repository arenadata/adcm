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

from api.api_views import ListView, GenericAPIPermView, create, update
from api.serializers import check_obj, get_config_version
from cm.adcm_config import ui_config
from cm.errors import AdcmApiEx
from cm.models import ADCM, Cluster, HostProvider, Host, ClusterObject, ConfigLog, ObjectConfig
from . import serializers


def get_objects_for_config(object_type):
    if object_type == 'adcm':
        return ADCM.objects.all()
    if object_type == 'cluster':
        return Cluster.objects.all()
    elif object_type == 'provider':
        return HostProvider.objects.all()
    elif object_type == 'service':
        return ClusterObject.objects.all()
    elif object_type == 'host':
        return Host.objects.all()
    else:
        # This function should return a QuerySet, this is necessary for the correct
        # construction of the schema.
        return Cluster.objects.all()


def get_obj(objects, object_type, object_id):
    try:
        obj = objects.get(id=object_id)
    except models.ObjectDoesNotExist:
        errors = {
            'adcm': 'ADCM_NOT_FOUND',
            'cluster': 'CLUSTER_NOT_FOUND',
            'provider': 'PROVIDER_NOT_FOUND',
            'host': 'HOST_NOT_FOUND',
            'service': 'SERVICE_NOT_FOUND',
        }
        raise AdcmApiEx(errors[object_type]) from None

    if object_type == 'provider':
        object_type = 'hostprovider'
    if object_type == 'service':
        object_type = 'clusterobject'
    oc = check_obj(ObjectConfig, {object_type: obj}, 'CONFIG_NOT_FOUND')
    cl = ConfigLog.objects.get(obj_ref=oc, id=oc.current)
    return obj, oc, cl


def get_object_type_id_version(**kwargs):
    object_type = kwargs.get('object_type')
    object_id = kwargs.get(f'{object_type}_id')
    version = kwargs.get('version')
    return object_type, object_id, version


class ConfigView(ListView):
    serializer_class = serializers.HistoryCurrentPreviousConfigSerializer
    object_type = None

    def get_queryset(self):
        return get_objects_for_config(self.object_type)

    def get(self, request, *args, **kwargs):
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, _, _ = get_obj(self.get_queryset(), object_type, object_id)
        serializer = self.serializer_class(
            self.get_queryset().get(id=obj.id), context={'request': request})
        return Response(serializer.data)


class ConfigHistoryView(ListView):
    serializer_class = serializers.ConfigHistorySerializer
    update_serializer = serializers.ObjectConfigUpdateSerializer
    object_type = None

    def get_queryset(self):
        return get_objects_for_config(self.object_type)

    def get(self, request, *args, **kwargs):
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, _, _ = get_obj(self.get_queryset(), object_type, object_id)
        cl = ConfigLog.objects.filter(obj_ref=obj.config).order_by('-id')
        # Variables object_type and object_id are needed to correctly build the hyperlink
        # in the serializer
        for c in cl:
            c.object_type = object_type
            c.object_id = object_id

        serializer = self.serializer_class(cl, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        object_type, object_id, _ = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, _, cl = get_obj(self.get_queryset(), object_type, object_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class ConfigVersionView(ListView):
    serializer_class = serializers.ObjectConfigSerializer
    object_type = None

    def get_queryset(self):
        return get_objects_for_config(self.object_type)

    def get(self, request, *args, **kwargs):
        object_type, object_id, version = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        obj, oc, _ = get_obj(self.get_queryset(), object_type, object_id)
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = ui_config(obj, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class ConfigHistoryRestoreView(GenericAPIPermView):
    serializer_class = serializers.ObjectConfigRestoreSerializer
    object_type = None

    def get_queryset(self):
        return get_objects_for_config(self.object_type)

    def patch(self, request, *args, **kwargs):
        object_type, object_id, version = get_object_type_id_version(**kwargs)
        self.object_type = object_type
        _, oc, _ = get_obj(self.get_queryset(), object_type, object_id)
        cl = get_config_version(oc, version)
        serializer = self.serializer_class(cl, data=request.data, context={'request': request})
        return update(serializer)
