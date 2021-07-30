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

from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from haystack.query import SearchQuerySet

from api.api_views import create
from cm.errors import AdcmEx
from cm.logger import log
from cm.models import Cluster


def search(query):
    res  = []
    #r = SearchQuerySet().filter(content=query)
    r = SearchQuerySet().filter(content=query).models(Cluster)
    for item in r:
        log.debug('QQ %s %s', item.get_additional_fields(), item.get_stored_fields())
        obj = item.object
        res.append({
            'id': obj.id,
            'type': obj.__class__.__name__,
            'name': obj.name,
        }
        )
    return res


class SearchPostSerializer(serializers.Serializer):
    query = serializers.CharField()
    

class Search(GenericAPIView):
    serializer_class = SearchPostSerializer

    def post(self, request):
        """
        Do search
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            res = search(serializer.data['query'])
            return Response(res, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
