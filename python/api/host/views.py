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

from django_filters import rest_framework as drf_filters
from rest_framework.response import Response
from rest_framework import status

import cm
from cm.errors import AdcmEx
from cm.models import Cluster, HostProvider, Host
from api.api_views import PageView, DetailViewDelete, create, check_obj
from . import serializers


class HostFilter(drf_filters.FilterSet):
    cluster_is_null = drf_filters.BooleanFilter(field_name='cluster_id', lookup_expr='isnull')
    provider_is_null = drf_filters.BooleanFilter(field_name='provider_id', lookup_expr='isnull')

    class Meta:
        model = Host
        fields = ['cluster_id', 'prototype_id', 'provider_id', 'fqdn']


class HostList(PageView):
    """
    get:
    List all hosts

    post:
    Create new host
    """

    serializer_class = serializers.HostSerializer
    serializer_class_ui = serializers.HostUISerializer
    filterset_class = HostFilter
    filterset_fields = (
        'cluster_id',
        'prototype_id',
        'provider_id',
        'fqdn',
        'cluster_is_null',
        'provider_is_null',
    )  # just for documentation
    ordering_fields = (
        'fqdn',
        'state',
        'provider__name',
        'cluster__name',
        'prototype__display_name',
        'prototype__version_order',
    )

    def get_queryset(self):
        ids = self.request.query_params.get('ids')
        if ids is not None:
            return Host.objects.filter(id__in=map(int, ids.split(',')))
        else:
            return Host.objects.all()

    def get(self, request, *args, **kwargs):
        """
        List all hosts
        """
        queryset = self.get_queryset()
        if 'cluster_id' in kwargs:  # List cluster hosts
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            queryset = self.get_queryset().filter(cluster=cluster)
        if 'provider_id' in kwargs:  # List provider hosts
            provider = check_obj(HostProvider, kwargs['provider_id'])
            queryset = self.get_queryset().filter(provider=provider)
        return self.get_page(self.filter_queryset(queryset), request)

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
        return create(serializer)


class HostListProvider(HostList):
    serializer_class = serializers.ProvideHostSerializer


class HostListCluster(HostList):
    serializer_class = serializers.ClusterHostSerializer


def check_host(host, cluster):
    if host.cluster != cluster:
        msg = "Host #{} doesn't belong to cluster #{}".format(host.id, cluster.id)
        raise AdcmEx('FOREIGN_HOST', msg)


class HostDetail(DetailViewDelete):
    """
    get:
    Show host
    """

    queryset = Host.objects.all()
    serializer_class = serializers.HostDetailSerializer
    serializer_class_ui = serializers.HostUISerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'host_id'
    error_code = 'HOST_NOT_FOUND'

    def get(self, request, host_id, **kwargs):  # pylint: disable=arguments-differ)
        host = check_obj(Host, host_id)
        if 'cluster_id' in kwargs:
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            check_host(host, cluster)
        serial_class = self.select_serializer(request)
        serializer = serial_class(host, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, host_id, **kwargs):  # pylint: disable=arguments-differ
        """
        Delete host
        """
        host = check_obj(Host, host_id, 'HOST_NOT_FOUND')
        if 'cluster_id' in kwargs:
            # Remove host from cluster
            cluster = check_obj(Cluster, kwargs['cluster_id'])
            check_host(host, cluster)
            cm.api.remove_host_from_cluster(host)
        else:
            # Delete host (and all corresponding host services:components)
            cm.api.delete_host(host)
        return Response(status=status.HTTP_204_NO_CONTENT)
