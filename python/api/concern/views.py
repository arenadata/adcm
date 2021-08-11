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

from api.api_views import PageView, DetailViewRO
from cm.models import ConcernItem
from . import serializers


class ConcernItemList(PageView):
    """
    get:
    List of all existing concern items
    """

    queryset = ConcernItem.objects.all()
    serializer_class = serializers.ConcernItemSerializer
    serializer_class_ui = serializers.ConcernItemDetailSerializer
    filterset_fields = ('name',)
    ordering_fields = ('name',)


class ConcernItemDetail(DetailViewRO):
    """
    get:
    Show concern item
    """

    queryset = ConcernItem.objects.all()
    serializer_class = serializers.ConcernItemDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'concern_id'
    error_code = 'CONCERNITEM_NOT_FOUND'
