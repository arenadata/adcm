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

from guardian.mixins import PermissionListMixin
from rest_framework import permissions, status
from rest_framework.response import Response

import cm.api
import cm.bundle
import cm.job
from api.base_view import DetailView, GenericUIView, PaginatedView
from api.cluster.serializers import (
    BindSerializer,
    ClusterBindSerializer,
    ClusterDetailSerializer,
    ClusterDetailUISerializer,
    ClusterSerializer,
    ClusterUISerializer,
    ClusterUpdateSerializer,
    DoBindSerializer,
    DoClusterUpgradeSerializer,
    HostComponentSaveSerializer,
    HostComponentSerializer,
    HostComponentUISerializer,
    PostImportSerializer,
    StatusSerializer,
)
from api.serializers import ClusterUpgradeSerializer
from api.stack.serializers import (
    BundleServiceUISerializer,
    ImportSerializer,
    ServiceSerializer,
)
from api.utils import (
    AdcmOrderingFilter,
    check_custom_perm,
    check_obj,
    create,
    get_object_for_user,
    update,
)
from audit.utils import audit
from cm.errors import AdcmEx
from cm.models import (
    Cluster,
    ClusterBind,
    ClusterObject,
    HostComponent,
    Prototype,
    Upgrade,
)
from cm.status_api import make_ui_cluster_status
from cm.upgrade import get_upgrade
from rbac.viewsets import DjangoOnlyObjectPermissions


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


class ClusterList(PermissionListMixin, PaginatedView):
    """
    get:
    List of all existing clusters

    post:
    Create new cluster
    """

    queryset = Cluster.objects.all()
    serializer_class = ClusterSerializer
    serializer_class_ui = ClusterUISerializer
    serializer_class_post = ClusterDetailSerializer
    filterset_fields = ('name', 'prototype_id')
    ordering_fields = ('name', 'state', 'prototype__display_name', 'prototype__version_order')
    permission_required = ['cm.view_cluster']

    @audit
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        return create(serializer)


class ClusterDetail(PermissionListMixin, DetailView):
    """
    get:
    Show cluster
    """

    queryset = Cluster.objects.all()
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = ['cm.view_cluster']
    serializer_class = ClusterDetailSerializer
    serializer_class_put = ClusterUpdateSerializer
    serializer_class_patch = ClusterUpdateSerializer
    serializer_class_ui = ClusterDetailUISerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'cluster_id'
    error_code = 'CLUSTER_NOT_FOUND'

    @audit
    def patch(self, request, *args, **kwargs):
        """
        Edit cluster
        """
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        return update(serializer)

    @audit
    def put(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data, partial=False)
        return update(serializer)

    @audit
    def delete(self, request, *args, **kwargs):
        """
        Remove cluster
        """
        cluster = self.get_object()
        cm.api.delete_cluster(cluster)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterBundle(GenericUIView):
    queryset = Prototype.objects.filter(type='service')
    serializer_class = ServiceSerializer
    serializer_class_ui = BundleServiceUISerializer

    def get(self, request, *args, **kwargs):
        """
        List all services of specified cluster of bundle
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'add_service_to', 'cluster', cluster)
        bundle = self.get_queryset().filter(bundle=cluster.prototype.bundle)
        shared = self.get_queryset().filter(shared=True).exclude(bundle=cluster.prototype.bundle)
        serializer = self.get_serializer(
            list(chain(bundle, shared)), many=True, context={'request': request, 'cluster': cluster}
        )
        return Response(serializer.data)


class ClusterImport(GenericUIView):
    queryset = Prototype.objects.all()
    serializer_class = ImportSerializer
    serializer_class_post = PostImportSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get(request, *args, **kwargs):
        """
        List all imports available for specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'view_import_of', 'cluster', cluster, 'view_clusterbind')
        res = cm.api.get_import(cluster)
        return Response(res)

    @audit
    def post(self, request, *args, **kwargs):
        """
        Update bind for cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'change_import_of', 'cluster', cluster)
        serializer = self.get_serializer(
            data=request.data, context={'request': request, 'cluster': cluster}
        )
        if serializer.is_valid():
            res = serializer.create(serializer.validated_data)
            return Response(res, status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClusterBindList(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = ClusterBindSerializer
    serializer_class_post = DoBindSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        List all binds of specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'view_import_of', 'cluster', cluster, 'view_clusterbind')
        obj = self.get_queryset().filter(cluster=cluster, service=None)
        serializer = self.get_serializer(obj, many=True)
        return Response(serializer.data)

    @audit
    def post(self, request, *args, **kwargs):
        """
        Bind two clusters
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'change_import_of', 'cluster', cluster)
        serializer = self.get_serializer(data=request.data)
        return create(serializer, cluster=cluster)


