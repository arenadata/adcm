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

from django.http.response import Http404
from django_filters import rest_framework as drf_filters
from guardian.mixins import PermissionListMixin
from guardian.shortcuts import get_objects_for_user
from rest_framework import status, permissions
from rest_framework.response import Response

from api.base_view import GenericUIView, PaginatedView
from api.utils import (
    create,
    check_obj,
    check_custom_perm,
)
from cm.api import remove_host_from_cluster, delete_host, add_host_to_cluster
from cm.errors import AdcmEx
from cm.models import (
    Cluster,
    HostProvider,
    Host,
    GroupConfig,
    ClusterObject,
    ServiceComponent,
    HostComponent,
)
from cm.status_api import make_ui_host_status
from rbac.viewsets import DjangoOnlyObjectPermissions
from . import serializers


class NumberInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class HostFilter(drf_filters.FilterSet):
    cluster_is_null = drf_filters.BooleanFilter(field_name='cluster_id', lookup_expr='isnull')
    provider_is_null = drf_filters.BooleanFilter(field_name='provider_id', lookup_expr='isnull')
    group_config = drf_filters.ModelChoiceFilter(
        queryset=GroupConfig.objects.all(), field_name='group_config', label='GroupConfig'
    )
    hostcomponent__service_id = drf_filters.ModelChoiceFilter(
        queryset=ClusterObject.objects.all(),
        field_name='hostcomponent__service_id',
        label='HostComponentService',
        distinct=True,
    )
    hostcomponent__component_id = drf_filters.ModelChoiceFilter(
        queryset=ServiceComponent.objects.all(),
        field_name='hostcomponent__component_id',
        label='HostComponentComponent',
        distinct=True,
    )

    exclude_group_config__in = NumberInFilter(
        field_name='group_config', lookup_expr='in', label='ExcludeGroupConfigIn', exclude=True
    )

    class Meta:
        model = Host
        fields = [
            'cluster_id',
            'prototype_id',
            'provider_id',
            'fqdn',
            'cluster_is_null',
            'provider_is_null',
            'group_config',
            'hostcomponent__service_id',
            'hostcomponent__component_id',
            'exclude_group_config__in',
        ]


class HostList(PermissionListMixin, PaginatedView):
    """
    get:
    List all hosts

    post:
    Create new host
    """

    queryset = Host.objects.all()
    serializer_class = serializers.HostSerializer
    serializer_class_ui = serializers.HostUISerializer
    permission_required = ['cm.view_host']
    filterset_class = HostFilter
    filterset_fields = (
        'cluster_id',
        'prototype_id',
        'provider_id',
        'fqdn',
        'cluster_is_null',
        'provider_is_null',
        'group_config',
        'hostcomponent__service_id',
        'hostcomponent__component_id',
        'exclude_group_config__in',
    )  # just for documentation
    ordering_fields = (
        'fqdn',
        'state',
        'provider__name',
        'cluster__name',
        'prototype__display_name',
        'prototype__version_order',
    )

    def get_queryset(self):  # pylint: disable=arguments-differ
        queryset = super().get_queryset()
        kwargs = self.kwargs
        if 'cluster_id' in kwargs:  # List cluster hosts
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            queryset = queryset.filter(cluster=cluster)
        if 'provider_id' in kwargs:  # List provider hosts
            provider = check_obj(HostProvider, kwargs['provider_id'])
            queryset = queryset.filter(provider=provider)
        return get_objects_for_user(**self.get_get_objects_for_user_kwargs(queryset))

    def post(self, request, *args, **kwargs):
        """
        Create host
        """
        serializer = self.serializer_class(
            data=request.data,
            context={
                'request': request,
                'cluster_id': kwargs.get('cluster_id', None),
                'provider_id': kwargs.get('provider_id', None),
            },
        )
        if serializer.is_valid():
            if 'provider_id' in kwargs:  # List provider hosts
                provider = check_obj(HostProvider, kwargs['provider_id'])
            else:
                provider = serializer.validated_data.get(
                    'provider_id',
                )
            check_custom_perm(request.user, 'add_host_to', 'hostprovider', provider)
            return create(serializer)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HostListProvider(HostList):
    serializer_class = serializers.ProvideHostSerializer


class HostListCluster(HostList):
    serializer_class = serializers.ClusterHostSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            validated_data = serializer.validated_data
            if 'cluster_id' in kwargs:
                cluster = check_obj(Cluster, kwargs['cluster_id'])
            host = check_obj(Host, validated_data.get('id'))
            check_custom_perm(request.user, 'map_host_to', 'cluster', cluster)
            add_host_to_cluster(cluster, host)
            return Response(self.get_serializer(host).data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def check_host(host, cluster):
    if host.cluster != cluster:
        msg = f"Host #{host.id} doesn't belong to cluster #{cluster.id}"
        raise AdcmEx('FOREIGN_HOST', msg)


class HostDetail(PermissionListMixin, GenericUIView):
    """
    get:
    Show host
    """

    queryset = Host.objects.all()
    serializer_class = serializers.HostDetailSerializer
    serializer_class_ui = serializers.HostUISerializer
    permission_classes = (DjangoOnlyObjectPermissions,)
    permission_required = ['cm.view_host']
    lookup_field = 'id'
    lookup_url_kwarg = 'host_id'
    error_code = 'HOST_NOT_FOUND'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise AdcmEx(self.error_code) from None

    def get(self, request, *args, **kwargs):
        host = self.get_object()
        if 'cluster_id' in kwargs:
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            check_host(host, cluster)
        serializer = self.get_serializer(host)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        """
        Delete host
        """
        host = self.get_object()
        if 'cluster_id' in kwargs:
            # Remove host from cluster
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            check_host(host, cluster)
            check_custom_perm(request.user, 'unmap_host_from', 'cluster', cluster)
            remove_host_from_cluster(host)
        else:
            # Delete host (and all corresponding host services:components)
            delete_host(host)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatusList(GenericUIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.StatusSerializer
    model_name = Host
    queryset = HostComponent.objects.all()

    def get(self, request, host_id, cluster_id=None):
        """
        Show all components in a specified host
        """
        host = check_obj(Host, host_id)
        if self._is_for_ui():
            host_components = self.get_queryset().filter(host=host)
            return Response(make_ui_host_status(host, host_components))
        else:
            serializer = self.get_serializer(host)
            return Response(serializer.data)
