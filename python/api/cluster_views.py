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

from itertools import chain

from rest_framework import status
from rest_framework.response import Response

import cm.job
import cm.api
import cm.bundle
import cm.status_api
from cm.errors import AdcmEx
from cm.models import Cluster, Host, HostComponent, Prototype
from cm.models import ClusterObject, Upgrade, ClusterBind
from cm.logger import log   # pylint: disable=unused-import

import api.serializers
import api.cluster_serial
import api.stack_serial
from api.api_views import create, update, check_obj, GenericAPIPermView
from api.api_views import ListView, PageView, PageViewAdd, InterfaceView
from api.api_views import DetailViewRO, DetailViewDelete


def get_obj_conf(cluster_id, service_id):
    cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
    if service_id:
        co = check_obj(ClusterObject, {'cluster': cluster, 'id': service_id})
        obj = co
    else:
        obj = cluster
    if not obj:
        raise AdcmEx('CONFIG_NOT_FOUND', "this object has no config")
    if not obj.config:
        raise AdcmEx('CONFIG_NOT_FOUND', "this object has no config")
    return obj


class ClusterList(PageViewAdd):
    """
    get:
    List of all existing clusters

    post:
    Create new cluster
    """
    queryset = Cluster.objects.all()
    serializer_class = api.cluster_serial.ClusterSerializer
    serializer_class_ui = api.cluster_serial.ClusterUISerializer
    serializer_class_post = api.cluster_serial.ClusterDetailSerializer
    filterset_fields = ('name', 'prototype_id')
    ordering_fields = ('name', 'state', 'prototype__display_name', 'prototype__version_order')


class ClusterDetail(DetailViewDelete):
    """
    get:
    Show cluster
    """
    queryset = Cluster.objects.all()
    serializer_class = api.cluster_serial.ClusterDetailSerializer
    serializer_class_ui = api.cluster_serial.ClusterUISerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'cluster_id'
    error_code = 'CLUSTER_NOT_FOUND'

    def patch(self, request, *args, **kwargs):
        """
        Edit cluster
        """
        obj = self.get_object()
        serializer = self.serializer_class(
            obj, data=request.data, partial=True, context={'request': request}
        )
        return update(serializer)

    def delete(self, request, *args, **kwargs):
        """
        Remove cluster
        """
        cluster = self.get_object()
        cm.api.delete_cluster(cluster)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterHostList(PageView):
    queryset = Host.objects.all()
    serializer_class = api.cluster_serial.ClusterHostSerializer
    post_serializer = api.cluster_serial.ClusterHostAddSerializer
    serializer_class_ui = api.cluster_serial.ClusterHostUISerializer
    filterset_fields = ('fqdn', 'prototype_id', 'provider_id')
    ordering_fields = (
        'fqdn', 'state', 'provider__name', 'prototype__display_name', 'prototype__version_order'
    )

    def get(self, request, cluster_id):   # pylint: disable=arguments-differ
        """
        List all hosts of a specified cluster
        """
        cluster = Cluster.obj.get(id=cluster_id)
        obj = self.filter_queryset(self.get_queryset().filter(cluster=cluster))
        return self.get_page(obj, request, {'cluster_id': cluster_id})

    def post(self, request, cluster_id):
        check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        serializer = self.post_serializer(data=request.data, context={'request': request})
        return create(serializer, cluster_id=cluster_id)