class ClusterBindDetail(GenericUIView):
    queryset = ClusterBind.objects.all()
    serializer_class = BindSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @staticmethod
    def get_obj(kwargs, bind_id):
        bind = ClusterBind.objects.filter(pk=bind_id).first()
        if bind:
            return bind.source_service

        return None

    def get(self, request, *args, **kwargs):
        """
        Show specified bind of specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        bind = check_obj(ClusterBind, {'cluster': cluster, 'id': kwargs['bind_id']})
        check_custom_perm(request.user, 'view_import_of', 'cluster', cluster, 'view_clusterbind')
        serializer = self.get_serializer(bind)
        return Response(serializer.data)

    @audit
    def delete(self, request, *args, **kwargs):
        """
        Unbind specified bind of specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        bind = check_obj(ClusterBind, {'cluster': cluster, 'id': kwargs['bind_id']})
        check_custom_perm(request.user, 'change_import_of', 'cluster', cluster)
        cm.api.unbind(bind)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClusterUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = ClusterUpgradeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_ordering(self):
        order = AdcmOrderingFilter()
        return order.get_ordering(self.request, self.get_queryset(), self)

    def get(self, request, *args, **kwargs):
        """
        List all available upgrades for specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'view_upgrade_of', 'cluster', cluster)
        obj = get_upgrade(cluster, self.get_ordering())
        serializer = self.serializer_class(
            obj, many=True, context={'cluster_id': cluster.id, 'request': request}
        )
        return Response(serializer.data)


class ClusterUpgradeDetail(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = ClusterUpgradeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        List all available upgrades for specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'view_upgrade_of', 'cluster', cluster)
        obj = check_obj(
            Upgrade, {'id': kwargs['upgrade_id'], 'bundle__name': cluster.prototype.bundle.name}
        )
        serializer = self.serializer_class(
            obj, context={'cluster_id': cluster.id, 'request': request}
        )
        return Response(serializer.data)


class DoClusterUpgrade(GenericUIView):
    queryset = Upgrade.objects.all()
    serializer_class = DoClusterUpgradeSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @audit
    def post(self, request, *args, **kwargs):
        """
        Do upgrade specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'do_upgrade_of', 'cluster', cluster)
        serializer = self.get_serializer(data=request.data)
        return create(serializer, upgrade_id=int(kwargs['upgrade_id']), obj=cluster)


class StatusList(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = HostComponent.objects.all()
    serializer_class = StatusSerializer

    def get(self, request, *args, **kwargs):
        """
        Show all hosts and components in a specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        host_components = self.get_queryset().filter(cluster=cluster)
        if self._is_for_ui():
            return Response(make_ui_cluster_status(cluster, host_components))
        else:
            serializer = self.get_serializer(host_components, many=True)
            return Response(serializer.data)


class HostComponentList(GenericUIView):
    queryset = HostComponent.objects.all()
    serializer_class = HostComponentSerializer
    serializer_class_ui = HostComponentUISerializer
    serializer_class_post = HostComponentSaveSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        Show host <-> component map in a specified cluster
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(
            request.user, 'view_host_components_of', 'cluster', cluster, 'view_hostcomponent'
        )
        hc = (
            self.get_queryset()
            .prefetch_related('service', 'component', 'host')
            .filter(cluster=cluster)
        )
        if self._is_for_ui():
            ui_hc = HostComponent()
            ui_hc.hc = hc
            serializer = self.get_serializer(
                ui_hc, context={'request': request, 'cluster': cluster}
            )
        else:
            serializer = self.get_serializer(hc, many=True)
        return Response(serializer.data)

    @audit
    def post(self, request, *args, **kwargs):
        """
        Create new mapping service:component <-> host in a specified cluster.
        """
        cluster = get_object_for_user(
            request.user, 'cm.view_cluster', Cluster, id=kwargs['cluster_id']
        )
        check_custom_perm(request.user, 'edit_host_components_of', 'cluster', cluster)
        serializer = self.get_serializer(
            data=request.data,
            context={
                'request': request,
                'cluster': cluster,
            },
        )
        if serializer.is_valid():
            hc_list = serializer.save()
            response_serializer = self.serializer_class(
                hc_list, many=True, context={'request': request}
            )
            return Response(response_serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HostComponentDetail(GenericUIView):
    queryset = HostComponent.objects.all()
    serializer_class = HostComponentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_obj(self, cluster_id, hs_id):
        cluster = get_object_for_user(self.request.user, 'cm.view_cluster', Cluster, id=cluster_id)
        check_custom_perm(
            self.request.user, 'view_host_components_of', 'cluster', cluster, 'view_hostcomponent'
        )
        return check_obj(HostComponent, {'id': hs_id, 'cluster': cluster}, 'HOSTSERVICE_NOT_FOUND')

    def get(self, request, *args, **kwargs):
        """
        Show host <-> component link in a specified cluster
        """
        obj = self.get_obj(kwargs['cluster_id'], kwargs['hs_id'])
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
