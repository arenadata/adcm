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

from django.contrib.contenttypes.models import ContentType
from django_filters import rest_framework as drf_filters
from rest_framework.permissions import IsAuthenticated

from api.base_view import DetailView, PaginatedView
from api.concern.serializers import (
    ConcernItemDetailSerializer,
    ConcernItemSerializer,
    ConcernItemUISerializer,
)
from cm import models
from cm.errors import AdcmEx

OBJECT_TYPES = {
    'adcm': 'adcm',
    'cluster': 'cluster',
    'service': 'clusterobject',
    'component': 'servicecomponent',
    'provider': 'hostprovider',
    'host': 'host',
}
CHOICES = list(zip(OBJECT_TYPES, OBJECT_TYPES))


class ConcernFilter(drf_filters.FilterSet):
    type = drf_filters.ChoiceFilter(choices=models.ConcernType.choices)
    cause = drf_filters.ChoiceFilter(choices=models.ConcernCause.choices)
    object_id = drf_filters.NumberFilter(label='Related object ID', method='_pass')
    object_type = drf_filters.ChoiceFilter(label='Related object type', choices=CHOICES, method='_filter_by_object')
    owner_type = drf_filters.ChoiceFilter(choices=CHOICES, method='_filter_by_owner_type')

    class Meta:
        model = models.ConcernItem
        fields = [
            'name',
            'type',
            'cause',
            'object_type',
            'object_id',
            'owner_type',
            'owner_id',
        ]

    def _filter_by_owner_type(self, queryset, name, value: str):
        owner_type = ContentType.objects.get(app_label='cm', model=OBJECT_TYPES[value])
        return queryset.filter(owner_type=owner_type)

    def _pass(self, queryset, name, value):
        # do not pass to filter directly
        return queryset

    def _filter_by_object(self, queryset, name, value):
        object_id = self.request.query_params.get('object_id')
        filters = {f'{OBJECT_TYPES[value]}_entities__id': object_id}
        return queryset.filter(**filters)

    def is_valid(self):
        object_type = self.request.query_params.get('object_type')
        object_id = self.request.query_params.get('object_id')
        both_present = all((object_id, object_type))
        none_present = not any((object_id, object_type))
        if not (both_present or none_present):
            raise AdcmEx(
                'BAD_QUERY_PARAMS',
                msg='Both object_type and object_id params are expected or none of them',
            )

        return super().is_valid()


class ConcernItemList(PaginatedView):
    """
    get:
    List of all existing concern items
    """

    queryset = models.ConcernItem.objects.all()
    serializer_class = ConcernItemSerializer
    serializer_class_ui = ConcernItemUISerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = ConcernFilter
    ordering_fields = ('name',)


class ConcernItemDetail(DetailView):
    """
    get:
    Show concern item
    """

    queryset = models.ConcernItem.objects.all()
    serializer_class = ConcernItemDetailSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = 'id'
    lookup_url_kwarg = 'concern_id'
    error_code = 'CONCERNITEM_NOT_FOUND'
