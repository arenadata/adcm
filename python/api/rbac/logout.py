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

from adcm.serializers import EmptySerializer
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.schemas.coreapi import AutoSchema
import django.contrib.auth


class LogOutSerializer(EmptySerializer):
    """Logout serializer (because DRF need one)"""


class LogOut(GenericAPIView):
    serializer_class = LogOutSerializer
    schema = AutoSchema()

    @staticmethod
    def post(request, *args, **kwargs):  # noqa: ARG004
        django.contrib.auth.logout(request)

        return Response(status=status.HTTP_204_NO_CONTENT)