class ClusterHostDetail(ListView):
    queryset = Host.objects.all()
    serializer_class = api.cluster_serial.ClusterHostDetailSerializer
    serializer_class_ui = api.cluster_serial.ClusterHostUISerializer

    def check_host(self, cluster, host):
        if host.cluster != cluster:
            msg = "Host #{} doesn't belong to cluster #{}".format(host.id, cluster.id)
            raise AdcmEx('FOREIGN_HOST', msg)

    def get_obj(self, cluster_id, host_id):
        cluster = Cluster.obj.get(id=cluster_id)
        host = Host.obj.get(id=host_id)
        self.check_host(cluster, host)
        return host

    def get(self, request, cluster_id, host_id):   # pylint: disable=arguments-differ
        """
        Show host of cluster
        """
        obj = self.get_obj(cluster_id, host_id)
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(obj, context={'request': request, 'cluster_id': cluster_id})
        return Response(serializer.data)

    def delete(self, request, cluster_id, host_id):
        """
        Remove host from cluster
        """
        host = self.get_obj(cluster_id, host_id)
        cm.api.remove_host_from_cluster(host)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterBundle(ListView):
    queryset = Prototype.objects.filter(type='service')
    serializer_class = api.stack_serial.ServiceSerializer
    serializer_class_ui = api.stack_serial.BundleServiceUISerializer

    def get(self, request, cluster_id):   # pylint: disable=arguments-differ
        """
        List all services of specified cluster of bundle
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        bundle = self.get_queryset().filter(bundle=cluster.prototype.bundle)
        shared = self.get_queryset().filter(shared=True).exclude(bundle=cluster.prototype.bundle)
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            list(chain(bundle, shared)), many=True, context={'request': request, 'cluster': cluster}
        )
        return Response(serializer.data)


class ClusterImport(ListView):
    queryset = Prototype.objects.all()
    serializer_class = api.stack_serial.ImportSerializer
    post_serializer = api.cluster_serial.PostImportSerializer

    def get(self, request, cluster_id):   # pylint: disable=arguments-differ
        """
        List all imports avaliable for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        res = cm.api.get_import(cluster)
        return Response(res)

    def post(self, request, cluster_id):   # pylint: disable=arguments-differ
        """
        Update bind for cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        serializer = self.post_serializer(data=request.data, context={
            'request': request, 'cluster': cluster
        })
        if serializer.is_valid():
            res = serializer.create(serializer.validated_data)
            return Response(res, status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClusterServiceImport(ListView):
    queryset = Prototype.objects.all()
    serializer_class = api.stack_serial.ImportSerializer
    post_serializer = api.cluster_serial.PostImportSerializer

    def get(self, request, cluster_id, service_id):   # pylint: disable=arguments-differ
        """
        List all imports avaliable for specified service in cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        service = check_obj(
            ClusterObject, {'cluster': cluster, 'id': service_id}, 'SERVICE_NOT_FOUND'
        )
        res = cm.api.get_import(cluster, service)
        return Response(res)

    def post(self, request, cluster_id, service_id):   # pylint: disable=arguments-differ
        """
        Update bind for service in cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        service = check_obj(
            ClusterObject, {'cluster': cluster, 'id': service_id}, 'SERVICE_NOT_FOUND'
        )
        serializer = self.post_serializer(data=request.data, context={
            'request': request, 'cluster': cluster, 'service': service
        })
        if serializer.is_valid():
            res = serializer.create(serializer.validated_data)
            return Response(res, status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClusterBindList(ListView):
    queryset = ClusterBind.objects.all()
    serializer_class = api.cluster_serial.ClusterBindSerializer

    def get_serializer_class(self):
        if self.request and self.request.method == 'POST':
            return api.cluster_serial.DoBindSerializer
        else:
            return api.cluster_serial.ClusterBindSerializer

    def get(self, request, cluster_id):   # pylint: disable=arguments-differ
        """
        List all binds of specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        obj = self.get_queryset().filter(cluster=cluster, service=None)
        serializer = self.get_serializer_class()(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, cluster_id):
        """
        Bind two clusters
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        return create(serializer, cluster=cluster)


class ClusterServiceBind(ListView):
    queryset = ClusterBind.objects.all()
    serializer_class = api.cluster_serial.ServiceBindSerializer

    def get_serializer_class(self):
        if self.request and self.request.method == 'POST':
            return api.cluster_serial.DoServiceBindSerializer
        else:
            return api.cluster_serial.ServiceBindSerializer

    def get(self, request, cluster_id, service_id):   # pylint: disable=arguments-differ
        """
        List all binds of specified service in cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        service = check_obj(
            ClusterObject, {'cluster': cluster, 'id': service_id}, 'SERVICE_NOT_FOUND'
        )
        obj = self.get_queryset().filter(cluster=cluster, service=service)
        serializer = self.get_serializer_class()(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, cluster_id, service_id):
        """
        Bind two services
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        service = check_obj(
            ClusterObject, {'cluster': cluster, 'id': service_id}, 'SERVICE_NOT_FOUND'
        )
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        return create(serializer, cluster=cluster, service=service)


class ClusterServiceBindDetail(DetailViewDelete):
    queryset = ClusterBind.objects.all()
    serializer_class = api.cluster_serial.BindSerializer

    def get_obj(self, cluster_id, service_id, bind_id):
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        if service_id:
            check_obj(
                ClusterObject, {'cluster': cluster, 'id': service_id}, 'SERVICE_NOT_FOUND'
            )
        return check_obj(ClusterBind, {'cluster': cluster, 'id': bind_id}, 'BIND_NOT_FOUND')

    def get(self, request, cluster_id, bind_id, service_id=None):   # pylint: disable=arguments-differ
        """
        Show specified bind of specified service in cluster
        """
        obj = self.get_obj(cluster_id, service_id, bind_id)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, cluster_id, bind_id, service_id=None):   # pylint: disable=arguments-differ
        """
        Unbind specified bind of specified service in cluster
        """
        bind = self.get_obj(cluster_id, service_id, bind_id)
        cm.api.unbind(bind)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterUpgrade(PageView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeLinkSerializer

    def get(self, request, cluster_id):   # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        obj = cm.upgrade.get_upgrade(cluster, self.get_ordering(request, self.queryset, self))
        serializer = self.serializer_class(obj, many=True, context={
            'cluster_id': cluster.id, 'request': request
        })
        return Response(serializer.data)


class ClusterUpgradeDetail(ListView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeLinkSerializer

    def get(self, request, cluster_id, upgrade_id):   # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        obj = self.get_queryset().get(id=upgrade_id)
        serializer = self.serializer_class(obj, context={
            'cluster_id': cluster.id, 'request': request
        })
        return Response(serializer.data)


class DoClusterUpgrade(GenericAPIPermView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.DoUpgradeSerializer

    def post(self, request, cluster_id, upgrade_id):
        """
        Do upgrade specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, upgrade_id=int(upgrade_id), obj=cluster)


