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

# pylint: disable=W0212

from itertools import chain

from rest_framework import status, permissions, exceptions
from rest_framework.response import Response

import api.serializers
import cm.api
import cm.bundle
import cm.job
import cm.status_api
from api.api_views import ListView, PageView, PageViewAdd, InterfaceView, DetailViewDelete
from api.api_views import GenericAPIPermView, GenericAPIPermStatusView, permission_denied
from api.api_views import create, update, check_obj, check_import_perm, DjangoModelPerm
from cm.errors import AdcmEx
from cm.models import Cluster, Host, HostComponent, Prototype
from cm.models import ClusterObject, Upgrade, ClusterBind
from . import serializers
from cm.logger import log


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


class MyPerm(DjangoModelPerm):
    def log_cache(self, user, label):
        cache = getattr(user, '_user_perm_cache', None)
        log.debug('HAS_PERM user: %s CACHE %s: %s', user, label, cache)

    def log_perm(self, user):
        log.debug('HAS_PERM user: %s, PERMS from DB: %s', user, user.user_permissions.all())

    def get_required_permissions(self, method, model_cls):
        log.debug('GET_PERM methd: %s, model: %s', method, model_cls)
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name,
        }

        log.debug('GET_PERM map: %s', self.perms_map)
        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        log.debug('GET_PERM kwargs: %s', kwargs)
        r = []
        for perm in self.perms_map[method]:
            codename = perm % kwargs
            log.debug('GET_PERM codename: %s, perm %s, kwargs: %s', codename, perm, kwargs)
            r.append(codename)
        log.debug('GET_PERM perm list: %s', r)
        return r

    def has_permission(self, request, view):
        if not request.user or (
            not request.user.is_authenticated and self.authenticated_users_only
        ):
            log.debug('HAS_PERM no user RESULT: False')
            return False

        queryset = self._queryset(view)
        perms = self.get_required_permissions(request.method, queryset.model)

        log.debug('HAS_PERM user: %s, PERMS: %s, MODEL %s', request.user, perms, queryset.model)
        self.log_perm(request.user)
        self.log_cache(request.user, 'BEFORE')

        r = request.user.has_perms(perms)
        self.log_cache(request.user, 'AFTER')
        log.debug('HAS_PERM user: %s, %s, %s RESULT: %s', request.user, perms, queryset.model, r)
        return r, perms


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
    permission_classes = (MyPerm,)

    def check_permissions(self, request):
        for permission in self.get_permissions():
            log.debug('CHECK_PERM %s %s', self.queryset.model, permission)
            r, perm = permission.has_permission(request, self)
            if not r:
                permission_denied(message=f'Auth fail {perm}')


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
    check_import_perm = check_import_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, cluster_id):  # pylint: disable=arguments-differ
        """
        List all imports avaliable for specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_import_perm('view', 'cluster', cluster)
        res = cm.api.get_import(cluster)
        return Response(res)

    def post(self, request, cluster_id):  # pylint: disable=arguments-differ
        """
        Update bind for cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_import_perm('change', 'cluster', cluster)
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
    check_import_perm = check_import_perm
    permission_classes = (permissions.IsAuthenticated,)

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
        self.check_import_perm('view', 'cluster', cluster)
        obj = self.get_queryset().filter(cluster=cluster, service=None)
        serializer = self.get_serializer_class()(obj, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, cluster_id):
        """
        Bind two clusters
        """
        cluster = check_obj(Cluster, cluster_id)
        self.check_import_perm('change', 'cluster', cluster)
        serializer = self.get_serializer_class()(data=request.data, context={'request': request})
        return create(serializer, cluster=cluster)


class ClusterBindDetail(DetailViewDelete):
    queryset = ClusterBind.objects.all()
    serializer_class = serializers.BindSerializer
    check_import_perm = check_import_perm
    permission_classes = (permissions.IsAuthenticated,)

    def get_obj(self, cluster_id, bind_id):
        cluster = check_obj(Cluster, cluster_id)
        return cluster, check_obj(ClusterBind, {'cluster': cluster, 'id': bind_id})

    def get(self, request, cluster_id, bind_id):  # pylint: disable=arguments-differ
        """
        Show specified bind of specified cluster
        """
        cluster, obj = self.get_obj(cluster_id, bind_id)
        self.check_import_perm('view', 'cluster', cluster)
        serializer = self.serializer_class(obj, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, cluster_id, bind_id):  # pylint: disable=arguments-differ
        """
        Unbind specified bind of specified cluster
        """
        cluster, bind = self.get_obj(cluster_id, bind_id)
        self.check_import_perm('change', 'cluster', cluster)
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


class StatusList(GenericAPIPermStatusView, InterfaceView):
    queryset = HostComponent.objects.all()
    model_name = Cluster
    serializer_class = serializers.StatusSerializer

    def ui_status(self, cluster, host_component):
        cluster_map = cm.status_api.get_object_map(cluster, 'cluster')

        def get_status(key, obj_id):
            if cluster_map is None:
                return 32
            if str(obj_id) in cluster_map[key]:
                return cluster_map[key][str(obj_id)]['status']
            else:
                return 0

        service_map = {}
        for hc in host_component:
            if hc.service.id not in service_map:
                service_map[hc.service.id] = {'service': hc.service, 'hc': {}}
            if hc.component.id not in service_map[hc.service.id]['hc']:
                service_map[hc.service.id]['hc'][hc.component.id] = {
                    'comp': hc.component,
                    'hosts': [],
                }
            service_map[hc.service.id]['hc'][hc.component.id]['hosts'].append(hc.host)

        # convert map to list
        service_list = []
        for srv in service_map.values():
            hc_list = []
            for hc in srv['hc'].values():
                host_comp_list = []
                for host in hc['hosts']:
                    host_comp_list.append(
                        {
                            'id': host.id,
                            'name': host.fqdn,
                            'status': cm.status_api.get_host_comp_status(host, hc['comp']),
                        }
                    )
                hc_list.append(
                    {
                        'id': hc['comp'].id,
                        'name': hc['comp'].display_name,
                        'status': cm.status_api.get_component_status(hc['comp']),
                        'hosts': host_comp_list,
                    }
                )
            service_list.append(
                {
                    'id': srv['service'].id,
                    'name': srv['service'].display_name,
                    'status': get_status('services', srv['service'].id),
                    'hc': hc_list,
                }
            )

        host_list = []
        for host in Host.obj.filter(cluster=cluster):
            host_list.append(
                {
                    'id': host.id,
                    'name': host.fqdn,
                    'status': get_status('hosts', host.id),
                }
            )

        return {
            'name': cluster.name,
            'status': 32 if cluster_map is None else cluster_map.get('status', 0),
            'chilren': {
                'hosts': host_list,
                'services': service_list,
            },
        }

    def get(self, request, cluster_id):
        """
        Show all hosts and components in a specified cluster
        """
        cluster = check_obj(Cluster, cluster_id)
        obj = self.get_queryset().filter(cluster=cluster)
        if self.for_ui(request):
            return Response(self.ui_status(cluster, obj))
        else:
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
