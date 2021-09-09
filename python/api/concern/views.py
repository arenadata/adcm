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

from api.api_views import PageView, DetailViewRO
from cm import models
from . import serializers


class ConcernFilter(drf_filters.FilterSet):
    adcm = drf_filters.ModelMultipleChoiceFilter(
        queryset=models.ADCM.objects.all(),
        field_name='adcm_entities__id',
        to_field_name='id',
    )
    cluster = drf_filters.ModelMultipleChoiceFilter(
        queryset=models.Cluster.objects.all(),
        field_name='cluster_entities__id',
        to_field_name='id',
    )
    service = drf_filters.ModelMultipleChoiceFilter(
        queryset=models.ClusterObject.objects.all(),
        field_name='clusterobject_entities__id',
        to_field_name='id',
    )
    component = drf_filters.ModelMultipleChoiceFilter(
        queryset=models.ServiceComponent.objects.all(),
        field_name='servicecomponent_entities__id',
        to_field_name='id',
    )
    provider = drf_filters.ModelMultipleChoiceFilter(
        queryset=models.HostProvider.objects.all(),
        field_name='hostprovider_entities__id',
        to_field_name='id',
    )
    host = drf_filters.ModelMultipleChoiceFilter(
        queryset=models.Host.objects.all(),
        field_name='host_entities__id',
        to_field_name='id',
    )

    class Meta:
        model = models.ConcernItem
        fields = [
            'name',
            'adcm',
            'cluster',
            'service',
            'component',
            'provider',
            'host',
        ]


class ConcernItemList(PageView):
    """
    get:
    List of all existing concern items
    """

    queryset = models.ConcernItem.objects.all()
    serializer_class = serializers.ConcernItemSerializer
    serializer_class_ui = serializers.ConcernItemDetailSerializer
    filterset_class = ConcernFilter
    ordering_fields = ('name',)


class ConcernItemDetail(DetailViewRO):
    """
    get:
    Show concern item
    """

    queryset = models.ConcernItem.objects.all()
    serializer_class = serializers.ConcernItemDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'concern_id'
    error_code = 'CONCERNITEM_NOT_FOUND'
