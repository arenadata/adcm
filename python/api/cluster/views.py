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

from rest_framework import status, permissions
from rest_framework.response import Response

import api.serializers
import cm.api
import cm.bundle
import cm.job
import cm.status_api
from api.utils import (
    AdcmOrderingFilter,
    check_custom_perm,
    check_obj,
    create,
    update,
)
from api.base_view import GenericUIView, DetailView, PaginatedView
from cm.errors import AdcmEx
from cm.models import Cluster, HostComponent, Prototype, ClusterObject, Upgrade, ClusterBind
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


class ClusterList(PaginatedView):
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        return create(serializer)


class ClusterDetail(DetailView):
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
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        return update(serializer)

    def delete(self, request, *args, **kwargs):
        """
        Remove cluster
        """
        cluster = self.get_object()
        cm.api.delete_cluster(cluster)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterBundle(GenericUIView):
    queryset = Prototype.objects.filter(type='service')
    serializer_class = api.stack.serializers.ServiceSerializer
    serializer_class_ui = api.stack.serializers.BundleServiceUISerializer

    def get(self, request, cluster_id):
        """
        List all services of specified cluster of bundle
        """
        cluster = check_obj(Cluster, cluster_id)
        bundle = self.get_queryset().filter(bundle=cluster.prototype.bundle)
        shared = self.get_queryset().filter(shared=True).exclude(bundle=cluster.prototype.bundle)
        serializer = self.get_serializer(
            list(chain(bundle, shared)), many=True, context={'request': request, 'cluster': cluster}
        )
        return Response(serializer.data)


class ClusterImport(GenericUIView):
    queryset = Prototype.objects.all()
    serializer_class = api.stack.serializers.ImportSerializer
    serializer_class_post = serializers.PostImportSerializer
    check_import_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, cluster_id):
        """
        List all imports avaliable for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_import_perm('view_import_of', 'cluster', cluster, 'view_clusterbind')
        res = cm.api.get_import(cluster)
        return Response(res)

    def post(self, request, cluster_id):
        """
        Update bind for cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_import_perm('change_import_of', 'cluster', cluster)
        serializer = self.get_serializer(
            data=request.data, context={'request': request, 'cluster': cluster}
        )
        if serializer.is_valid():
            res = serializer.create(serializer.validated_data)
            return Response(res, status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClusterBindList(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = serializers.ClusterBindSerializer
    serializer_class_post = serializers.DoBindSerializer
    check_import_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, cluster_id):
        """
        List all binds of specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_import_perm('view_import_of', 'cluster', cluster, 'view_clusterbind')
        obj = self.get_queryset().filter(cluster=cluster, service=None)
        serializer = self.get_serializer(obj, many=True)
        return Response(serializer.data)

    def post(self, request, cluster_id):
        """
        Bind two clusters
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_import_perm('change_import_of', 'cluster', cluster)
        serializer = self.get_serializer(data=request.data)
        return create(serializer, cluster=cluster)


class ClusterBindDetail(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = serializers.BindSerializer
    check_import_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get_obj(self, cluster_id, bind_id):
        cluster = check_obj(Cluster, cluster_id)
        return cluster, check_obj(ClusterBind, {'cluster': cluster, 'id': bind_id})

    def get(self, request, cluster_id, bind_id):
        """
        Show specified bind of specified cluster
        """
        cluster, obj = self.get_obj(cluster_id, bind_id)
        self.check_import_perm('view_import_of', 'cluster', cluster, 'view_clusterbind')
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def delete(self, request, cluster_id, bind_id):
        """
        Unbind specified bind of specified cluster
        """
        cluster, bind = self.get_obj(cluster_id, bind_id)
        self.check_import_perm('change_import_of', 'cluster', cluster)
        cm.api.unbind(bind)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeLinkSerializer
    check_upgrade_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get_ordering(self, request, queryset, view):
        Order = AdcmOrderingFilter()
        return Order.get_ordering(request, queryset, view)

    def get(self, request, cluster_id):
        """
        List all avaliable upgrades for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_upgrade_perm('view_upgrade_of', 'cluster', cluster)
        obj = cm.upgrade.get_upgrade(cluster, self.get_ordering(request, self.queryset, self))
        serializer = self.serializer_class(
            obj, many=True, context={'cluster_id': cluster.id, 'request': request}
        )
        return Response(serializer.data)


class ClusterUpgradeDetail(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.UpgradeLinkSerializer
    check_upgrade_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, cluster_id, upgrade_id):
        """
        List all avaliable upgrades for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_upgrade_perm('view_upgrade_of', 'cluster', cluster)
        obj = self.get_queryset().get(id=upgrade_id)
        serializer = self.serializer_class(
            obj, context={'cluster_id': cluster.id, 'request': request}
        )
        return Response(serializer.data)


class DoClusterUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.DoUpgradeSerializer
    check_upgrade_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, cluster_id, upgrade_id):
        """
        Do upgrade specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_upgrade_perm('do_upgrade_of', 'cluster', cluster)
        serializer = self.get_serializer(data=request.data)
        return create(serializer, upgrade_id=int(upgrade_id), obj=cluster)


class StatusList(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = HostComponent.objects.all()
    model_name = Cluster
    serializer_class = serializers.StatusSerializer

    def get(self, request, cluster_id):
        """
        Show all hosts and components in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        host_components = self.get_queryset().filter(cluster=cluster)
        if self._is_for_ui():
            return Response(cm.status_api.make_ui_cluster_status(cluster, host_components))
        else:
            serializer = self.get_serializer(host_components, many=True)
            return Response(serializer.data)


class HostComponentList(GenericUIView):
    queryset = HostComponent.objects.all()
    serializer_class = serializers.HostComponentSerializer
    serializer_class_ui = serializers.HostComponentUISerializer
    serializer_class_post = serializers.HostComponentSaveSerializer
    check_hc_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, cluster_id):
        """
        Show host <-> component map in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_hc_perm('view_host_components_of', 'cluster', cluster, 'view_hostcomponent')
        hc = self.get_queryset().filter(cluster=cluster)
        if self._is_for_ui():
            ui_hc = HostComponent()
            ui_hc.hc = hc
            serializer = self.get_serializer(
                ui_hc, context={'request': request, 'cluster': cluster}
            )
        else:
            serializer = self.get_serializer(hc, many=True)
        return Response(serializer.data)

    def post(self, request, cluster_id):
        """
        Create new mapping service:component <-> host in a specified cluster.
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_hc_perm('edit_host_components_of', 'cluster', cluster)
        serializer = self.get_serializer(
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


class HostComponentDetail(GenericUIView):
    queryset = HostComponent.objects.all()
    serializer_class = serializers.HostComponentSerializer
    check_hc_perm = check_custom_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get_obj(self, cluster_id, hs_id):
        cluster = check_obj(Cluster, cluster_id)
        self.check_hc_perm('view_host_components_of', 'cluster', cluster, 'view_hostcomponent')
        return check_obj(HostComponent, {'id': hs_id, 'cluster': cluster}, 'HOSTSERVICE_NOT_FOUND')

    def get(self, request, cluster_id, hs_id):
        """
        Show host <-> component link in a specified cluster
        """
        obj = self.get_obj(cluster_id, hs_id)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