class ClusterServiceList(PageView):
    queryset = ClusterObject.objects.all()
    serializer_class = api.cluster_serial.ClusterServiceSerializer
    serializer_class_ui = api.cluster_serial.ClusterServiceUISerializer
    ordering_fields = ('state', 'prototype__display_name', 'prototype__version_order')

    def get(self, request, cluster_id):   # pylint: disable=arguments-differ
        """
        List all services of a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        obj = self.filter_queryset(self.get_queryset().filter(cluster=cluster))
        return self.get_page(obj, request, {'cluster_id': cluster_id})

    def post(self, request, cluster_id):
        """
        Add service to specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        serializer = self.serializer_class(data=request.data, context={
            'request': request, 'cluster': cluster,
        })
        return create(serializer, id=cluster_id)


class ClusterServiceDetail(DetailViewRO):
    queryset = ClusterObject.objects.all()
    serializer_class = api.cluster_serial.ClusterServiceDetailSerializer
    serializer_class_ui = api.cluster_serial.ClusterServiceUISerializer

    def get(self, request, cluster_id, service_id):   # pylint: disable=arguments-differ
        """
        Show service in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        service = check_obj(
            ClusterObject, {'id': service_id, 'cluster': cluster}, 'SERVICE_NOT_FOUND'
        )
        serial_class = self.select_serializer(request)
        serializer = serial_class(service, context={'request': request, 'cluster_id': cluster_id})
        return Response(serializer.data)

    def delete(self, request, cluster_id, service_id):
        """
        Remove service from cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        service = check_obj(
            ClusterObject, {'id': service_id, 'cluster': cluster}, 'SERVICE_NOT_FOUND'
        )
        cm.api.delete_service(service)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatusList(GenericAPIPermView):
    queryset = HostComponent.objects.all()
    serializer_class = api.cluster_serial.StatusSerializer

    def get(self, request, cluster_id):
        """
        Show all hosts and components in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        obj = self.get_queryset().filter(cluster=cluster)
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)


class HostComponentList(GenericAPIPermView, InterfaceView):
    queryset = HostComponent.objects.all()
    serializer_class = api.cluster_serial.HostComponentSerializer
    serializer_class_ui = api.cluster_serial.HostComponentUISerializer

    def get_serializer_class(self):
        if self.request and self.request.method == 'POST':
            return api.cluster_serial.HostComponentSaveSerializer
        return self.serializer_class

    def get(self, request, cluster_id):
        """
        Show host <-> component map in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        hc = self.get_queryset().filter(cluster=cluster)
        serializer_class = self.select_serializer(request)
        if self.for_ui(request):
            ui_hc = HostComponent()
            ui_hc.hc = hc
            serializer = serializer_class(ui_hc, context={'request': request, 'cluster': cluster})
        else:
            serializer = serializer_class(hc, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, cluster_id):
        """
        Create new mapping service:component <-> host in a specified cluster.
        """
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        save_serializer = self.get_serializer_class()
        serializer = save_serializer(data=request.data, context={
            'request': request, 'cluster': cluster,
        })
        if serializer.is_valid():
            hc_list = serializer.save()
            responce_serializer = self.serializer_class(
                hc_list, many=True, context={'request': request}
            )
            return Response(responce_serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HostComponentDetail(GenericAPIPermView):
    queryset = HostComponent.objects.all()
    serializer_class = api.cluster_serial.HostComponentSerializer

    def get_obj(self, cluster_id, hs_id):
        cluster = check_obj(Cluster, cluster_id, 'CLUSTER_NOT_FOUND')
        return check_obj(
            HostComponent,
            {'id': hs_id, 'cluster': cluster},
            'HOSTSERVICE_NOT_FOUND'
        )

    def get(self, request, cluster_id, hs_id):
        """
        Show host <-> component link in a specified cluster
        """
        obj = self.get_obj(cluster_id, hs_id)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)
