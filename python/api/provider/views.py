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

from rest_framework import status
from rest_framework.response import Response

import cm
from cm.models import HostProvider, Upgrade

from api.api_views import create, check_obj, ListView, PageView, PageViewAdd, DetailViewRO
from api.api_views import GenericAPIPermView
import api.serializers
from . import serializers


class ProviderList(PageViewAdd):
    """
    get:
    List all host providers

    post:
    Create new host provider
    """
    queryset = HostProvider.objects.all()
    serializer_class = serializers.ProviderSerializer
    serializer_class_ui = serializers.ProviderUISerializer
    serializer_class_post = serializers.ProviderDetailSerializer
    filterset_fields = ('name', 'prototype_id')
    ordering_fields = ('name', 'state', 'prototype__display_name', 'prototype__version_order')


class ProviderDetail(DetailViewRO):
    """
    get:
    Show host provider
    """
    queryset = HostProvider.objects.all()
    serializer_class = serializers.ProviderDetailSerializer
    serializer_class_ui = serializers.ProviderUISerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'provider_id'
    error_code = 'PROVIDER_NOT_FOUND'

    def delete(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        Remove host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        cm.api.delete_host_provider(provider)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProviderUpgrade(PageView):
    queryset = Upgrade.objects.all()
    serializer_class = serializers.UpgradeProviderSerializer

    def get(self, request, provider_id):   # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = cm.upgrade.get_upgrade(provider, self.get_ordering(request, self.queryset, self))
        serializer = self.serializer_class(obj, many=True, context={
            'provider_id': provider.id, 'request': request
        })
        return Response(serializer.data)


class ProviderUpgradeDetail(ListView):
    queryset = Upgrade.objects.all()
    serializer_class = serializers.UpgradeProviderSerializer

    def get(self, request, provider_id, upgrade_id):   # pylint: disable=arguments-differ
        """
        List all avaliable upgrades for specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        obj = self.get_queryset().get(id=upgrade_id)
        serializer = self.serializer_class(obj, context={
            'provider_id': provider.id, 'request': request
        })
        return Response(serializer.data)


class DoProviderUpgrade(GenericAPIPermView):
    queryset = Upgrade.objects.all()
    serializer_class = api.serializers.DoUpgradeSerializer

    def post(self, request, provider_id, upgrade_id):
        """
        Do upgrade specified host provider
        """
        provider = check_obj(HostProvider, provider_id, 'PROVIDER_NOT_FOUND')
        serializer = self.serializer_class(data=request.data, context={'request': request})
        return create(serializer, upgrade_id=int(upgrade_id), obj=provider)
