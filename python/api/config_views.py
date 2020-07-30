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

# pylint: disable=arguments-differ

from rest_framework.response import Response

import api.cluster_serial
import cm.adcm_config
from api.api_views import ListView
from api.api_views import create, update, GenericAPIPermView
from api.cluster_views import get_obj_conf
from api.serializers import check_obj, get_config_version
from cm.errors import AdcmApiEx, AdcmEx
from cm.models import Cluster, Host
from cm.models import ClusterObject, ConfigLog
from cm.models import HostProvider, ADCM, ObjectConfig


class AdcmConfig(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.AdcmConfigSerializer

    def get(self, request, adcm_id):
        """
        Show current config for a adcm object
        """
        check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        obj = ObjectConfig()
        serializer = self.serializer_class(
            obj, context={'request': request, 'adcm_id': adcm_id}
        )
        return Response(serializer.data)


class AdcmConfigHistory(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.AdcmConfigHistorySerializer
    update_serializer = api.cluster_serial.ObjectConfigUpdate

    def get_obj(self, adcm_id):
        adcm = check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'adcm': adcm}, 'CONFIG_NOT_FOUND')
        return adcm, oc, self.get_queryset().get(obj_ref=oc, id=oc.current)

    def get(self, request, adcm_id):
        """
        Show history of config of an adcm object
        """
        _, oc, _ = self.get_obj(adcm_id)
        obj = self.get_queryset().filter(obj_ref=oc).order_by('-id')
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, adcm_id):
        """
        Update host provider config. Config parameter is json
        """
        obj, _, cl = self.get_obj(adcm_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)

    def patch(self, request, adcm_id):
        """
        Update host provider config. Config parameter is json
        """
        obj, _, cl = self.get_obj(adcm_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class AdcmConfigVersion(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfig

    def get(self, request, adcm_id, version):
        """
        Show config for a specified version of adcm object.

        """
        adcm = check_obj(ADCM, adcm_id, 'ADCM_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'adcm': adcm}, 'CONFIG_NOT_FOUND')
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = cm.adcm_config.ui_config(adcm, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class ClusterServiceConfig(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ClusterServiceConfigSerializer

    def get(self, request, cluster_id, service_id):
        """
        Show config page for a specified service and cluster
        """
        check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        if service_id:
            check_obj(ClusterObject, service_id, 'SERVICE_NOT_FOUND')
        obj = ClusterObject()
        serializer = self.serializer_class(
            obj, context={'request': request, 'cluster_id': cluster_id, 'service_id': service_id}
        )
        return Response(serializer.data)


class ClusterConfig(ClusterServiceConfig):
    """
    get:
    Show config page for a specified cluster
    """
    serializer_class = api.cluster_serial.ClusterConfigSerializer


class ClusterServiceConfigVersion(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfig

    def get(self, request, cluster_id, service_id, version):
        """
        Show config for a specified version, service and cluster.

        """
        obj = get_obj_conf(cluster_id, service_id)
        cl = get_config_version(obj.config, version)
        if self.for_ui(request):
            try:
                cl.config = cm.adcm_config.ui_config(obj, cl)
            except AdcmEx as e:
                raise AdcmApiEx(e.code, e.msg, e.http_code)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class ClusterConfigVersion(ClusterServiceConfigVersion):
    """
    get:
    Show config for a specified version and cluster.
    """


class ClusterConfigRestore(GenericAPIPermView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfigRestore

    def patch(self, request, cluster_id, service_id, version):
        """
        Restore config of specified version in a specified service and cluster.
        """
        obj = get_obj_conf(cluster_id, service_id)
        try:
            cl = self.get_queryset().get(obj_ref=obj.config, id=version)
        except ConfigLog.DoesNotExist:
            raise AdcmApiEx('CONFIG_NOT_FOUND', "config version doesn't exist")
        serializer = self.serializer_class(cl, data=request.data, context={'request': request})
        return update(serializer)


class ClusterConfigHistory(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ClusterConfigHistorySerializer
    update_serializer = api.cluster_serial.ObjectConfigUpdate

    def get_obj(self, cluster_id, service_id):
        obj = get_obj_conf(cluster_id, service_id)
        return obj, self.get_queryset().get(obj_ref=obj.config, id=obj.config.current)

    def get(self, request, cluster_id, service_id):
        """
        Show history of config in a specified service and cluster
        """
        obj = get_obj_conf(cluster_id, service_id)
        cl = self.get_queryset().filter(obj_ref=obj.config).order_by('-id')
        serializer = self.serializer_class(cl, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, cluster_id, service_id):
        """
        Update config in a specified service and cluster. Config parameter is json
        """
        obj, cl = self.get_obj(cluster_id, service_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)

    def patch(self, request, cluster_id, service_id):
        """
        Update config in a specified service and cluster. Config parameter is json
        """
        obj, cl = self.get_obj(cluster_id, service_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class ClusterServiceConfigHistory(ClusterConfigHistory):
    serializer_class = api.cluster_serial.ClusterServiceConfigHistorySerializer
    """
    get:
    Show history of config in a specified service and cluster
    """


class ProviderConfig(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ProviderConfigSerializer

    def get(self, request, provider_id):
        """
        Show current config for a specified host provider
        """
        check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = ObjectConfig()
        serializer = self.serializer_class(
            obj, context={'request': request, 'provider_id': provider_id}
        )
        return Response(serializer.data)


class ProviderConfigHistory(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ProviderConfigHistorySerializer
    update_serializer = api.cluster_serial.ObjectConfigUpdate

    def get_obj(self, provider_id):
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'hostprovider': provider}, 'CONFIG_NOT_FOUND')
        return provider, cc, self.get_queryset().get(obj_ref=cc, id=cc.current)

    def get(self, request, provider_id):
        """
        Show history of config of a specified host provider
        """
        _, cc, _ = self.get_obj(provider_id)
        obj = self.get_queryset().filter(obj_ref=cc).order_by('-id')
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, provider_id):
        """
        Update host provider config. Config parameter is json
        """
        obj, _, cl = self.get_obj(provider_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)

    def patch(self, request, provider_id):
        """
        Update host provider config. Config parameter is json
        """
        obj, _, cl = self.get_obj(provider_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class ProviderConfigVersion(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfig

    def get(self, request, provider_id, version):
        """
        Show config for a specified version and host provider.

        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'hostprovider': provider}, 'CONFIG_NOT_FOUND')
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = cm.adcm_config.ui_config(provider, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class ProviderConfigRestore(GenericAPIPermView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfigRestore

    def patch(self, request, provider_id, version):
        """
        Restore config of specified version of a specified host provider.
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'hostprovider': provider}, 'CONFIG_NOT_FOUND')
        try:
            obj = self.get_queryset().get(obj_ref=cc, id=version)
        except ConfigLog.DoesNotExist:
            raise AdcmApiEx('CONFIG_NOT_FOUND', "config version doesn't exist")
        serializer = self.serializer_class(obj, data=request.data, context={'request': request})
        return update(serializer)


class HostConfig(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.HostConfigSerializer

    def get(self, request, host_id):
        """
        Show current config for a specified host
        """
        check_obj(Host, host_id, 'HOST_NOT_FOUND')
        obj = ObjectConfig()
        serializer = self.serializer_class(obj, context={'request': request, 'host_id': host_id})
        return Response(serializer.data)


class HostConfigHistory(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.HostConfigHistorySerializer
    update_serializer = api.cluster_serial.ObjectConfigUpdate

    def get_obj(self, host_id):
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        return host, self.get_queryset().get(obj_ref=cc, id=cc.current)

    def get(self, request, host_id):
        """
        Show history of config of a specified host
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        obj = self.get_queryset().filter(obj_ref=cc).order_by('-id')
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, host_id):
        """
        Update config of a specified host. Config parameter is json
        """
        obj, cl = self.get_obj(host_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)

    def patch(self, request, host_id):
        """
        Update config of a specified host. Config parameter is json
        """
        obj, cl = self.get_obj(host_id)
        serializer = self.update_serializer(cl, data=request.data, context={'request': request})
        return create(serializer, ui=bool(self.for_ui(request)), obj=obj)


class HostConfigVersion(ListView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfig

    def get(self, request, host_id, version):
        """
        Show config for a specified version and host.

        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        oc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        cl = get_config_version(oc, version)
        if self.for_ui(request):
            cl.config = cm.adcm_config.ui_config(host, cl)
        serializer = self.serializer_class(cl, context={'request': request})
        return Response(serializer.data)


class HostConfigRestore(GenericAPIPermView):
    queryset = ConfigLog.objects.all()
    serializer_class = api.cluster_serial.ObjectConfigRestore

    def patch(self, request, host_id, version):
        """
        Restore config of specified version of a specified host.
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        cc = check_obj(ObjectConfig, {'host': host}, 'CONFIG_NOT_FOUND')
        try:
            obj = self.get_queryset().get(obj_ref=cc, id=version)
        except ConfigLog.DoesNotExist:
            raise AdcmApiEx('CONFIG_NOT_FOUND', "config version doesn't exist")
        serializer = self.serializer_class(obj, data=request.data, context={'request': request})
        return update(serializer)
