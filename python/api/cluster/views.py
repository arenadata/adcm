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
from cm.models import Cluster, HostComponent, Prototype
from cm.models import ClusterObject, Upgrade, ClusterBind
from cm.logger import log  # pylint: disable=unused-import

import api.serializers
from api.api_views import create, update, check_obj, GenericAPIPermView
from api.api_views import ListView, PageView, PageViewAdd, InterfaceView, DetailViewDelete
from . import serializers


def get_obj_conf(cluster_id, service_id):
    cluster = check_obj(Cluster, cluster_id)
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
    serializer_class = serializers.ClusterSerializer
    serializer_class_ui = serializers.ClusterUISerializer
    serializer_class_post = serializers.ClusterDetailSerializer
    filterset_fields = ('name', 'prototype_id')
    ordering_fields = ('name', 'state', 'prototype__display_name', 'prototype__version_order')


class ClusterDetail(DetailViewDelete):
    """
    get:
    Show cluster
    """

    queryset = Cluster.objects.all()
    serializer_class = serializers.ClusterDetailSerializer
    serializer_class_ui = serializers.ClusterUISerializer
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


class ClusterBundle(ListView):
    queryset = Prototype.objects.filter(type='service')
    serializer_class = api.stack.serializers.ServiceSerializer
    serializer_class_ui = api.stack.serializers.BundleServiceUISerializer

    def get(self, request, cluster_id):  # pylint: disable=arguments-differ
        """
        List all services of specified cluster of bundle
        """
        cluster = check_obj(Cluster, cluster_id)
        bundle = self.get_queryset().filter(bundle=cluster.prototype.bundle)
        shared = self.get_queryset().filter(shared=True).exclude(bundle=cluster.prototype.bundle)
        serializer_class = self.select_serializer(request)
        serializer = serializer_class(
            list(chain(bundle, shared)), many=True, context={'request': request, 'cluster': cluster}
        )
        return Response(serializer.data)


class ClusterImport(ListView):
    queryset = Prototype.objects.all()
    serializer_class = api.stack.serializers.ImportSerializer
    post_serializer = serializers.PostImportSerializer

    def get(self, request, cluster_id):  # pylint: disable=arguments-differ
        """
        List all imports avaliable for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        res = cm.api.get_import(cluster)
        return Response(res)

    def post(self, request, cluster_id):  # pylint: disable=arguments-differ
        """
        Update bind for cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        serializer = self.post_serializer(
            data=request.data, context={'request': request, 'cluster': cluster}
        )
        if serializer.is_valid():
            res = serializer.create(serializer.validated_data)
            return Response(res, status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClusterBindList(ListView):
    queryset = ClusterBind.objects.all()
    serializer_class = serializers.ClusterBindSerializer

    def get_serializer_class(self):
        if self.request and self.request.method == 'POST':
            return serializers.DoBindSerializer
        else:
            return serializers.ClusterBindSerializer

    def get(self, request, cluster_id):  # pylint: disable=arguments-differ
        """
        List all binds of specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        obj = self.get_queryset().filter(cluster=cluster, service=None)
        serializer = self.get_serializer_class()(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, cluster_id):
        """
        Bind two clusters
        """
        cluster = check_obj(Cluster, cluster_id)
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        return create(serializer, cluster=cluster)


class ClusterBindDetail(DetailViewDelete):
    queryset = ClusterBind.objects.all()
    serializer_class = serializers.BindSerializer

    def get_obj(self, cluster_id, bind_id):
        cluster = check_obj(Cluster, cluster_id)
        return check_obj(ClusterBind, {'cluster': cluster, 'id': bind_id})

    def get(self, request, cluster_id, bind_id):  # pylint: disable=arguments-differ
        """
        Show specified bind of specified cluster
        """
        obj = self.get_obj(cluster_id, bind_id)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, cluster_id, bind_id):  # pylint: disable=arguments-differ
        """
        Unbind specified bind of specified cluster
        """
        bind = self.get_obj(cluster_id, bind_id)
        cm.api.unbind(bind)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterUpgrade(PageView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeLinkSerializer

    def get(self, request, cluster_id):  # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        obj = cm.upgrade.get_upgrade(cluster, self.get_ordering(request, self.queryset, self))
        serializer = self.serializer_class(
            obj, many=True, context={'cluster_id': cluster.id, 'request': request}
        )
        return Response(serializer.data)


class ClusterUpgradeDetail(ListView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeLinkSerializer

    def get(self, request, cluster_id, upgrade_id):  # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        obj = self.get_queryset().get(id=upgrade_id)
        serializer = self.serializer_class(
            obj, context={'cluster_id': cluster.id, 'request': request}
        )
        return Response(serializer.data)


class DoClusterUpgrade(GenericAPIPermView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.DoUpgradeSerializer

    def post(self, request, cluster_id, upgrade_id):
        """
        Do upgrade specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, upgrade_id=int(upgrade_id), obj=cluster)


class StatusList(GenericAPIPermView):
    queryset = HostComponent.objects.all()
    serializer_class = serializers.StatusSerializer

    def get(self, request, cluster_id):
        """
        Show all hosts and components in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        obj = self.get_queryset().filter(cluster=cluster)
        serializer = self.serializer_class(obj, many=True, context={'request': request})
        return Response(serializer.data)


class HostComponentList(GenericAPIPermView, InterfaceView):
    queryset = HostComponent.objects.all()
    serializer_class = serializers.HostComponentSerializer
    serializer_class_ui = serializers.HostComponentUISerializer

    def get_serializer_class(self):
        if self.request and self.request.method == 'POST':
            return serializers.HostComponentSaveSerializer
        return self.serializer_class

    def get(self, request, cluster_id):
        """
        Show host <-> component map in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
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
        cluster = check_obj(Cluster, cluster_id)
        save_serializer = self.get_serializer_class()
        serializer = save_serializer(
            data=request.data,
            context={
                'request': request,
                'cluster': cluster,
            },
        )
        if serializer.is_valid():
            hc_list = serializer.save()
            responce_serializer = self.serializer_class(
                hc_list, many=True, context={'request': request}
            )
            return Response(responce_serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HostComponentDetail(GenericAPIPermView):
    queryset = HostComponent.objects.all()
    serializer_class = serializers.HostComponentSerializer

    def get_obj(self, cluster_id, hs_id):
        cluster = check_obj(Cluster, cluster_id)
        return check_obj(HostComponent, {'id': hs_id, 'cluster': cluster}, 'HOSTSERVICE_NOT_FOUND')

    def get(self, request, cluster_id, hs_id):
        """
        Show host <-> component link in a specified cluster
        """
        obj = self.get_obj(cluster_id, hs_id)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)
